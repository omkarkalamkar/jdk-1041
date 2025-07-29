ARG BUILD_IMAGE=artefact.skao.int/ska-build-python:0.1.1
ARG RUNTIME_IMAGE=artefact.skao.int/ska-tango-images-tango-python:0.1.0

FROM ${BUILD_IMAGE} AS build
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

FROM ${RUNTIME_IMAGE}
ENV VIRTUAL_ENV=/app/.venv \
    PATH=/app/.venv/bin:$PATH
COPY --from=build ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY --chown=tango:tango src /app/src
WORKDIR /app
USER tango
RUN ipython profile create