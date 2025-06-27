FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy local files
COPY udp_parser_lookup.py .
COPY lookup_table_1.json .
COPY lookup_table_2.json .
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose UDP port
EXPOSE 5000/udp

# Run the script
CMD ["python", "udp_parser_lookup.py"]
