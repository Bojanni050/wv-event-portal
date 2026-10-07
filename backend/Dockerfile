FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
# Alleen runtime-pakketten installeren (tests/lint overslaan)
RUN sed '/^# Tests/,$d' requirements.txt > req.prod.txt \
 && pip install --no-cache-dir -r req.prod.txt
COPY . .
RUN chmod +x entrypoint.sh
ENV PORT=8000
EXPOSE 8000
# entrypoint.sh: alembic upgrade head + uvicorn
CMD ["./entrypoint.sh"]
