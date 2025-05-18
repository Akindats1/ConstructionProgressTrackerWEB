# Use official lightweight Python image with pip pre-installed
FROM python:3.13-alpine

# Set working directory inside the container
WORKDIR /app

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose the port your Flask app runs on
EXPOSE 5000

# Run the Flask app using Gunicorn with 4 worker processes
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
