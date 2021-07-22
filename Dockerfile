FROM artefact.skao.int/ska-tango-images-pytango-builder:9.3.10 AS buildenv
FROM artefact.skao.int/ska-tango-images-pytango-runtime:9.3.10 AS runtime

# create ipython profile to so that itango doesn't fail if ipython hasn't run yet
RUN ipython profile create

USER root

RUN python3 -m pip install  -r requirements.txt .

RUN python3 -m pip install /app

USER tango

CMD ["/usr/local/bin/CentralNodeDS"]
