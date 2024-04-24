===============
Getting started
===============

This page contains instructions for software developers who want to get
started with usage and development of the Central Node.

Background
----------
Detailed information on how the SKA Software development
community works is available at the `SKA software developer portal <https://developer.skao.int/en/latest/>`_.
There you will find guidelines, policies, standards and a range of other
documentation.

Set up your development environment
-----------------------------------
This project is structured to use k8s for development and testing so that the build environment, test environment and test results are all completely reproducible and are independent of host environment. It uses ``make`` to provide a consistent UI (run ``make help`` for targets documentation).

Install minikube
^^^^^^^^^^^^^^^^

You will need to install `minikube` or equivalent k8s installation in order to set up your test environment. You can follow the instruction here  `<https://gitlab.com/ska-telescope/sdi/deploy-minikube/>`_:
::
* git clone git@gitlab.com:ska-telescope/sdi/deploy-minikube.git
* cd deploy-minikube
* make all
* eval $(minikube docker-env)

* Please note that the command `eval $(minikube docker-env)` will point your local docker client at the docker-in-docker for minikube. Use this only for building the docker image and another shell for other work.*

How to Use
^^^^^^^^^^

Clone this repo:
::
* git clone https://gitlab.com/ska-telescope/ska-tmc/ska-tmc-centralnode.git
* cd ska-tmc-centralnode

Install dependencies
::
* apt update
* apt install -y curl git build-essential libboost-python-dev libtango-dev 
* curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python3 -
* source $HOME/.poetry/env

Please note that:
 * the `libtango-dev` will install an old version of the TANGO-controls framework (9.2.5);
 * the best way to get the framework is compiling it (instructions can be found `here <https://gitlab.com/tango-controls/cppTango/-/blob/main/INSTALL.md>`_);
 * the above script has been tested with Ubuntu 20.04.

*During this step, `libtango-dev` installation can ask for the Tango Server IP:PORT. Just accept the default proposed value.*

Install python requirements for linting and unit testing:
::
$ poetry install

Activate the poetry environment:
::
$ source $(poetry env info --path)/bin/activate

Alternate way to install and activate poetry:
::
* Follow the steps till installation of dependencies. then, 

    $ virtualenv cn_venv
    $ source cn_venv/bin/activate
    $ make requirements

Run python-test:
::
$ make python-test
$ PyTango 9.4.2 
$ Python : 3.10 or above
$ Numpy  : 1.23.0 or above
$ Tango  : 9.4.2
$ Boost  : 1.71.0


    PyTango running on:
    uname_result(system='Linux', node='LAPTOP-5LBGJH83', release='4.19.128-microsoft-standard', version='#1 SMP Tue Jun 23 12:58:10 UTC 2020', machine='x86_64', processor='x86_64')

    ============================= test session starts ==============================
    platform linux -- Python 3.8.5, pytest-5.4.3, py-1.10.0, pluggy-0.13.1 -- /home/
    [....]

    --------------------------------- JSON report ----------------------------------
    JSON report written to: build/reports/report.json (165946 bytes)

    ----------- coverage: platform linux, python 3.8.5-final-0 -----------
    Coverage HTML written to dir build/htmlcov
    Coverage XML written to file build/reports/code-coverage.xml

    ======================== 48 passed, 5 deselected in 42.42s ========================

    Formatting the code:
    ::
    $ make python-format
    [...]
    --------------------------------------------------------------------
    Your code has been rated at 10.00/10 (previous run: 10.00/10, +0.00)


    Python linting:
    ::
    $ make python-lint
    [...]
    --------------------------------------------------------------------
    Your code has been rated at 10.00/10 (previous run: 10.00/10, +0.00)


Helm Charts linting:
::
$ make helm-lint
[...]
10 chart(s) linted, 0 chart(s) failed


Build the container image for the project:
::
$ make oci-image-build
[...]
[+] Building 111.7s (14/14) FINISHED 
[...]


Install the umbrella chart:
::
$ make k8s-install-chart
[...]
NAME: test
LAST DEPLOYED: Fri Nov  5 10:35:18 2021
NAMESPACE: ska-tmc-centralnode
STATUS: deployed
REVISION: 1
TEST SUITE: None

Test the deployment with (the result of the tests are stored into the folder ``charts/build``):
::
make k8s-wait && make k8s-test 
k8s-test: start test runner: test-runner-test -n ska-tmc-centralnode
k8s-test: sending test folder: tar -cz src/ tests/
( cd /home/ubuntu/ska-tmc-centralnode; tar -cz src/ tests/ \
| kubectl run test-runner-test -n ska-tmc-centralnode --restart=Never --pod-running-timeout=360s  --image-pull-policy=IfNotPresent --image=artefact.skao.int/ska-tmc-centralnode:0.3.4-dirty --env=INGRESS_HOST=  -iq -- /bin/bash -o pipefail -c " mkfifo results-pipe && tar zx --warning=all && cd tests && ( if [[ -f requirements.txt ]]; then echo 'k8s-test: installing requirements.txt'; pip install -qUr requirements.txt; fi ) && export PYTHONPATH=:/app/src:/app/ska_tmc_centralnode/ && mkdir -p build && ( cd .. && PYTHONPATH=.:./src TANGO_HOST=tango-databaseds:10000  pytest -m 'SKA_mid and (post_deployment or acceptance)'  --true-context tests ./tests | tee pytest.stdout;  ); echo \$? > build/status; pip list > build/pip_list.txt; echo \"k8s_test_command: test command exit is: \$(cat build/status)\"; tar zcf ../results-pipe build;" 2>&1 \
| grep -vE "^(1\||-+ live log)" --line-buffered &); \
sleep 1; \
echo "k8s-test: waiting for test runner to boot up: test-runner-test -n ska-tmc-centralnode"; \
( \
kubectl wait pod test-runner-test -n ska-tmc-centralnode --for=condition=ready --timeout=360s ; \
wait_status=$?; \
if ! [[ $wait_status -eq 0 ]]; then echo "Wait for Pod test-runner-test -n ska-tmc-centralnode failed - aborting"; exit 1; fi; \
) && \
echo "k8s-test: test-runner-test -n ska-tmc-centralnode is up, now waiting for tests to complete" && \
(kubectl exec test-runner-test -n ska-tmc-centralnode -- cat results-pipe | tar --directory=/home/ubuntu/ska-tmc-centralnode -xz); \
cd /home/ubuntu/ska-tmc-centralnode/; \
(kubectl get all,job,pv,pvc,ingress,cm -n ska-tmc-centralnode -o yaml > build/k8s_manifest.txt); \
echo "k8s-test: test run complete, processing files"; \
kubectl --namespace ska-tmc-centralnode delete --ignore-not-found pod test-runner-test --wait=false
k8s-test: waiting for test runner to boot up: test-runner-test -n ska-tmc-centralnode
pod/test-runner-test condition met
k8s-test: test-runner-test -n ska-tmc-centralnode is up, now waiting for tests to complete
k8s-test: installing requirements.txt
[...]
===================== 19 passed, 178 deselected in 18.38s ======================


It is possible to install and test the centralnode both in Mid and Low by passing the variable TELESCOPE (``SKA-mid`` or ``SKA-low``):
::
$ make k8s-install-chart TELESCOPE=SKA-low
$ make k8s-wait TELESCOPE=SKA-low
$ make k8s-test TELESCOPE=SKA-low


Uninstall the chart: 
::
$ make k8s-uninstall-chart 
release "test" uninstalled


Makefile targets
^^^^^^^^^^^^^^^^

This project contains a Makefile which acts as a UI for building container images, testing images, and for launching interactive developer environments.
For the documentation of the Makefile run ``make help``.
