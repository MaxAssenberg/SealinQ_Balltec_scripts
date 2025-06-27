from azure.iot.device import IoTHubModuleClient
import json
import socket
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS
import time
import os

# InfluxDB config via environment
influx_url = os.getenv("INFLUX_URL", "http://172.28.2.35:8086")
influx_org = os.getenv("INFLUX_ORG", "HIL")
influx_bucket = os.getenv("INFLUX_BUCKET", "Balltec")
influx_token = os.getenv("INFLUX_TOKEN", "ci-PRoiUGgN1cRSgi5K0Td5rSeZ2evKxjBAvENGZ57RINbdji3qTNP2uvnix12AuTnA1pdseN--bnYa9zqzz_Q==")

# UDP config via environment
UDP_IP = os.getenv("UDP_IP", "10.8.0.109")
UDP_PORT = int(os.getenv("UDP_PORT", 5000))

client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)
write_api = client.write_api(write_options=SYNCHRONOUS)

# Azure IoT Hub client
iot_client = IoTHubModuleClient.create_from_edge_environment()

def send_telemetry(data_dict):
    try:
        msg = json.dumps(data_dict)
        iot_client.send_message(msg)
    except Exception as e:
        print(f"[AzureIoT] Error sending telemetry: {e}")

def parse_message(raw_data):
    try:
        fields = raw_data.strip().split()
        if len(fields) < 13:
            return None

        data = {
            "battery_voltage": int(fields[8], 16),
            "temperature": int(fields[9], 16),
            "timestamp": time.time_ns()
        }
        return data
    except Exception as e:
        print(f"[Parser] Failed to parse message: {e}")
        return None

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"[UDP] Listening on {UDP_IP}:{UDP_PORT}...")

    while True:
        data, addr = sock.recvfrom(1024)
        line = data.decode("utf-8").strip()
        print(f"[RECV] {line}")

        parsed = parse_message(line)
        if parsed:
            point = {
                "measurement": "udp_parser",
                "tags": {"source": "udp-parser"},
                "fields": {
                    "battery_voltage": parsed["battery_voltage"],
                    "temperature": parsed["temperature"]
                },
                "time": parsed["timestamp"]
            }

            try:
                write_api.write(bucket=influx_bucket, org=influx_org, record=point)
                send_telemetry(point)
                print("[LOG] Written to InfluxDB and sent to Azure IoT Hub")
            except Exception as e:
                print(f"[Error] Writing failed: {e}")

if __name__ == "__main__":
    main()
