FROM nexus.engageska-portugal.pt/ska-docker/ska-python-buildenv:9.3.2 AS buildenv
FROM nexus.engageska-portugal.pt/ska-docker/ska-python-runtime:9.3.2 AS runtime

# create ipython profile to so that itango doesn't fail if ipython hasn't run yet
RUN ipython profile create

#install lmc-base-classes
USER root
RUN python3 -m pip install ska-logging==0.3.0 \
                           lmcbaseclasses==0.7.2 \
                           cdm-shared-library==2.0.0 \
                           ska-log-transactions \
                           skatmccommon==0.1.6+3aaa7bbe \
                            .

USER tango

CMD ["/usr/local/bin/CentralNodeDS"]
