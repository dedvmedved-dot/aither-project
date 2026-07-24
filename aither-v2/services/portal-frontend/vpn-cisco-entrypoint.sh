#!/bin/bash
set -e
FIRST=1
while true; do
  [ "$FIRST" = "1" ] && { ip link del tun0 2>/dev/null; ip route flush dev tun0 2>/dev/null; FIRST=0; }
  echo "$(date) Starting OC..."
  expect -c '
    set timeout 30
    spawn openconnect 95.137.2.98 --user=ZKO_ADMIN --servercert pin-sha256:DYWfgV3j7en1oL9TOy7Yd2vA2pduzFn0RSkmydfdwGg= --no-dtls --protocol=anyconnect --reconnect-timeout=30
    expect {
      Password: { send "'"$OPENCONNECT_PASSWORD"'\r"; exp_continue }
      Group: { send "'"$OPENCONNECT_GROUP"'\r"; exp_continue }
      CSTP { puts CONNECTED }
    }
    set timeout -1
    expect {
      timeout { exp_continue }
      eof {}
    }
  '
  echo "$(date) OC exit, reconnecting in 5s..."
  sleep 5
done
