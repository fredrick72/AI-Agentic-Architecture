FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev freetds-dev \
    && rm -rf /var/lib/apt/lists/* \
    && printf '[global]\ntls version = auto\ntls verify cert = no\n' > /etc/freetds/freetds.conf

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8010

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010"]
