FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc g++ git && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
EXPOSE 8080
CMD exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}
