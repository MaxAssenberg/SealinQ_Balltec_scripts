#!/usr/bin/env python3

import socket
import time
import requests
import json
import os
import subprocess
import sys

# InfluxDB config
influx_url = 'http://influxdb:8086'
influx_org = 'HIL'
influx_bucket = 'Balltec'
influx_token = 'ci-PRoiUGgN1cRSgi5K0Td5rSeZ2evKxjBAvENGZ57RINbdji3qTNP2uvnix12AuTnA1pdseN--bnYa9zqzz_Q=='

# UDP device
UDP_IP = "10.8.0.109"
UDP_PORT = 5000

# Load lookup tables from JSON files
def load_lookup_tables():
    try:
        with open("lookup_table_1.json") as f1:
            lookup1 = json.load(f1)
        with open("lookup_table_2.json") as f2:
            lookup2 = json.load(f2)
        print("Loaded lookup tables successfully.")
        return lookup1, lookup2
    except Exception as e:
        print(f"Failed to load lookup tables: {e}")
        exit(1)

# Ping target 10 times before giving up
def ping_check(target_ip, count=10):
    print(f"Pinging {target_ip} up to {count} times...")
    success = False
    for attempt in range(count):
        print(f"Ping attempt {attempt+1}...")
        try:
            result = subprocess.run(["ping", "-c", "1", "-W", "1", target_ip],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            if result.returncode == 0:
                print("Ping successful.")
                success = True
                break
        except Exception as e:
            print(f"Ping error: {e}")
        time.sleep(1)
    if not success:
        print(f"Target {target_ip} not reachable after {count} attempts. Exiting.")
        sys.exit(1)

lookup_table_1, lookup_table_2 = load_lookup_tables()

# Create and bind UDP socket to local port 5000
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", 5000))
sock.settimeout(10)
print("UDP client bound to local port 5000")

# Handshake logic
def send_and_wait_for_ok(command, retries=3):
    for attempt in range(1, retries + 1):
        print(f"[Attempt {attempt}] Sending: {command.strip()}")
        sock.sendto(command.encode(), (UDP_IP, UDP_PORT))
        try:
            response, _ = sock.recvfrom(1024)
            decoded = response.decode()
            print(f"Handshake response: {repr(decoded)}")
            if decoded == "R ok\n" or decoded == "R ok\\n":
                return True
            else:
                print("Unexpected response")
        except socket.timeout:
            print("Timeout waiting for response.")
        time.sleep(1)
    return False

def perform_handshake():
    commands = [
        "CAN 1 STOP\n",
        "CAN 1 INIT STD 250\n",
        "CAN 1 FILTER CLEAR\n",
        "CAN 1 FILTER ADD STD 000 000\n"
    ]
    for cmd in commands:
        if not send_and_wait_for_ok(cmd):
            print(f"Handshake failed at: {cmd.strip()}")
            return False
    print("Sending: CAN 1 START")
    sock.sendto(b"CAN 1 START\n", (UDP_IP, UDP_PORT))
    print("Handshake complete.")
    return True

# Data parse + Influx write
def handle_udp_data(data):
    try:
        msg = data.decode().strip().split()
        if len(msg) < 12:
            print("Too short, skipping")
            return

        mux = msg[6]                    # Byte 2: mux byte
        data_bytes = msg[7:13]         # Bytes 3–7 (5 data bytes)

        table = lookup_table_1 if mux == "01" else lookup_table_2 if mux == "02" else None
        if not table:
            print(f"Unknown mux byte: {mux}")
            return

        fields = {}
        for idx, (key, field) in enumerate(table["fields"].items()):
            byte_index = int(key.replace("byte", ""))
            if byte_index >= len(msg):
                continue
            hex_val = msg[byte_index + 4]  # +4 offset: msg[4] = byte0 (startup0)
            if field.get("type") == "bitmask":
                bit_labels = field.get("bitflags", {})
                val = int(hex_val, 16)
                flags = [label for bit, label in bit_labels.items() if val & (1 << int(bit))]
                fields[field["name"]] = ' | '.join(flags) if flags else "none"
            else:
                val = eval(field["formula"].replace("hex", f"'{hex_val}'"))
                fields[field["name"]] = round(val, 2) if isinstance(val, float) else val

        if not fields:
            return

        line = f"udp_stream,source={mux} " + ",".join(
            f"{k.replace(' ', '_').replace('–','-')}={json.dumps(v)}" for k, v in fields.items()
        )
        timestamp = int(time.time() * 1e9)
        line += f" {timestamp}"

        r = requests.post(
            f"{influx_url}/api/v2/write?org={influx_org}&bucket={influx_bucket}&precision=ns",
            headers={"Authorization": f"Token {influx_token}"},
            data=line
        )
        if not r.ok:
            print(f"Influx write failed: {r.status_code} {r.text}")
        else:
            print(f"Wrote to Influx: {line}")

    except Exception as e:
        print(f"Error parsing or writing: {e}")

# Main loop
if __name__ == "__main__":
    ping_check(UDP_IP)
    if not perform_handshake():
        exit(1)

    print("Listening for UDP stream...")
    while True:
        try:
            data, _ = sock.recvfrom(1024)
            print(f"[RECV] {len(data)} bytes: {data}")
            handle_udp_data(data)
        except Exception as e:
            print(f"Receive error: {e}")

