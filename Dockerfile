FROM python:3.11

RUN mkdir -p /app
WORKDIR /app

RUN pip install --upgrade pip
RUN pip install "poetry==1.7.1"
COPY poetry.lock pyproject.toml /app/

# Project initialization:
RUN poetry config virtualenvs.create false \
  && poetry install --no-dev --no-interaction --no-ansi

ADD vision-ai-service /app/vision-ai-service

EXPOSE 8080

CMD gunicorn  "photo_service_gui:create_app"  --config=vision-ai-service/gunicorn_config.py --worker-class aiohttp.GunicornWebWorker
