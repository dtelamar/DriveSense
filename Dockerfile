FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements-api.txt ./
RUN python -m pip install --no-cache-dir -r requirements-api.txt

RUN useradd --create-home --uid 10001 drivesense

COPY --chown=drivesense:drivesense \
    api.py \
    analyzer.py \
    data_loader.py \
    metrics.py \
    ./

USER drivesense

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
