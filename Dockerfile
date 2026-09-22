ARG BUILD_IMAGE="artefact.skao.int/ska-build-python:1.0.2"
ARG BASE_IMAGE="artefact.skao.int/ska-tango-images-tango-python:0.5.1"
FROM $BUILD_IMAGE AS buildenv

FROM $BASE_IMAGE

USER root

COPY --from=buildenv /usr/lib/ /usr/lib/
COPY --from=buildenv /usr/bin/ /usr/bin/
COPY --from=buildenv /root/.local/ /root/.local/
ENV PATH=$PATH:/root/.local/bin
RUN apt-get update && \
      apt-get install -y --no-install-recommends \
      ca-certificates \
  && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*
ENV SETUPTOOLS_USE_DISTUTILS=stdlib

RUN poetry config virtualenvs.create false

WORKDIR /app

COPY --chown=tango:tango . /app
# Install runtime dependencies and the app
RUN poetry install --only main \
 && rm /usr/bin/python && ln -s /usr/bin/python3 /usr/bin/python
USER tango
