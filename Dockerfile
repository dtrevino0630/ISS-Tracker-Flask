# Use a slim Python image for smaller size
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy only requirements first (optimizes caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Expose Flask's default port
EXPOSE 5000

# Set environment variables for Flask
ENV FLASK_APP=iss_tracker.py
ENV FLASK_RUN_HOST=0.0.0.0

# Run the Flask application
CMD ["flask", "run"]

