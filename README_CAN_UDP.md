# CAN UDP Client (Handshake + Stream + Stop Command)

This project contains two Python scripts for interacting with a device over UDP on port `5000`. The device expects specific ASCII commands to initiate CAN communication and will stream UDP data once started.

---

## 📂 Scripts

### 1. `udp_handshake_and_listen.py`

This script:
- Binds to local UDP port `5000`
- Sends a 4-step ASCII handshake to the device
- Waits for `"R ok\n"` responses after the first 3 steps
- Sends the final `"CAN 1 START\n"` without expecting confirmation
- After handshake, continuously listens to incoming UDP packets and prints their raw contents to the console

#### 💬 Sent Commands
```
CAN 1 INIT STD 250\n
CAN 1 FILTER CLEAR\n
CAN 1 FILTER ADD STD 000 000\n
CAN 1 START\n
```

#### 🖥️ Run it with:
```bash
python3 udp_handshake_and_listen.py
```

#### 🔧 Customize target:
Edit `UDP_IP` and `UDP_PORT` in the script if your target changes:
```python
UDP_IP = "10.8.0.109"
UDP_PORT = 5000
```

---

### 2. `send_can_stop.py`

This **minimal** script:
- Binds to UDP port `5000`
- Sends a single command:
```
CAN 1 STOP\n
```
- Exits after sending

#### 🖥️ Run it with:
```bash
python3 send_can_stop.py
```

---

## 📦 Dependencies

Both scripts use only the Python standard library. No external packages are required.

Tested with **Python 3.6+**.

---

## 📡 Use Case

These scripts are designed for environments where a CAN device is controlled over a UDP interface. The full script sets up communication and logs data, while the stop script safely stops the CAN interface on the device.

---

## 🔒 Safety Tip

Avoid sending `"CAN 1 START\n"` unless your script is actively bound to port `5000` and listening. Otherwise, the device may send UDP packets to an unbound port, triggering ICMP "unreachable" errors.

---

## 🛠️ Next Steps

You may extend this setup to:
- Parse UDP messages and decode CAN frames
- Forward the data to InfluxDB
- Run as a Docker container or systemd service
