#!/usr/bin/env python3

import socket
import time
import requests
import json
import subprocess
import sys

# InfluxDB config
influx_url = 'http://10.0.4.200:8086'
influx_org = 'seaqualize'
influx_bucket = 'Balltec'
influx_token = 'tBWR3s8t4zdmzCBxY1U5qTUJuJUmQW'

# UDP device
UDP_IP = "10.1.21.2"
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
    for attempt in range(count):
        print(f"Ping attempt {attempt + 1}...")
        try:
            result = subprocess.run(["ping", "-c", "1", "-W", "1", target_ip],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            if result.returncode == 0:
                print("Ping successful.")
                return
        except Exception as e:
            print(f"Ping error: {e}")
        time.sleep(1)
    print(f"Target {target_ip} not reachable after {count} attempts. Exiting.")
    sys.exit(1)

# Perform CAN initialization handshake
def perform_handshake(sock):
    commands = [
        "CAN 1 STOP\n",
        "CAN 1 INIT STD 250\n",
        "CAN 1 FILTER CLEAR\n",
        "CAN 1 FILTER ADD STD 000 000\n"
    ]
    for cmd in commands:
        print(f"Sending: {cmd.strip()}")
        sock.sendto(cmd.encode(), (UDP_IP, UDP_PORT))
        if "STOP" not in cmd:
            if not send_and_wait_for_ok(sock, cmd):
                print(f"Handshake failed at: {cmd.strip()}")
                return False
        time.sleep(0.2)
    print("Sending: CAN 1 START")
    sock.sendto(b"CAN 1 START\n", (UDP_IP, UDP_PORT))
    print("Handshake complete.")
    return True

# Only wait for "R ok" — do not re-send
def send_and_wait_for_ok(sock, command, retries=3):
    for attempt in range(1, retries + 1):
        print(f"[Attempt {attempt}] Waiting for response to: {command.strip()}")
        try:
            response, _ = sock.recvfrom(1024)
            decoded = response.decode()
            print(f"Handshake response: {repr(decoded)}")
            if decoded.strip() == "R ok":
                return True
        except socket.timeout:
            print("Timeout waiting for response.")
        time.sleep(1)
    return False

# Parse incoming UDP message and write to InfluxDB
def handle_udp_data(data, lookup_table_1, lookup_table_2):
    try:
        msg = data.decode().strip().split()
        if len(msg) < 12:
            print("Too short, skipping")
            return

        mux = msg[6]
        data_bytes = msg[7:13]

        table = lookup_table_1 if mux == "01" else lookup_table_2 if mux == "02" else None
        if not table:
            print(f"Unknown mux byte: {mux}")
            return

        fields = {}
        for idx, (key, field) in enumerate(table["fields"].items()):
            byte_index = int(key.replace("byte", ""))
            if byte_index >= len(msg):
                continue
            hex_val = msg[byte_index + 4]
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
