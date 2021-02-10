#
# Project makefile for a ska-tmc-centralnode-mid project. You should normally only need to modify
# DOCKER_REGISTRY_USER and PROJECT below.
#
#
# DOCKER_REGISTRY_HOST, DOCKER_REGISTRY_USER and PROJECT are combined to define
# the Docker tag for this project. The definition below inherits the standard
# value for DOCKER_REGISTRY_HOST (=rnexus.engageska-portugal.pt) and overwrites
# DOCKER_REGISTRY_USER and PROJECT to give a final Docker tag of
# nexus.engageska-portugal.pt/tango-example/dishmaster
#
DOCKER_REGISTRY_USER:=ska-telescope
PROJECT = ska-tmc-centralnode-mid

#
# include makefile to pick up the standard Make targets, e.g., 'make build'
# build, 'make push' docker push procedure, etc. The other Make targets
# ('make interactive', 'make test', etc.) are defined in this file.
#
include .make/Makefile.mk
include .make/docker.mk
include .make/test.mk


.PHONY: all test lint help