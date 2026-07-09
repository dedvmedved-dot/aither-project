"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.authenticateViaLDAP = authenticateViaLDAP;
exports.isLDAPEnabled = isLDAPEnabled;
const ldap = require("ldapjs");
// --- Configuration (from env) ---
const LDAP_ENABLED = !!(process.env.LDAP_URL);
const LDAP_URL = process.env.LDAP_URL || "ldap://localhost:389";
const LDAP_BASE_DN = process.env.LDAP_BASE_DN || "dc=example,dc=com";
const LDAP_BIND_DN = process.env.LDAP_BIND_DN || ""; // service account DN
const LDAP_BIND_PASSWORD = process.env.LDAP_BIND_PASSWORD || "";
// Where to search for users. FreeIPA default: cn=users,cn=accounts
const LDAP_USER_BASE = process.env.LDAP_USER_BASE || `cn=users,cn=accounts,${LDAP_BASE_DN}`;
// Where to search for groups (optional, for role mapping)
const LDAP_GROUP_BASE = process.env.LDAP_GROUP_BASE || `cn=groups,cn=accounts,${LDAP_BASE_DN}`;
// Attribute mappings
const LDAP_UID_ATTR = process.env.LDAP_UID_ATTR || "uid"; // FreeIPA/OpenLDAP
const LDAP_MAIL_ATTR = process.env.LDAP_MAIL_ATTR || "mail";
const LDAP_NAME_ATTR = process.env.LDAP_NAME_ATTR || "displayName"; // cn fallback
// --- LDAP client factory ---
function createClient() {
    return ldap.createClient({ url: LDAP_URL, reconnect: false, timeout: 5000 });
}
// --- Bind as service account ---
function bindService(client) {
    return new Promise((resolve, reject) => {
        if (!LDAP_BIND_DN) {
            // Anonymous bind (not recommended, but works for some setups)
            client.bind("", "", (err) => {
                if (err)
                    return reject(new Error("LDAP anonymous bind failed: " + err.message));
                resolve();
            });
            return;
        }
        client.bind(LDAP_BIND_DN, LDAP_BIND_PASSWORD, (err) => {
            if (err)
                return reject(new Error("LDAP service bind failed: " + err.message));
            resolve();
        });
    });
}
// --- Search for user DN ---
function searchUser(client, username) {
    return new Promise((resolve, reject) => {
        const filter = `(|(${LDAP_UID_ATTR}=${escapeLDAP(username)})(mail=${escapeLDAP(username)}))`;
        const opts = {
            filter,
            scope: "sub",
            attributes: [LDAP_UID_ATTR, LDAP_MAIL_ATTR, LDAP_NAME_ATTR, "cn", "memberOf", "dn"],
            timeLimit: 3,
            sizeLimit: 1,
        };
        client.search(LDAP_USER_BASE, opts, (err, res) => {
            if (err)
                return reject(new Error("LDAP search failed: " + err.message));
            let found = null;
            res.on("searchEntry", (entry) => {
                const attrs = {};
                entry.pojo.attributes.forEach((a) => {
                    attrs[a.type] = a.values.length === 1 ? a.values[0] : a.values;
                });
                found = { dn: entry.pojo.objectName, attrs };
            });
            res.on("error", (err) => reject(err));
            res.on("end", () => resolve(found));
        });
    });
}
// --- Authenticate user (bind with user DN + password) ---
function bindUser(client, dn, password) {
    return new Promise((resolve, reject) => {
        client.bind(dn, password, (err) => {
            if (err)
                return reject(new Error("LDAP user bind failed: invalid credentials"));
            resolve();
        });
    });
}
// --- Search for user groups ---
function getUserGroups(client, userDn) {
    return new Promise((resolve) => {
        // Try memberOf attribute first (Active Directory style)
        // For FreeIPA: search groups where member=userDn
        const filter = `(member=${escapeLDAP(userDn)})`;
        const opts = { filter, scope: "sub", attributes: ["cn"], timeLimit: 2 };
        client.search(LDAP_GROUP_BASE, opts, (err, res) => {
            if (err)
                return resolve([]);
            const groups = [];
            res.on("searchEntry", (entry) => {
                const cn = entry.pojo.attributes.find((a) => a.type === "cn");
                if (cn && cn.values[0])
                    groups.push(cn.values[0]);
            });
            res.on("error", () => resolve(groups));
            res.on("end", () => resolve(groups));
        });
    });
}
// --- Map LDAP groups → portal role ---
const GROUP_ROLE_MAP = {
    "aither-admins": "owner",
    "aither-billing": "billing_admin",
    "aither-developers": "developer",
    // Default: "viewer"
};
function mapRole(groups) {
    for (const g of groups) {
        const role = GROUP_ROLE_MAP[g.toLowerCase()];
        if (role)
            return role;
    }
    return "developer"; // default
}
// --- Escape LDAP filter special chars ---
function escapeLDAP(str) {
    return str.replace(/[*()\\\x00]/g, "\\$&");
}
async function authenticateViaLDAP(username, password) {
    if (!LDAP_ENABLED)
        return null;
    if (!username || !password)
        return null;
    const client = createClient();
    try {
        // Step 1: bind as service account
        await bindService(client);
        // Step 2: search for user
        const userEntry = await searchUser(client, username);
        if (!userEntry)
            return null;
        // Step 3: close service client, open new one for user bind
        // (ldapjs won't allow re-binding after search)
        client.destroy();
        const userClient = createClient();
        await bindUser(userClient, userEntry.dn, password);
        // Step 4: get groups (on the user-bound client if possible, or service client)
        // Re-bind as service for group search
        userClient.destroy();
        const groupClient = createClient();
        await bindService(groupClient);
        const groups = await getUserGroups(groupClient, userEntry.dn);
        groupClient.destroy();
        const attrs = userEntry.attrs;
        const uid = attrs[LDAP_UID_ATTR] || username;
        const email = attrs[LDAP_MAIL_ATTR] || `${username}@ldap.local`;
        const displayName = attrs[LDAP_NAME_ATTR] || attrs["cn"] || uid;
        return {
            uid,
            email,
            displayName,
            groups,
            role: mapRole(groups),
        };
    }
    catch (e) {
        client.destroy();
        return null;
    }
}
// --- Check if LDAP is configured ---
function isLDAPEnabled() {
    return LDAP_ENABLED;
}
