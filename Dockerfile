FROM python:3.10-alpine

WORKDIR /usr/src/app

COPY requirements.txt .

RUN apk --no-cache add sqlite && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "main:app"]
