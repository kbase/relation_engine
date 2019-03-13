FROM python:3.7-alpine

ARG DEVELOPMENT

COPY requirements.txt dev-requirements.txt /tmp/
WORKDIR /app

# Install dependencies
RUN apk --update add --virtual build-dependencies python-dev build-base && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    if [ "$DEVELOPMENT" ]; then pip install --no-cache-dir -r /tmp/dev-requirements.txt; fi && \
    apk del build-dependencies

# Run the app
COPY . /app

CMD ["sh", "scripts/start_server.sh"]
