FROM python:3.13-alpine

WORKDIR /app

RUN apt-get update && apt-get install -y g++ unixodbc-dev

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
