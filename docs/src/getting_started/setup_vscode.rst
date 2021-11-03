Set up Visual Studio Code
=========================
This page describes how to set up Visual Studio Code (vscode) for remote
container development in a SKA Software docker container.

Background
----------
The ska-tmc-centralnode-mid repository is set up
for remote container development in Visual Studio Code ("vscode"), and
it is recommended that you use vscode to develop.


Instructions
------------
The following instructions simply integrate our remote container
development workflow into the vscode IDE, so that, for example, the
vscode IDE terminal runs inside a Docker container.

1. Install vscode on your local machine.

2. Clone ska-tmc-centralnode-mid repository if not cloned already.

  .. code-block:: bash

    me@local:~$ git clone https://gitlab.com/ska-telescope/ska-tmc-centralnode-mid.git

3. Start vscode. Choose "Open folder..." and select the ska-tmc-centralnode-mid
   repository folder. You should see the contents of the repository open
   into your sidebar. Set the interpreter to Python3.7 in vscode.

3. Check for a new version of ``ska-cicd-deploy-minikube``. Development is ongoing in 
the ska-tmc-centralnode-mid folder, and you want to be running the latest version:

  .. code-block:: bash

    me@local:~/ska-tmc-centralnode-mid git submodule update --init --recursive 

4. Click on the "Extensions" sidebar icon. Search for and install "Remote-Containers".

5. Once the extension is installed, you should see a pop-up box telling
   you that it has detected a ``.devcontainers`` folder, and asking if
   you want to reload the repository in a remote container. Choose yes.
   You'll see a pop-up message that it is "Starting with Dev Container".

   * If you left it too long and the ".devcontainer detected" pop-up
     disappeared, then press <Ctrl-Shift-P> . It opens a Command
     Bar from which any VScode command can be searched for and run. Type
     "Remote" and you will find an option along the lines of "Open folder 
     in container". Select the ska-tmc-centralnode-mid folder.

   * The first time you do this, it may take a very long time, because
     the Docker image has to be downloaded. Once downloaded, the image
     will be cached, so it will be much faster in future.
     
   * If you click on the "Starting with Dev Container" message box, it
     will show you a terminal where things are happening.

6. Visual Studio Code is now running inside your container. Open a bash
   terminal in vscode (look for the + button amongst the terminal
   options). The bash prompt will be something like

  .. code-block:: shell-session

    tango@41561d39198a:/workspaces/ska-tmc-centralnode-mid$

   indicating that you are user "tango" in a docker container named
   "41561d39198a" (your container name will differ).

6. Run the unit tests:

  .. code-block:: shell-session

    tango@41561d39198a:/workspaces/ska-tmc-centralnode-mid$ make python-test
    python-pre-test: running with: PYTHONPATH=.:src:src/ska_tmc_centralnode_mid:tests TANGO_HOST=tango-databaseds:10000  pytest -m 'not post_deployment and not acceptance'  --forked   --cov=src --cov-report=term-missing --cov-report xml:build/reports/code-coverage.xml --junitxml=build/reports/unit-tests.xml 
    pytest --version -c /dev/null
    pytest 6.2.5
    PyTango 9.3.3 (9, 3, 3)
    PyTango compiled with:
        Python : 3.7.3
        Numpy  : 1.19.2
        Tango  : 9.3.4
        Boost  : 1.67.0

    PyTango runtime is:
        Python : 3.7.3
        Numpy  : 1.17.2
        Tango  : 9.3.4

    PyTango running on:
    uname_result(system='Linux', node='41561d39198a', release='5.4.0-89-generic', version='#100~18.04.1-Ubuntu SMP Wed Sep 29 10:59:42 UTC 2021', machine='x86_64', processor='')

    ====================================================== test session starts =======================================================
    platform linux -- Python 3.7.3, pytest-6.2.5, py-1.10.0, pluggy-1.0.0 -- /usr/bin/python3
    cachedir: .pytest_cache
    metadata: {'Python': '3.7.3', 'Platform': 'Linux-5.4.0-89-generic-x86_64-with-debian-10.10', 'Packages': {'pytest': '6.2.5', 'py': '1.10.0', 'pluggy': '1.0.0'}, 'Plugins': {'repeat': '0.9.1', 'bdd': '3.4.0', 'xdist': '2.4.0', 'timeout': '2.0.1', 'forked': '1.3.0', 'cov': '2.12.1', 'pycodestyle': '2.2.0', 'json-report': '1.4.1', 'pylint': '0.18.0', 'mock': '3.6.1', 'metadata': '1.11.0', 'pydocstyle': '2.2.0'}}
    rootdir: /workspaces/ska-tmc-centralnode-mid, configfile: setup.cfg, testpaths: tests
    plugins: repeat-0.9.1, bdd-3.4.0, xdist-2.4.0, timeout-2.0.1, forked-1.3.0, cov-2.12.1, pycodestyle-2.2.0, json-report-1.4.1, pylint-0.18.0, mock-3.6.1, metadata-1.11.0, pydocstyle-2.2.0
    collecting ... 
    ------------------------------------------------------ live log collection -------------------------------------------------------
    DEBUG    parse:parse.py:837 format 'a CentralNode device called <central_node_name>' -> 'a CentralNode device called <central_node_name>'
    DEBUG    parse:parse.py:837 format 'I call the command <command_name>' -> 'I call the command <command_name>'
    DEBUG    parse:parse.py:837 format 'the command is queued and executed in less than {seconds} ss' -> 'the command is queued and executed in less than (?P<seconds>.+?) ss'
    collected 197 items / 37 deselected / 160 selected                                                                               

    tests/unit/commands/low/test_assign_resources_command.py::test_telescope_low_assign_resources_command 
    --------------------------------------------------------- live log setup ---------------------------------------------------------
    INFO     root:conftest.py:42 true context: False
    DEBUG    tango:server.py:1347 server loop started
    PASSED               [  0%]
    tests/unit/commands/low/test_assign_resources_command.py::test_telescope_low_assign_resources_command_fail_subarray 
    --------------------------------------------------------- live log setup ---------------------------------------------------------
    INFO     root:conftest.py:42 true context: False
    DEBUG    tango:server.py:1347 server loop started
    PASSED [  1%]
    tests/unit/commands/low/test_assign_resources_command.py::test_telescope_low_assign_resources_command_missing_subarray_beam_ids_key 
    --------------------------------------------------------- live log setup ---------------------------------------------------------
    INFO     root:conftest.py:42 true context: False
    DEBUG    tango:server.py:1347 server loop started
    PASSED [  1%]
    
    .... [tests running]

    tests/unit/mid/test_tmc_state_on.py::test_tmc_state_on_only_events 
--------------------------------------------------------- live log setup ---------------------------------------------------------
INFO     root:conftest.py:42 true context: False
DEBUG    tango:server.py:1347 server loop started
PASSED                                                  [100%]

---------------------- generated xml file: /workspaces/ska-tmc-centralnode-mid/build/reports/unit-tests.xml ----------------------
---------------------------------------------------------- JSON report -----------------------------------------------------------
report saved to: build/reports/report.json

Coverage HTML written to dir build/reports/htmlcov
Coverage XML written to file build/reports/code-coverage.xml

========================================= 160 passed, 37 deselected in 349.89s (0:05:49) =========================================

   The unit tests from tests/unit folder are executed because they are being run inside the Docker container,
   which contains all the dependencies.

7. Before pushing the chnages on the remote repository you need to run below command to fix formatting and
  linting errors and warnings.

  .. code-block:: shell-session

    tango@41561d39198a:/workspaces/ska-tmc-centralnode-mid$ make python-format && make python-lint
    isort --profile black -w 79  src/ tests/  
    black --line-length 79  src/ tests/  
    All done! ✨ 🍰 ✨
    100 files left unchanged.
    isort --check-only --profile black -w 79  src/ tests/  
    black --check --line-length 79  src/ tests/  
    All done! ✨ 🍰 ✨
    100 files would be left unchanged.
    flake8 --show-source --statistics --ignore=W503 --max-line-length=180 src/ tests/  
    pylint --output-format=parseable  src/ tests/   | tee build/code_analysis.stdout


    Report
    ======
    3244 statements analysed.

    Statistics by type
    ------------------

    +---------+-------+-----------+-----------+------------+---------+
    |type     |number |old number |difference |%documented |%badname |
    +=========+=======+===========+===========+============+=========+
    |module   |43     |43         |=          |NC          |NC       |
    +---------+-------+-----------+-----------+------------+---------+
    |class    |59     |59         |=          |NC          |NC       |
    +---------+-------+-----------+-----------+------------+---------+
    |method   |0      |0          |=          |0           |0        |
    +---------+-------+-----------+-----------+------------+---------+
    |function |0      |0          |=          |0           |0        |
    +---------+-------+-----------+-----------+------------+---------+

    [running lint]

    --------------------------------------------------------------------
    Your code has been rated at 10.00/10 (previous run: 10.00/10, +0.00)

    pylint --output-format=pylint_junit.JUnitReporter  src/ tests/   > build/reports/linting-python.xml
    tango@41561d39198a:/workspaces/ska-tmc-centralnode-mid$ 

