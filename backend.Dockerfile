FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose API port
EXPOSE 8000

# Run the API server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
