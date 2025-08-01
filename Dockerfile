<<<<<<< HEAD
ARG BUILD_IMAGE="artefact.skao.int/ska-tango-images-pytango-builder:9.5.0"
ARG BASE_IMAGE="artefact.skao.int/ska-tango-images-pytango-runtime:9.5.0"
FROM $BUILD_IMAGE AS buildenv
FROM $BASE_IMAGE





# Install Poetry
USER root

ENV SETUPTOOLS_USE_DISTUTILS=stdlib
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    poetry config virtualenvs.create false
=======
ARG BUILD_IMAGE=artefact.skao.int/ska-build-python:0.1.1
ARG RUNTIME_IMAGE=artefact.skao.int/ska-tango-images-tango-python:0.1.0

FROM ${BUILD_IMAGE} AS build
>>>>>>> 5f293a5a207ec26cd83e921b3cdee287bd3cf3aa
WORKDIR /app
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH=/app/.venv/bin:$PATH
    
COPY pyproject.toml poetry.lock* ./
RUN poetry install --only main --no-root
COPY src ./src
RUN pip install --no-deps .

<<<<<<< HEAD
COPY --chown=tango:tango . /app
# Install runtime dependencies and the app
RUN poetry install --only main
RUN rm /usr/bin/python && ln -s /usr/bin/python3 /usr/bin/python

=======
FROM ${RUNTIME_IMAGE}
ENV VIRTUAL_ENV=/app/.venv \
    PATH=/app/.venv/bin:$PATH
COPY --from=build ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY --chown=tango:tango src /app/src
WORKDIR /app
>>>>>>> 5f293a5a207ec26cd83e921b3cdee287bd3cf3aa
USER tango
RUN ipython profile create