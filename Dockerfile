FROM artefact.skao.int/ska-tango-images-pytango-builder:9.3.10 AS buildenv
FROM artefact.skao.int/ska-tango-images-pytango-runtime:9.3.10 AS runtime

# create ipython profile to so that itango doesn't fail if ipython hasn't run yet
RUN ipython profile create

USER root

RUN python3 -m pip install  -r requirements.txt .

# This is a temporary approach to install base classes from Gitlab.
# This will be reverted back in PI 12. 
RUN apt-get -y update && \
    apt-get install -y git && \
    python3 -m pip install -U git+https://gitlab.com/ska-telescope/ska-ser-logging@0.3.0  \
                                git+https://gitlab.com/ska-telescope/ska-tango-base@0.7.2

RUN python3 -m pip install /app

USER tango

CMD ["/usr/local/bin/CentralNodeDS"]
