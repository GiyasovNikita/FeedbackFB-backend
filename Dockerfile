FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app/src

EXPOSE 8000

ARG SERVICE=backend

CMD if [ "$SERVICE" = "backend" ]; then uvicorn main:app --host 0.0.0.0 --port 8000; else python bot.py; fi
