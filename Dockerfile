FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=/app
EXPOSE 8200
CMD ["uvicorn", "src.backend.server:app", "--host", "0.0.0.0", "--port", "8200"]
