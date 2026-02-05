# backend/Dockerfile
# Base image - using the full version (Heavy)
FROM python:3.12

# Set working directory inside the container
WORKDIR /app

# Copy dependency file
# writing to a separate layer to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on (Note: This is just documentation; actual port mapping is done in docker-compose.yml)
EXPOSE 8000

# Command to run the application
# "uvicorn": The high-performance server that can run Async Python.
# "main:app": Refers to the 'app' instance in the 'main.py' file.
# 0.0.0.0 means "Accept connections from outside" (eg. from the host machine and other containers).
# --reload: Automatically reloads the server when code changes (useful for development).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]