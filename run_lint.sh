#!/bin/bash
set -eo pipefail
#Entering into a bash shell script to run unit-test cases and generating reports
# The installation of lmc base classes is older version hence separately written the installation for linting.
# This will be updated when lmc base class new version is utilised in TMC 
echo "Coding analysis will be performed shortly..."
python3 -m pip install pylint pylint2junit junitparser; \
python3 -m pip install --index-url https://artefact.skao.int/repository/pypi-internal/simple ska-ser-logging==0.4.0 ska-tmc-cdm==6.0.0 ska-tmc-common==0.1.7+d39e6423; \
python3 -m pip install --index-url https://nexus.engageska-portugal.pt/repository/pypi/simple lmcbaseclasses==0.7.2
pwd

python3 -m pip install .;
mkdir -p ./build/reports; \
pylint --rcfile=.pylintrc --output-format=parseable  src/tmc | tee ./build/reports/linting.stdout; \
pylint --rcfile=.pylintrc --output-format=pylint2junit.JunitReporter src/tmc > ./build/reports/linting.xml
