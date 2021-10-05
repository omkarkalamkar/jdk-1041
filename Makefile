#
# Project makefile for a ska-tmc-centralnode-mid project. You should normally only need to modify
# PROJECT below.
#
#
# CAR_OCI_REGISTRY_HOST and PROJECT are combined to define
# the Docker tag for this project. The definition below inherits the standard
# value for CAR_OCI_REGISTRY_HOST (=artefact.skao.int) and overwrites
# PROJECT to give a final Docker tag of
# artefact.skao.int/ska-telescope/ska-tmc-centralnode-mid


CAR_OCI_REGISTRY_HOST ?= artefact.skao.int
CAR_OCI_REGISTRY_USER ?= ska-telescope
PROJECT = ska-tmc-centralnode-mid

#KbHrD13unm7H
# include makefile to pick up the standard Make targets, e.g., 'make build'
# build, 'make push' docker push procedure, etc. The other Make targets
# ('make interactive', 'make test', etc.) are defined in this file.
#
#include .make/Makefile.mk
#include .make/docker.mk
#include .make/test.mk

# F401 Ignore unused imports because of tagno protected sections
# W503 Ignore operator at beginning of line as conflicts with black
# stretch line length to 180 because of super long parameter assignments
PYTHON_SWITCHES_FOR_FLAKE8=--ignore=F401,W503 --max-line-length=180

# include makefile targets for make submodule
-include .make/make.mk
# include makefile targets for releases
-include .make/release.mk
# include makefile targets for Python
-include .make/python.mk
# include makefile targets for OCI Images
-include .make/oci.mk
# include makefile targets for Makefile help
-include .make/help.mk
# include your own private variables for custom deployment configuration
-include PrivateRules.mak


# Unit test command
unit-test:
	chmod 755 run_tox.sh; \
	./run_tox.sh;

# Lint command
old-lint:
	chmod 755 run_lint.sh; \
	./run_lint.sh;

# .PHONY is additive
.PHONY: unit-test old-lint
