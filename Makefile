#
# Project makefile for a ska-tmc-centralnode project. You should normally only need to modify
# PROJECT below.
#
#
# CAR_OCI_REGISTRY_HOST and PROJECT are combined to define
# the Docker tag for this project. The definition below inherits the standard
# value for CAR_OCI_REGISTRY_HOST (=artefact.skao.int) and overwrites
# PROJECT to give a final Docker tag of
# artefact.skao.int/ska-telescope/ska-tmc-centralnode


CAR_OCI_REGISTRY_HOST ?= artefact.skao.int
PROJECT = ska-tmc-centralnode
KUBE_APP = ska-tmc-centralnode
TELESCOPE ?= SKA-mid

# KUBE_NAMESPACE defines the Kubernetes Namespace that will be deployed to
# using Helm.  If this does not already exist it will be created
KUBE_NAMESPACE ?= ska-tmc-centralnode

# HELM_RELEASE is the release that all Kubernetes resources will be labelled
# with
HELM_RELEASE ?= test
HELM_CHARTS_TO_PUBLISH=

# F401 Ignore unused imports because of tagno protected sections
# W503 Ignore operator at beginning of line as conflicts with black
# stretch line length to 180 because of super long parameter assignments
PYTHON_SWITCHES_FOR_FLAKE8=--ignore=W503 --max-line-length=180

# UMBRELLA_CHART_PATH Path of the umbrella chart to work with
HELM_CHART=test-parent
UMBRELLA_CHART_PATH ?= charts/$(HELM_CHART)/
K8S_CHARTS ?= ska-tmc-centralnode test-parent## list of charts
K8S_CHART ?= $(HELM_CHART)

CI_PROJECT_DIR ?= .

XAUTHORITY ?= $(HOME)/.Xauthority
THIS_HOST := $(shell ip a 2> /dev/null | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p' | head -n1)
DISPLAY ?= $(THIS_HOST):0
JIVE ?= false# Enable jive
TARANTA ?= false
MINIKUBE ?= true ## Minikube or not
FAKE_DEVICES ?= true ## Install fake devices or not
TANGO_HOST ?= tango-databaseds:10000## TANGO_HOST connection to the Tango DS
SKUID ?= ska-ser-skuid-$(HELM_RELEASE)-svc.$(KUBE_NAMESPACE).svc.cluster.local:9870
CI_PROJECT_PATH_SLUG ?= ska-tmc-centralnode
CI_ENVIRONMENT_SLUG ?= ska-tmc-centralnode
$(shell echo 'global:\n  annotations:\n    app.gitlab.com/app: $(CI_PROJECT_PATH_SLUG)\n    app.gitlab.com/env: $(CI_ENVIRONMENT_SLUG)' > gilab_values.yaml)

# Test runner - run to completion job in K8s
# name of the pod running the k8s_tests
K8S_TEST_RUNNER = test-runner-$(HELM_RELEASE)

ITANGO_DOCKER_IMAGE = $(CAR_OCI_REGISTRY_HOST)/ska-tango-images-tango-itango:9.3.9

## override so that this picks up setup.cfg from the project root
PYTHON_TEST_FILE ?=

# Set the specific environment variables required for pytest
PYTHON_VARS_BEFORE_PYTEST ?= PYTHONPATH=.:./src \
							 TANGO_HOST=$(TANGO_HOST)

MARK ?= -x## What -m opt to pass to pytest
# run one test with FILE=acceptance/test_central_node.py::test_check_internal_model_according_to_the_tango_ecosystem_deployed
FILE ?= tests## A specific test file to pass to pytest
ADD_ARGS ?= ## Additional args to pass to pytest


CI_REGISTRY ?= gitlab.com
CUSTOM_VALUES = --set central_node.centralnodemid.image.tag=$(VERSION)
K8S_TEST_IMAGE_TO_TEST=$(CAR_OCI_REGISTRY_HOST)/$(PROJECT):$(VERSION)
ifneq ($(CI_JOB_ID),)
CUSTOM_VALUES = --set central_node.centralnodemid.image.image=$(PROJECT) \
	--set central_node.centralnodemid.image.registry=$(CI_REGISTRY)/ska-telescope/ska-tmc/$(PROJECT) \
	--set central_node.centralnodemid.image.tag=$(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA)

K8S_TEST_IMAGE_TO_TEST=$(CI_REGISTRY)/ska-telescope/ska-tmc/$(PROJECT)/$(PROJECT):$(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA)
endif

# override for python-test - must not have the above --true-context
ifeq ($(MAKECMDGOALS),python-test)
ADD_ARGS +=  --forked
MARK = not post_deployment and not acceptance
endif
ifeq ($(MAKECMDGOALS),k8s-test)
ADD_ARGS +=  --true-context
MARK = $(shell echo $(TELESCOPE) | sed s/-/_/) and (post_deployment or acceptance)
endif

PYTHON_VARS_AFTER_PYTEST ?= -m '$(MARK)' $(ADD_ARGS) $(FILE)

K8S_TEST_TEST_COMMAND = $(PYTHON_VARS_BEFORE_PYTEST) $(PYTHON_RUNNER) \
						pytest \
						$(PYTHON_VARS_AFTER_PYTEST) ./tests \
						 | tee pytest.stdout

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
OCI_IMAGES=ska-tmc-centralnode

clean:
	@rm -rf .coverage .eggs .pytest_cache build */__pycache__ */*/__pycache__ */*/*/__pycache__ */*/*/*/__pycache__ charts/ska-tmc-centralnode/charts \
			charts/build charts/test-parent/charts charts/ska-tmc-centralnode/Chart.lock charts/test-parent/Chart.lock code-coverage \
			tests/.pytest_cache

unit-test: python-test

PYTHON_BUILD_TYPE = non_tag_setup

K8S_CHART_PARAMS = --set global.minikube=$(MINIKUBE) \
	--set global.tango_host=$(TANGO_HOST) \
	--set ska-tango-base.display=$(DISPLAY) \
	--set ska-tango-base.xauthority=$(XAUTHORITY) \
	--set ska-tango-base.jive.enabled=$(JIVE) \
	--set central_node.telescope=$(TELESCOPE) \
	--set central_node.deviceServers.mocks.enabled=$(FAKE_DEVICES) \
	--set ska-taranta.enabled=$(TARANTA) \
	--set central_node.deviceServers.centralnode.SkuidService=$(SKUID) \
	$(CUSTOM_VALUES) \
	--values gilab_values.yaml

test-requirements:
	@poetry export --without-hashes --dev --format requirements.txt --output tests/requirements.txt

k8s-pre-test: python-pre-test test-requirements

cred:
	make k8s-namespace
	curl -s https://gitlab.com/ska-telescope/templates-repository/-/raw/master/scripts/namespace_auth.sh | bash -s $(SERVICE_ACCOUNT) $(KUBE_NAMESPACE) || true

requirements: ## Install Dependencies
	poetry install

# .PHONY is additive
.PHONY: unit-test
