# Use official Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements.txt first and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app files
COPY main.py .
COPY parser.py .

# Default command to run your app
CMD ["python", "main.py"]
