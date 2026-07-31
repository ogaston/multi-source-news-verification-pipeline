FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ADMIN_HOST=0.0.0.0 \
    ADMIN_PORT=7001

WORKDIR /app

COPY admin/requirements.txt ./admin-requirements.txt
RUN pip install --no-cache-dir -r admin-requirements.txt

COPY common ./common
COPY admin ./admin

EXPOSE 7001

CMD ["uvicorn", "admin.app:app", "--host", "0.0.0.0", "--port", "7001"]
