FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    API_HOST=0.0.0.0 \
    API_PORT=7002

WORKDIR /app

COPY api/requirements.txt ./api-requirements.txt
RUN pip install --no-cache-dir -r api-requirements.txt

COPY common ./common
COPY api ./api

EXPOSE 7002

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "7002"]
