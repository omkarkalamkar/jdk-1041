FROM nexus.engageska-portugal.pt/ska-docker/ska-python-buildenv:9.3.2 AS buildenv
FROM nexus.engageska-portugal.pt/ska-docker/ska-python-runtime:9.3.2 AS runtime

# create ipython profile to so that itango doesn't fail if ipython hasn't run yet
RUN ipython profile create

#install lmc-base-classes
USER root

RUN python3 -m pip install ska-logging==0.3.0 \
                           lmcbaseclasses==0.7.2 \
                           ska-log-transactions \
                           skatmccommon==0.1.6+3aaa7bbe 

# As the CDM shared library is moved to Artifacts repository, hence need to download from that path
FROM artefact.skao.int/ska-tango-images-pytango-builder:9.3.10 
FROM artefact.skao.int/ska-tango-images-pytango-runtime:9.3.10 

RUN python3 -m pip install ska-tmc-cdm==6.0.0

USER tango

CMD ["/usr/local/bin/CentralNodeDS"]
