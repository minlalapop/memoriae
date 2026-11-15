FROM python:3.12.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml requirements.lock README.md ./
COPY app ./app
COPY frontend ./frontend
COPY migrations ./migrations
COPY alembic.ini demo.py ./
COPY tests ./tests

RUN python -m pip install --no-cache-dir --constraint requirements.lock '.[test,model]'

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
