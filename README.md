# CentralNode

Central Node is a coordinator of the complete M&C system.

# 1 Prerequisites

* Linux/Ubuntu (18.04 LTS)
* Python 3.7
* [python3-pip](https://packages.ubuntu.com/xenial/python3-pip)
* [Tango (9.3.4-rc2)](https://docs.google.com/document/d/1TMp5n380YMvaeqeKZvRHHXa7yVxT8oBn5xsEymyNFC4/edit?usp=sharing)
* [PyTango (9.3.2)](https://docs.google.com/document/d/1DtuIs1PeYGHlDXx8RyOzZyRQ-_Eiup-ncqeDDCtcNxk/edit?usp=sharing)
* skabase (LMC Base classes for SKA): Refer Section 2.1 for installation guide
* [ska-ser-logging](https://gitlab.com/ska-telescope/ska-ser-logging)
* [ska-tmc-cdm](https://gitlab.com/ska-telescope/ska-tmc-cdm)
* [pytest](https://pypi.org/project/pytest/)
* [pytest-cov](https://pypi.org/project/pytest-cov/)
* [pytest-json-report](https://pypi.org/project/pytest-json-report/)
* [pycodestyle](https://pypi.org/project/pycodestyle/)
* [pylint](https://pypi.org/project/pylint/)
* [Docker](https://docs.docker.com/install/linux/docker-ce/ubuntu/) (for running the prototype in a containerised environment)
* [ska-tmc-common] (https://gitlab.com/ska-telescope/ska-tmc-common) : 0.1.2

# 2 Installing, configuring and running the prototype

## 2.1 Install SKA Base classes

Since the Central Node is developed using LMC Base classes, we need to install them prior to running centralnode.
Follow the steps specified at [this link](https://gitlab.com/ska-telescope/lmc-base-classes#installation-steps) to install LMC Base classes.

# 4 Testing

## 4.1 Unit Testing

As depicted above, the higher level of TMC devices are dependent on lower level devices in normal operation.
However for better testability, the unit testing is carried out by mocking the dependent devices.
This enables us to test each of the nodes independently without setting up the entire hierarchy of control nodes.
In order to execute the entire suit of test cases in the repository, a command in makefile is implemented. \
The command to run the unit tests is: `make unit-test` \
In 'make unit-test' job, *tox* based on Python3.7 is used to create testing environment.

# 5 Linting

[Pylint](http://pylint.pycqa.org/en/stable/), code analysis tool used for the linting in the TMC prototype.
 Configuration for linting is provided in *.pylintrc* file. For the code analysis of entire TMC, a command in the
 makefile is implemented.

The command used for linting is: `make lint`

After completion of linting job, *linting.xml* file is generated, which is used in generation of *lint errors*,
*lint failures* and *lint tests* gitlab badges.


# 6 Usage

Now you can start your device server in any
Terminal or console by calling it :

CentralNodeDS instance_name
