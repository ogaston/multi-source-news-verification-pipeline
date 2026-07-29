FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DB_NAME=/data/dominican_news_repository.db \
    ADMIN_HOST=0.0.0.0 \
    ADMIN_PORT=8001

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY __init__.py auth.py models.py views.py app.py ./admin/

EXPOSE 8001

CMD ["uvicorn", "admin.app:app", "--host", "0.0.0.0", "--port", "8001"]
