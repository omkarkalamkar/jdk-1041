ARG BUILD_IMAGE=artefact.skao.int/ska-build-python:0.1.1
ARG BASE_IMAGE=artefact.skao.int/ska-tango-images-tango-python:0.1.0

FROM $BUILD_IMAGE AS buildenv
WORKDIR /app
COPY . .
RUN poetry install --no-interaction --only main

FROM $BASE_IMAGE
ENV SETUPTOOLS_USE_DISTUTILS=stdlib
WORKDIR /app

COPY --from=buildenv --chown=tango:tango /app /app
RUN [ -e /usr/bin/python ] || ln -s /usr/bin/python3 /usr/bin/python

USER tango