# Production Dockerfile for the Flask companion app
FROM python:3.13-slim AS builder

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.13-slim AS runner

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production

RUN useradd --create-home --uid 10001 appuser
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY src ./src

USER appuser
EXPOSE 8000
CMD ["gunicorn", "--chdir", "src", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "wsgi:app"]
