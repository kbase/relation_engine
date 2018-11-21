FROM python:3.7-alpine

ARG DEVELOPMENT
ARG spec_url=https://github.com/kbase/relation_engine_spec
ARG spec_path=/spec

COPY requirements.txt /app/requirements.txt
COPY dev-requirements.txt /app/dev-requirements.txt
WORKDIR /app

# Install dependencies
RUN apk --update add --virtual build-dependencies python-dev build-base && \
    pip install --upgrade pip && \
    pip install --upgrade --no-cache-dir -r requirements.txt && \
    if [ "$DEVELOPMENT" ]; then pip install -r dev-requirements.txt; fi && \
    apk del build-dependencies

# Run the app
COPY . /app

CMD ["sh", "scripts/start_server.sh"]
