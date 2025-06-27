FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install dependencies including ping
RUN apt-get update && apt-get install -y iputils-ping && rm -rf /var/lib/apt/lists/*

# Copy files
COPY udp_parser_lookup.py .
COPY lookup_table_1.json .
COPY lookup_table_2.json .
COPY requirements.txt .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Expose UDP port
EXPOSE 5000/udp

# Run the script
CMD ["python", "udp_parser_lookup.py"]
