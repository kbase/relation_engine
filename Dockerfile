FROM python:3.10-alpine

ARG DEVELOPMENT
ARG BUILD_DATE
ARG VCS_REF
ARG BRANCH=develop

COPY requirements.txt dev-requirements.txt /tmp/
WORKDIR /app

# Install dockerize
ENV DOCKERIZE_VERSION v0.6.1
RUN apk --update add --virtual build-dependencies curl tar gzip && \
    curl -o dockerize.tar.gz \
      https://raw.githubusercontent.com/kbase/dockerize/master/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz && \
    tar -C /usr/local/bin -xvzf dockerize.tar.gz && \
    rm dockerize.tar.gz && \
    apk del build-dependencies

# Install dependencies
RUN apk --update add --virtual build-dependencies build-base python3-dev && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    if [ "$DEVELOPMENT" ]; then pip install --no-cache-dir -r /tmp/dev-requirements.txt; fi && \
    apk del build-dependencies && \
    pip install types-requests types-PyYAML

COPY . /app

# Create tarball of the spec directory so we have it cached in the image
RUN tar czvf /opt/spec.tar.gz /app/spec
ENV SPEC_RELEASE_PATH=/opt/spec.tar.gz

LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.vcs-url="https://github.com/kbase/relation_engine_api" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.schema-version="1.0.0-rc1" \
      us.kbase.vcs-branch=$BRANCH \
      maintainer="KBase Team"

EXPOSE 5000
ENTRYPOINT ["/usr/local/bin/dockerize"]
CMD ["sh", "-x", "/app/scripts/start_server.sh"]
