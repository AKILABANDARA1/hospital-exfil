FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data/uploads && chown -R 10001:10001 /data

RUN groupadd -g 10001 appuser && useradd -u 10001 -g appuser -s /bin/sh -m appuser

USER 10001

EXPOSE 8080

CMD ["uvicorn", "exfil_receiver:app", "--host", "0.0.0.0", "--port", "8080"]
