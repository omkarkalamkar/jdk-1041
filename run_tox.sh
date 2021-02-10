#!/bin/bash
set -eo pipefail

REPORTS_DIR=./build/reports

# Entering into a bash shell script to run unit-test cases and generating reports
echo "Unit test cases will be executed shortly..."

if [ -d "$REPORTS_DIR" ]; then rm -rf $REPORTS_DIR; fi

mkdir -p $REPORTS_DIR

tox -e py37
