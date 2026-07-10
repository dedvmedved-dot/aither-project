"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.authenticateViaLDAP = authenticateViaLDAP;
exports.isLDAPEnabled = isLDAPEnabled;
var ldap = require("ldapjs");
// --- Configuration (from env) ---
var LDAP_ENABLED = !!(process.env.LDAP_URL);
var LDAP_URL = process.env.LDAP_URL || "ldap://localhost:389";
var LDAP_BASE_DN = process.env.LDAP_BASE_DN || "dc=example,dc=com";
var LDAP_BIND_DN = process.env.LDAP_BIND_DN || ""; // service account DN
var LDAP_BIND_PASSWORD = process.env.LDAP_BIND_PASSWORD || "";
// Where to search for users. FreeIPA default: cn=users,cn=accounts
var LDAP_USER_BASE = process.env.LDAP_USER_BASE || "cn=users,cn=accounts,".concat(LDAP_BASE_DN);
// Where to search for groups (optional, for role mapping)
var LDAP_GROUP_BASE = process.env.LDAP_GROUP_BASE || "cn=groups,cn=accounts,".concat(LDAP_BASE_DN);
// Attribute mappings
var LDAP_UID_ATTR = process.env.LDAP_UID_ATTR || "uid"; // FreeIPA/OpenLDAP
var LDAP_MAIL_ATTR = process.env.LDAP_MAIL_ATTR || "mail";
var LDAP_NAME_ATTR = process.env.LDAP_NAME_ATTR || "displayName"; // cn fallback
// --- LDAP client factory ---
function createClient() {
    return ldap.createClient({ url: LDAP_URL, reconnect: false, timeout: 5000 });
}
// --- Bind as service account ---
function bindService(client) {
    return new Promise(function (resolve, reject) {
        if (!LDAP_BIND_DN) {
            // Anonymous bind (not recommended, but works for some setups)
            client.bind("", "", function (err) {
                if (err)
                    return reject(new Error("LDAP anonymous bind failed: " + err.message));
                resolve();
            });
            return;
        }
        client.bind(LDAP_BIND_DN, LDAP_BIND_PASSWORD, function (err) {
            if (err)
                return reject(new Error("LDAP service bind failed: " + err.message));
            resolve();
        });
    });
}
// --- Search for user DN ---
function searchUser(client, username) {
    return new Promise(function (resolve, reject) {
        var filter = "(|(".concat(LDAP_UID_ATTR, "=").concat(escapeLDAP(username), ")(mail=").concat(escapeLDAP(username), "))");
        var opts = {
            filter: filter,
            scope: "sub",
            attributes: [LDAP_UID_ATTR, LDAP_MAIL_ATTR, LDAP_NAME_ATTR, "cn", "memberOf", "dn"],
            timeLimit: 3,
            sizeLimit: 1,
        };
        client.search(LDAP_USER_BASE, opts, function (err, res) {
            if (err)
                return reject(new Error("LDAP search failed: " + err.message));
            var found = null;
            res.on("searchEntry", function (entry) {
                var attrs = {};
                entry.pojo.attributes.forEach(function (a) {
                    attrs[a.type] = a.values.length === 1 ? a.values[0] : a.values;
                });
                found = { dn: entry.pojo.objectName, attrs: attrs };
            });
            res.on("error", function (err) { return reject(err); });
            res.on("end", function () { return resolve(found); });
        });
    });
}
// --- Authenticate user (bind with user DN + password) ---
function bindUser(client, dn, password) {
    return new Promise(function (resolve, reject) {
        client.bind(dn, password, function (err) {
            if (err)
                return reject(new Error("LDAP user bind failed: invalid credentials"));
            resolve();
        });
    });
}
// --- Search for user groups ---
function getUserGroups(client, userDn) {
    return new Promise(function (resolve) {
        // Try memberOf attribute first (Active Directory style)
        // For FreeIPA: search groups where member=userDn
        var filter = "(member=".concat(escapeLDAP(userDn), ")");
        var opts = { filter: filter, scope: "sub", attributes: ["cn"], timeLimit: 2 };
        client.search(LDAP_GROUP_BASE, opts, function (err, res) {
            if (err)
                return resolve([]);
            var groups = [];
            res.on("searchEntry", function (entry) {
                var cn = entry.pojo.attributes.find(function (a) { return a.type === "cn"; });
                if (cn && cn.values[0])
                    groups.push(cn.values[0]);
            });
            res.on("error", function () { return resolve(groups); });
            res.on("end", function () { return resolve(groups); });
        });
    });
}
// --- Map LDAP groups → portal role ---
var GROUP_ROLE_MAP = {
    "aither-admins": "owner",
    "aither-billing": "billing_admin",
    "aither-developers": "developer",
    // Default: "viewer"
};
function mapRole(groups) {
    for (var _i = 0, groups_1 = groups; _i < groups_1.length; _i++) {
        var g = groups_1[_i];
        var role = GROUP_ROLE_MAP[g.toLowerCase()];
        if (role)
            return role;
    }
    return "developer"; // default
}
// --- Escape LDAP filter special chars ---
function escapeLDAP(str) {
    return str.replace(/[*()\\\x00]/g, "\\$&");
}
function authenticateViaLDAP(username, password) {
    return __awaiter(this, void 0, void 0, function () {
        var client, userEntry, userClient, groupClient, groups, attrs, uid, email, displayName, e_1;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0:
                    if (!LDAP_ENABLED)
                        return [2 /*return*/, null];
                    if (!username || !password)
                        return [2 /*return*/, null];
                    client = createClient();
                    _a.label = 1;
                case 1:
                    _a.trys.push([1, 7, , 8]);
                    // Step 1: bind as service account
                    return [4 /*yield*/, bindService(client)];
                case 2:
                    // Step 1: bind as service account
                    _a.sent();
                    return [4 /*yield*/, searchUser(client, username)];
                case 3:
                    userEntry = _a.sent();
                    if (!userEntry)
                        return [2 /*return*/, null];
                    // Step 3: close service client, open new one for user bind
                    // (ldapjs won't allow re-binding after search)
                    client.destroy();
                    userClient = createClient();
                    return [4 /*yield*/, bindUser(userClient, userEntry.dn, password)];
                case 4:
                    _a.sent();
                    // Step 4: get groups (on the user-bound client if possible, or service client)
                    // Re-bind as service for group search
                    userClient.destroy();
                    groupClient = createClient();
                    return [4 /*yield*/, bindService(groupClient)];
                case 5:
                    _a.sent();
                    return [4 /*yield*/, getUserGroups(groupClient, userEntry.dn)];
                case 6:
                    groups = _a.sent();
                    groupClient.destroy();
                    attrs = userEntry.attrs;
                    uid = attrs[LDAP_UID_ATTR] || username;
                    email = attrs[LDAP_MAIL_ATTR] || "".concat(username, "@ldap.local");
                    displayName = attrs[LDAP_NAME_ATTR] || attrs["cn"] || uid;
                    return [2 /*return*/, {
                            uid: uid,
                            email: email,
                            displayName: displayName,
                            groups: groups,
                            role: mapRole(groups),
                        }];
                case 7:
                    e_1 = _a.sent();
                    client.destroy();
                    return [2 /*return*/, null];
                case 8: return [2 /*return*/];
            }
        });
    });
}
// --- Check if LDAP is configured ---
function isLDAPEnabled() {
    return LDAP_ENABLED;
}
