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

# KUBE_NAMESPACE defines the Kubernetes Namespace that will be deployed to
# using Helm.  If this does not already exist it will be created
KUBE_NAMESPACE ?= ska-tmc-centralnode-mid

# RELEASE_NAME is the release that all Kubernetes resources will be labelled
# with
RELEASE_NAME ?= test
# F401 Ignore unused imports because of tagno protected sections
# W503 Ignore operator at beginning of line as conflicts with black
# stretch line length to 180 because of super long parameter assignments
PYTHON_SWITCHES_FOR_FLAKE8=--ignore=F401,W503 --max-line-length=180

# UMBRELLA_CHART_PATH Path of the umbrella chart to work with
HELM_CHART=test-umbrella
UMBRELLA_CHART_PATH ?= charts/$(HELM_CHART)/
K8S_CHARTS ?= ska-tmc-centralnode-mid test-umbrella## list of charts

CI_PROJECT_DIR ?= .

XAUTHORITY ?= $(HOME)/.Xauthority
THIS_HOST := $(shell ip a 2> /dev/null | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p' | head -n1)
DISPLAY ?= $(THIS_HOST):0
JIVE ?= false# Enable jive

CI_PROJECT_PATH_SLUG ?= ska-tmc-centralnode-mid
CI_ENVIRONMENT_SLUG ?= ska-tmc-centralnode-mid
$(shell echo 'global:\n  annotations:\n    app.gitlab.com/app: $(CI_PROJECT_PATH_SLUG)\n    app.gitlab.com/env: $(CI_ENVIRONMENT_SLUG)' > gilab_values.yaml)

PYTHON_VARS_BEFORE_PYTEST = PYTHONPATH=.:src:src/ska_tango_examples

PYTHON_VARS_AFTER_PYTEST = -m "not post_deployment"

-include .make/make.mk
-include .make/release.mk
-include .make/python.mk
-include .make/oci.mk
-include .make/k8s.mk
-include .make/help.mk
-include PrivateRules.mak

python-do-test:
	@mkdir -p build; \
	$(PYTHON_VARS_BEFORE_PYTEST) pytest $(PYTHON_VARS_AFTER_PYTEST) $(FILE)

# Unit test command
unit-test: python-do-test

HELM_CHARTS_TO_PUBLISH ?= ska-tmc-central-node

PYTHON_BUILD_TYPE = non_tag_setup

K8S_CHART_PARAMS = --set global.minikube=$(MINIKUBE) \
	--set global.tango_host=$(TANGO_HOST) \
	--set ska-tango-base.display=$(DISPLAY) \
	--set ska-tango-base.xauthority=$(XAUTHORITY) \
	--set ska-tango-base.jive.enabled=$(JIVE) \
	--set ska-tmc-centralnode-mid.centralnodemid.image.tag=$(VERSION) \
	--values gilab_values.yaml

requirements: ## Install Dependencies
	python3 -m pip install -r requirements.txt -r requirements-dev.txt

python-pre-lint: requirements## Overriding python.mk 

python-pre-test: requirements## Overriding python.mk 
	@mkdir -p build;

# .PHONY is additive
.PHONY: unit-test
