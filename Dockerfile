FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt config.example.yaml ./
RUN pip install -r requirements.txt

COPY . .
RUN cp config.example.yaml config.yaml \
    && mkdir -p /app/data \
    && useradd --system --uid 1000 --home-dir /app --shell /usr/sbin/nologin crunchy \
    && chown -R crunchy:root /app

COPY docker/entrypoint.sh /usr/local/bin/crunchy-entrypoint
RUN chmod +x /usr/local/bin/crunchy-entrypoint

USER crunchy

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/crunchy-entrypoint"]
CMD ["status"]
