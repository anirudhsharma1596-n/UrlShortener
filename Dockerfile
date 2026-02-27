# Dockerfile
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first — Docker caches this layer
# If requirements don't change, Docker skips reinstalling on rebuild
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of our code
COPY . .

# Run the FastAPI app via uvicorn
# --host 0.0.0.0 means "accept connections from outside the container"
# --reload means "restart when code changes" (development only)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]