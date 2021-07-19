# FROM nexus.engageska-portugal.pt/ska-docker/ska-python-buildenv:9.3.2 AS buildenv
# FROM nexus.engageska-portugal.pt/ska-docker/ska-python-runtime:9.3.2 AS runtime

FROM artefact.skao.int/ska-tango-images-pytango-builder:9.3.10
FROM artefact.skao.int/ska-tango-images-pytango-runtime:9.3.10
# create ipython profile to so that itango doesn't fail if ipython hasn't run yet
RUN ipython profile create

USER root

#install lmc-base-classes from EngageSka Nexus repository. 
# Once TMC code is upgraded to work with new lmc base classes, install from Central Artifacts Repository as below
# Also, once all the old artefacts are moved from EngageSKA repo to CAR, change the implementation as below
# RUN python3 -m pip install lmcbaseclasses==0.7.2 


#install other packages from Central Artifacts Repository (Nexus) repository
RUN python3 -m pip install ska-ser-logging==0.4.0 \
                           ska-tmc-cdm==6.0.0 \
                           ska-ser-log-transactions \
                           ska-tmc-common==0.1.7+d39e6423 \
                           ska-tango-base==0.11.3

USER tango

CMD ["/usr/local/bin/CentralNodeDS"]
