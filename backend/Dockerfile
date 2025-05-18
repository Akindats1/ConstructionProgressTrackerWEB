# Use official Python image for Flask app
FROM python:3.13-alpine3.21 as flask-build

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Use official Nginx image for serving and proxy
FROM nginx:alpine

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy Flask app from previous stage
COPY --from=flask-build /app /app

# Install Gunicorn
RUN apk add --no-cache python3 py3-pip && \
    pip3 install --no-cache-dir gunicorn

# Expose port (Heroku will assign actual port)
EXPOSE 80

# Start script to replace $PORT and run Nginx + Gunicorn
CMD sh -c "envsubst '\$PORT' < /etc/nginx/conf.d/default.conf > /etc/nginx/conf.d/default.conf && \
    gunicorn -b 127.0.0.1:5000 app:app & nginx -g 'daemon off;'"
