"""
Reservation Reaper — cleans up stuck billing reserves.
Finds `reserve` operations in billing_ledger without matching `settle` or `refund`,
and refunds them if older than a configurable threshold.
"""
import os
import time
import psycopg2
import psycopg2.pool

PG_URL = os.environ.get("PG_URL", "postgresql://aither@postgres:5432/aither")
REAP_INTERVAL = int(os.environ.get("REAP_INTERVAL", "60"))  # seconds between sweeps
STUCK_THRESHOLD = int(os.environ.get("STUCK_THRESHOLD", "300"))  # seconds before refund

db_pool = psycopg2.pool.SimpleConnectionPool(1, 3, PG_URL)


def reap():
    """Find and refund stuck reservations."""
    conn = db_pool.getconn()
    try:
        with conn:
            with conn.cursor() as cur:
                # Find reserves without settle/refund, older than threshold
                cur.execute("""
                    SELECT r.id, r.org_id, r.reference, r.amount, r.created_at
                    FROM billing_ledger r
                    LEFT JOIN billing_ledger s
                        ON s.reference = r.reference AND s.operation = 'settle'
                    LEFT JOIN billing_ledger f
                        ON f.reference = r.reference AND f.operation = 'refund'
                    WHERE r.operation = 'reserve'
                      AND s.id IS NULL
                      AND f.id IS NULL
                      AND r.created_at < now() - interval '%s seconds'
                    ORDER BY r.created_at
                """, (str(STUCK_THRESHOLD),))

                stuck = cur.fetchall()
                if not stuck:
                    return 0

                refunded = 0
                for (ledger_id, org_id, ref, amount, created_at) in stuck:
                    # Refund: decrease reserved by amount
                    cur.execute(
                        """UPDATE billing_accounts
                           SET reserved = reserved - %s, updated_at = now()
                           WHERE org_id = %s AND reserved >= %s
                           RETURNING balance""",
                        (amount, org_id, amount))
                    row = cur.fetchone()
                    if not row:
                        continue  # reserved < amount, skip
                    new_balance = row[0]
                    cur.execute(
                        """INSERT INTO billing_ledger
                           (org_id, amount, operation, reference, balance_after)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (org_id, amount, "refund", ref, new_balance))
                    refunded += 1

                return refunded

    except Exception as e:
        conn.rollback()
        print(f"[Reaper] Error: {e}", flush=True)
        return -1
    finally:
        db_pool.putconn(conn)


def reaper_loop():
    """Run reaper in a loop."""
    print(f"[Reaper] Started (interval={REAP_INTERVAL}s, threshold={STUCK_THRESHOLD}s)", flush=True)
    while True:
        time.sleep(REAP_INTERVAL)
        try:
            count = reap()
            if count > 0:
                print(f"[Reaper] Refunded {count} stuck reservation(s)", flush=True)
            elif count == 0:
                pass  # all clean
        except Exception as e:
            print(f"[Reaper] Loop error: {e}", flush=True)


if __name__ == "__main__":
    reaper_loop()
