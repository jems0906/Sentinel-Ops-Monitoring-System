FROM python:3.12-alpine3.22

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apk update \
    && apk upgrade \
    && rm -rf /var/cache/apk/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN addgroup -S app && adduser -S app -G app

COPY app ./app
COPY config ./config
COPY data ./data
RUN chown -R app:app /app

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
