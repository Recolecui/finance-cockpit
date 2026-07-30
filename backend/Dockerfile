FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "python -c 'from app.database import engine,Base; from app.models import *; Base.metadata.create_all(bind=engine)' && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
