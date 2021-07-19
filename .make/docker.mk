#
# IMAGE_TO_TEST defines the tag of the Docker image to test
#
IMAGE_TO_TEST = $(CAR_OCI_REGISTRY_HOST)/$(CAR_OCI_REGISTRY_USER)/$(PROJECT):latest

#
# Never use the network=host mode when running CI jobs, and add extra
# distinguishing identifiers to the network name and container names to
# prevent collisions with jobs from the same project running at the same
# time.
#
ifneq ($(CI_JOB_ID),)
NETWORK_MODE := tangonet-$(CI_JOB_ID)
CONTAINER_NAME_PREFIX := $(PROJECT)-$(CI_JOB_ID)-
else
CONTAINER_NAME_PREFIX := $(PROJECT)-
endif

