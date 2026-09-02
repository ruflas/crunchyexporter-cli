FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install -r requirements.txt

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY src ./src
COPY config.example.yaml ./config.example.yaml

RUN mkdir -p /app/data \
    && useradd --system --create-home --home-dir /app --shell /usr/sbin/nologin crunchy \
    && chown -R crunchy:root /app

USER crunchy

ENTRYPOINT ["python", "src/main.py"]
CMD ["status"]
