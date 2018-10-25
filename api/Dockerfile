FROM python:3.7-alpine

COPY requirements.txt /app/requirements.txt
COPY dev-requirements.txt /app/dev-requirements.txt
WORKDIR /app

# Install dependencies
RUN apk --update add make
RUN apk --update add --virtual build-dependencies python-dev build-base && \
    pip install --upgrade pip && \
    pip install --upgrade --no-cache-dir \
      --extra-index-url https://pypi.anaconda.org/kbase/simple \
      -r requirements.txt && \
    pip install -r dev-requirements.txt && \
    apk del build-dependencies

# Run the app
COPY . /app

ENV PYTHONUNBUFFERED="true"

CMD ["gunicorn", "--worker-class", "gevent", "--timeout", "1800", "--workers", "17", "-b", ":5000", "--reload", "src.relation_engine_api.__main__:app"]
