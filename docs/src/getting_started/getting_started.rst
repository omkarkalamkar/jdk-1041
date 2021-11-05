===============
Getting started
===============

This page contains instructions for software developers who want to get
started with usage and development of the CentralNode.

Background
----------
Detailed information on how the SKA Software development
community works is available at the `SKA software developer portal`_.
There you will find guidelines, policies, standards and a range of other
documentation.

Set up your development environment
-----------------------------------
This project is structured to use k8s for development and testing so that the build environment, test environment and test results are all completely reproducible and are independent of host environment. It uses ``make`` to provide a consistent UI (run ``make help`` for targets documentation).

Install minikube
^^^^^^^^^^^^^^^^

You will need to install `minikube` or equivalent k8s installation in order to set up your test environment. You can follow the instruction at [here](https://gitlab.com/ska-telescope/sdi/deploy-minikube/):
::
    git clone git@gitlab.com:ska-telescope/sdi/deploy-minikube.git
    cd deploy-minikube
    make all
    eval $(minikube docker-env)

*Please note that the command `eval $(minikube docker-env)` will point your local docker client at the docker-in-docker for minikube. Use this only for building the docker image and another shell for other work.*

How to Use
^^^^^^^^^^

Clone this repo:
::
    git clone https://gitlab.com/ska-telescope/ska-tmc-centralnode-mid.git
    cd ska-tmc-centralnode-mid


Create a virtualenv:
::
    virtualenv venv
    source venv/bin/activate

Build a new Docker image for the project:
::
    $ make oci-build
    [...]
    [+] Building 111.7s (14/14) FINISHED 
    [...]


Install python requirements for linting and unit testing:
::
    $ make requirements
    poetry install

Run python-test:
::
    $ make python-test
    PyTango 9.3.3 (9, 3, 3)
    PyTango compiled with:
        Python : 3.8.5
        Numpy  : 0.0.0 ## output generated from a WSL windows machine
        Tango  : 9.2.5
        Boost  : 1.71.0

    PyTango runtime is:
        Python : 3.8.5
        Numpy  : None
        Tango  : 9.2.5

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


Install the umbrella chart:
::
    $ make k8s-install-chart
    [...]
    NAME: test
    LAST DEPLOYED: Fri Nov  5 10:35:18 2021
    NAMESPACE: ska-tmc-centralnode-mid
    STATUS: deployed
    REVISION: 1
    TEST SUITE: None

Test the deployment with (the result of the tests are stored into the folder ``charts/build``):
::
    $ make k8s-wait && make k8s-test 
    k8s-test: start test runner: test-runner-test -n ska-tmc-centralnode-mid
    k8s-test: sending test folder: tar -cz src/ tests/
    ( cd /home/ubuntu/ska-tmc-centralnode-mid; tar -cz src/ tests/ \
    | kubectl run test-runner-test -n ska-tmc-centralnode-mid --restart=Never --pod-running-timeout=360s  --image-pull-policy=IfNotPresent --image=artefact.skao.int/ska-tmc-centralnode-mid:0.3.2-dirty --env=INGRESS_HOST=  -iq -- /bin/bash -o pipefail -c " mkfifo results-pipe && tar zx --warning=all && cd tests && ( if [[ -f requirements.txt ]]; then echo 'k8s-test: installing requirements.txt'; pip install -qUr requirements.txt; fi ) && export PYTHONPATH=:/app/src:/app/ska_tmc_centralnode_mid/ && mkdir -p build && ( cd .. && PYTHONPATH=.:./src TANGO_HOST=tango-databaseds:10000  pytest -m 'SKA_mid and (post_deployment or acceptance)'  --true-context tests ./tests | tee pytest.stdout;  ); echo \$? > build/status; pip list > build/pip_list.txt; echo \"k8s_test_command: test command exit is: \$(cat build/status)\"; tar zcf ../results-pipe build;" 2>&1 \
    | grep -vE "^(1\||-+ live log)" --line-buffered &); \
    sleep 1; \
    echo "k8s-test: waiting for test runner to boot up: test-runner-test -n ska-tmc-centralnode-mid"; \
    ( \
    kubectl wait pod test-runner-test -n ska-tmc-centralnode-mid --for=condition=ready --timeout=360s ; \
    wait_status=$?; \
    if ! [[ $wait_status -eq 0 ]]; then echo "Wait for Pod test-runner-test -n ska-tmc-centralnode-mid failed - aborting"; exit 1; fi; \
    ) && \
            echo "k8s-test: test-runner-test -n ska-tmc-centralnode-mid is up, now waiting for tests to complete" && \
            (kubectl exec test-runner-test -n ska-tmc-centralnode-mid -- cat results-pipe | tar --directory=/home/ubuntu/ska-tmc-centralnode-mid -xz); \
    \
    cd /home/ubuntu/ska-tmc-centralnode-mid/; \
    (kubectl get all,job,pv,pvc,ingress,cm -n ska-tmc-centralnode-mid -o yaml > build/k8s_manifest.txt); \
    echo "k8s-test: test run complete, processing files"; \
    kubectl --namespace ska-tmc-centralnode-mid delete --ignore-not-found pod test-runner-test --wait=false
    k8s-test: waiting for test runner to boot up: test-runner-test -n ska-tmc-centralnode-mid
    pod/test-runner-test condition met
    k8s-test: test-runner-test -n ska-tmc-centralnode-mid is up, now waiting for tests to complete
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
