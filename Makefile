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
PROJECT = ska-tmc-centralnode-mid
KUBE_APP = ska-tmc-centralnode-mid

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
HELM_CHART=test-parent
UMBRELLA_CHART_PATH ?= charts/$(HELM_CHART)/
K8S_CHARTS ?= ska-tmc-centralnode-mid test-parent## list of charts
K8S_CHART ?= $(HELM_CHART)

CI_PROJECT_DIR ?= .

XAUTHORITY ?= $(HOME)/.Xauthority
THIS_HOST := $(shell ip a 2> /dev/null | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p' | head -n1)
DISPLAY ?= $(THIS_HOST):0
JIVE ?= false# Enable jive
MINIKUBE ?= true ## Minikube or not
TANGO_HOST ?= tango-databaseds:10000## TANGO_HOST connection to the Tango DS

CI_PROJECT_PATH_SLUG ?= ska-tmc-centralnode-mid
CI_ENVIRONMENT_SLUG ?= ska-tmc-centralnode-mid
$(shell echo 'global:\n  annotations:\n    app.gitlab.com/app: $(CI_PROJECT_PATH_SLUG)\n    app.gitlab.com/env: $(CI_ENVIRONMENT_SLUG)' > gilab_values.yaml)

# Test runner - run to completion job in K8s
# name of the pod running the k8s_tests
K8S_TEST_RUNNER = test-runner-$(RELEASE_NAME)

ITANGO_DOCKER_IMAGE = $(CAR_OCI_REGISTRY_HOST)/ska-tango-images-tango-itango:9.3.5

PYTHON_VARS_BEFORE_PYTEST ?= PYTHONPATH=.:src:src/ska_tango_examples \
							 TANGO_HOST=$(TANGO_HOST) \
							 SKUID_URL=ska-ser-skuid-$(HELM_RELEASE)-svc.$(KUBE_NAMESPACE).svc.cluster.local:9870 \

MARK ?= not post_deployment## What -m opt to pass to pytest
# run one test with FILE=acceptance/test_central_node.py::test_check_internal_model_according_to_the_tango_ecosystem_deployed
FILE ?= ## A specific test file to pass to pytest
ADD_ARGS ?= ## Additional args to pass to pytest


CI_REGISTRY ?= gitlab.com
CUSTOM_VALUES = --set central_node.centralnodemid.image.tag=$(VERSION)
K8S_TEST_IMAGE_TO_TEST=$(CAR_OCI_REGISTRY_HOST)/$(PROJECT):$(VERSION)
ifneq ($(CI_JOB_ID),)
CUSTOM_VALUES = --set central_node.centralnodemid.image.image=$(PROJECT) \
	--set central_node.centralnodemid.image.registry=$(CI_REGISTRY)/ska-telescope/$(PROJECT) \
	--set central_node.centralnodemid.image.tag=$(VERSION)-dev.$(CI_COMMIT_SHORT_SHA)
K8S_TEST_IMAGE_TO_TEST=$(CI_REGISTRY)/ska-telescope/$(PROJECT)/$(PROJECT):$(VERSION)-dev.$(CI_COMMIT_SHORT_SHA)
ADD_ARGS=--true-context
MARK=post_deployment
endif

PYTHON_VARS_AFTER_PYTEST ?= -m '$(MARK)' $(ADD_ARGS) $(FILE)


-include .make/k8s.mk
-include .make/python.mk
-include .make/helm.mk
-include .make/oci.mk
-include .make/docs.mk
-include .make/release.mk
-include .make/make.mk
-include .make/help.mk
-include PrivateRules.mak

# flag this up for the oneshot /Dockerfile
OCI_IMAGES=ska-tmc-centralnode-mid

clean:
	@rm -rf .coverage .eggs .pytest_cache build */__pycache__ */*/__pycache__ */*/*/__pycache__ charts/ska-tmc-centralnode-mid/charts \
			charts/build charts/test-parent/charts charts/ska-tmc-centralnode-mid/Chart.lock charts/test-parent/Chart.lock code-coverage

unit-test: python-test

HELM_CHARTS_TO_PUBLISH ?= ska-tmc-central-node

PYTHON_BUILD_TYPE = non_tag_setup

K8S_CHART_PARAMS = --set global.minikube=$(MINIKUBE) \
	--set global.tango_host=$(TANGO_HOST) \
	--set ska-tango-base.display=$(DISPLAY) \
	--set ska-tango-base.xauthority=$(XAUTHORITY) \
	--set ska-tango-base.jive.enabled=$(JIVE) \
	$(CUSTOM_VALUES) \
	--values gilab_values.yaml

requirements: ## Install Dependencies
	python3 -m pip install -r requirements.txt -r requirements-dev.txt

python-pre-test: ## Overriding python.mk
	@mkdir -p build;

# .PHONY is additive
.PHONY: unit-test
