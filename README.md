# CAN UDP Client with InfluxDB Export (Dockerized for IoT Edge)

This project provides a complete pipeline for reading UDP-based CAN data from a device, parsing it, and writing it to InfluxDB — all deployable via Docker and Azure IoT Edge.

---

## 📂 Scripts

### `udp_parser_lookup.py`

This script:
- Pings the target device (`10.8.0.109`) **up to 10 times**
- Only proceeds if the device responds to ping
- Sends a 4-step ASCII UDP handshake to the device
- Waits for `"R ok\n"` responses
- Sends `"CAN 1 START\n"` to initiate data stream
- Listens on UDP port `5000`
- Parses incoming UDP messages using two JSON lookup tables:
  - `lookup_table_1.json`
  - `lookup_table_2.json`
- Pushes decoded metrics to **InfluxDB v2**

### 🔧 Configuration

Inside the script, set:

```python
UDP_IP = "10.8.0.109"
UDP_PORT = 5000
influx_url = 'http://172.28.2.35:8086'
influx_org = 'HIL'
influx_bucket = 'Balltec'
influx_token = 'ci-PRoiUGgN1cRSgi5K0Td5rSeZ2evKxjBAvENGZ57RINbdji3qTNP2uvnix12AuTnA1pdseN--bnYa9zqzz_Q=='
```

> ⚠️ If the ping fails 10 times, the script exits with a clear log message:  
> `Target 10.8.0.109 not reachable after 10 attempts. Exiting.`

---

## 🐳 Docker Support

### 🛠️ Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY udp_parser_lookup.py .
COPY lookup_table_1.json .
COPY lookup_table_2.json .
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000/udp

CMD ["python", "udp_parser_lookup.py"]
```

---

### 🔁 GitHub Actions: `.github/workflows/push-ghcr.yml`

Every push to `main` triggers:
- Docker build
- Push to GitHub Container Registry (GHCR)

Workflow sample:
```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main]

jobs:
  build-and-push:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/seaqualize/sealinq_balltec_scripts/udp-parser-balltec:latest
```

---

## 📦 Deployment to Azure IoT Edge

1. Add the module to your IoT Edge deployment manifest:
   ```json
   "udp-parser": {
     "version": "1.0",
     "type": "docker",
     "status": "running",
     "restartPolicy": "always",
     "settings": {
       "image": "ghcr.io/seaqualize/sealinq_balltec_scripts/udp-parser-balltec:latest",
       "createOptions": "{}"
     }
   }
   ```

2. Make sure `SLQInfluxDbWriter` is running and exposes port `8086`.

3. Restart `udp-parser` via Azure or:
   ```bash
   sudo iotedge restart udp-parser
   ```

---

## 🧪 Debugging from Inside the Container

```bash
sudo docker exec -it udp-parser /bin/sh
ping SLQInfluxDbWriter
curl http://SLQInfluxDbWriter:8086/health
```

---

## 🧠 Troubleshooting

- ❌ `Connection refused` → InfluxDB not running or wrong hostname
- ❌ `Name or service not known` → wrong module name, fix `influx_url`

---

## 📈 InfluxDB Output Example

Data points will be written using line protocol with proper measurement and tags based on decoded values.

---

Let me know if you want the `send_can_stop.py` integrated into Docker as well.
