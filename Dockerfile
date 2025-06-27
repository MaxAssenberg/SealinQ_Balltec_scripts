FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy application files
COPY udp_parser_lookup_env.py .
COPY lookup_table_1.json .
COPY lookup_table_2.json .
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose UDP port (optional default)
EXPOSE 5000/udp

# Run the main script
CMD ["python", "udp_parser_lookup_env.py"]
