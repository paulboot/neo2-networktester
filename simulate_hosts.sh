#!/bin/bash

# Logging function
log() {
    echo "$1"
    logger -t simulate_hosts "$1"
}

# Set main interface name (adjust if needed)
MAIN_IF="end0"
SUBNET="192.168.3"
START_IP=180
COUNT=6
BASE_MAC="02:aa:bb:cc:dd"
EXPECTED_GW_IP="192.168.3.1"
EXPECTED_GW_MAC="00:0d:b9:4b:59:d4"

case "$1" in
  start)
    log "Starting simulated hosts setup..."

    # Check default gateway
    GW_IP=$(ip route | awk '/default/ {print $3}')
    if [ "$GW_IP" != "$EXPECTED_GW_IP" ]; then
        log "Default gateway IP is $GW_IP, expected $EXPECTED_GW_IP. Exiting."
        exit 1
    fi

    # Try to resolve MAC if not in ARP cache
    ip neigh show "$EXPECTED_GW_IP" | grep -q "$EXPECTED_GW_MAC" || ping -c1 "$EXPECTED_GW_IP" >/dev/null
    GW_MAC=$(ip neigh show "$EXPECTED_GW_IP" | awk '{print $5}')

    if [ "$GW_MAC" != "$EXPECTED_GW_MAC" ]; then
        log "Default gateway MAC is $GW_MAC, expected $EXPECTED_GW_MAC. Exiting."
        exit 1
    fi

    log "Gateway check passed: $GW_IP ($GW_MAC)"

    for i in $(seq 0 $((COUNT - 1))); do
        IF_NAME="macvlan$i"
        IP="$SUBNET.$((START_IP + i))"
        MAC="$BASE_MAC:$(printf "%02x" $i)"

        log "Creating $IF_NAME with IP $IP and MAC $MAC"

        # Set MAC during link creation to avoid conflicts
        sudo ip link add $IF_NAME link $MAIN_IF address $MAC type macvlan mode bridge || {
            log "Failed to create link $IF_NAME"
            exit 1
        }
        sudo ip link set $IF_NAME up || {
            log "Failed to bring up $IF_NAME"
            exit 1
        }
        sudo ip addr add $IP/24 dev $IF_NAME || {
            log "Failed to assign IP to $IF_NAME"
            exit 1
        }

        sudo ip netns del ns$i 2>/dev/null
        sudo ip netns add ns$i || { log "Failed to create netns ns$i"; exit 1; }
        sudo ip link set $IF_NAME netns ns$i || { log "Failed to move $IF_NAME to ns$i"; exit 1; }

        sudo ip netns exec ns$i ip link set lo up
        sudo ip netns exec ns$i ip link set $IF_NAME up
        sudo ip netns exec ns$i ip addr add $IP/24 dev $IF_NAME

        cat <<EOF | sudo tee /tmp/app$i.py >/dev/null
from flask import Flask
app = Flask(__name__)
@app.route('/')
def index():
    return "Hello from $IP"
if __name__ == '__main__':
    app.run(host='$IP', port=80)
EOF

        sudo ip netns exec ns$i python3 /tmp/app$i.py > /tmp/simhost$i.log 2>&1 &
        echo $! | sudo tee /tmp/simhost$i.pid >/dev/null
        log "Started Flask app on ns$i at $IP"
    done

    log "All simulated hosts started."
    sleep infinity
    ;;

  stop)
    log "Stopping simulated hosts..."
    for i in $(seq 0 $((COUNT - 1))); do
        IF_NAME="macvlan$i"
        PID_FILE="/tmp/simhost$i.pid"
        APP_FILE="/tmp/app$i.py"

        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            sudo kill "$PID" 2>/dev/null && log "Stopped app on ns$i (PID $PID)"
            sudo rm -f "$PID_FILE"
        fi

        sudo ip netns del ns$i 2>/dev/null
        sudo ip link delete $IF_NAME 2>/dev/null
        sudo rm -f "$APP_FILE" "/tmp/simhost$i.log"
    done
    ;;

  *)
    log "Usage: $0 {start|stop}"
    exit 1
    ;;
esac
