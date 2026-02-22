FROM python:3.9-slim
WORKDIR /app
COPY webhook_assistant.py /app/
RUN pip install --no-cache-dir flask google-cloud-texttospeech requests
ENV PORT 8080
CMD ["python","webhook_assistant.py"]
