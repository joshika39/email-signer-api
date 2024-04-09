FROM python:3.10

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY routes.py .
COPY backend/*.py backend/
COPY backend/*.html backend/
COPY backend/*.css backend/

# The keys/ directory is mounted as a volume from the host
# so that the keys are not stored in the image
VOLUME /app/keys

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
