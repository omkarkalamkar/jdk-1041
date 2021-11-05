==================================
Set up your deployment environment
==================================

These instructions will allow you to set up a deployment environment so
that you can run an actual cluster of Tango devices.

These instructions assume a Linux environment; it should be possible to
deploy in other environments.

Machine requirements
--------------------

Memory requirements
^^^^^^^^^^^^^^^^^^^
The ska-tmc-centralnode-mid project uses the SKA `ska-cicd-deploy-minikube` project to
manage cluster deployment. By default, `ska-cicd-deploy-minikube` requests 8Gb of
memory for minikube. This implies that, assuming you want to be able to
do other things with your computer while minikube is running, you will
need upwards of 12Gb of memory.

CPU requirements
^^^^^^^^^^^^^^^^

By default, `ska-cicd-deploy-minikube` tells minikube to use two CPUs. As a rough
rule of thumb: you probably won't see timeouts if minikube can get the
two CPUs that it asks for; but if there is contention for those CPUs,
you may see timeouts.


Overview of setup / teardown
----------------------------
Installation and configuration of the cluster is handled by the SKA
``ska-cicd-deploy-minikube`` project. Thus, this project need only handle the
deployment of centralnode chart to the cluster.

Prerequisites and initial setup
-------------------------------
As with all SKA subsystems, CentralNode uses Helm to deploy Kubernetes
clusters of Docker containers.

#. If you are setting up on a machine that has not already been set up
   with a development environment, then you will need to install Docker,
   install Git, and clone our repo.

#. Install minikube and kubectl.

minikube
^^^^^^^^^^^^^^^^
1. Clone repository deploy-minikube (https://gitlab.com/ska-telescope/sdi/ska-cicd-deploy-minikube)
   and navigate to deploy-minikube directory

   .. code-block:: bash

      me@local:~$ git clone https://gitlab.com/ska-telescope/sdi/deploy-minikube.git
      me@local:~$ cd deploy-minikube

2. Run command `make all`

   .. code-block:: bash

         me@local:~/deploy-minikube make all

3. Once the installation is done, make sure minikube is running using:

   .. code-block:: bash

        me@local:~$ minikube start

kubectl
^^^^^^^^^^^^^^^^

This step is optional as the above `make all` will install `kubectl` for you.  However, if you elect to install `minikube` through a separate process, then the following will be required.

1. Download the latest release with the command:

   .. code-block:: bash

         me@local:~$ curl -LO "https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl"

2. Make the kubectl binary executable.

   .. code-block:: bash

      me@local:~$ chmod +x ./kubectl

3. Move the binary in to your PATH.

   .. code-block:: bash

      me@local:~$ sudo mv ./kubectl /usr/local/bin/kubectl

4. Test to ensure the version you installed is up-to-date:

   .. code-block:: bash

      me@local:~$ kubectl version --client


#. Clone ska-tmc-centralnode-mid repository if not cloned already.

  .. code-block:: bash

         me@local:~$ git clone https://gitlab.com/ska-telescope/ska-tmc-centralnode-mid.git

#. Check for a new version of ``ska-cicd-deploy-minikube``. Development is ongoing in
   the ska-tmc-centralnode-mid folder, and you want to be running the latest version:

   .. code-block:: bash

      me@local:~/ska-tmc-centralnode-mid git submodule update --init --recursive

#. If the CentralNode values.yaml (https://gitlab.com/ska-telescope/ska-tmc-centralnode-mid/-/blob/master/charts/ska-tmc-centralnode-mid/values.yaml)
   is referring to the CentralNode docker image present on CAR Nexuse repository, no need to build
   the image locally. You can directly proceed to install the deployment.

#. If the latest CentralNode image is not published on CAR yet, you first need to build the docker image:

   .. code-block:: bash

       me@local:~/ska-tmc-centralnode-mid make oci-build

#. **IMPORTANT** Because we are using docker as our driver, the
   environment must be set in your terminal. This command must be run in
   each new terminal:

   .. code-block:: bash

       me@local:~/ska-tmc-centralnode-mid eval $(minikube docker-env)

#. Run the deployment using the below command. The TELESCOPE variable is set to SKA-mid
   or SKA-low to run the Mid or Low specific deployment.

   .. code-block:: bash

       me@local:~/ska-tmc-centralnode-mid make k8s-install-chart TELESCOPE=SKA-mid

#. Check the deployment using below command (timeout is optional, but can help with slow image pull issues):

   .. code-block:: bash

          me@local:~/ska-tmc-centralnode-mid make k8s-wait K8S_TIMEOUT=600s

#. Execute the integration test cases from tests/integration folder. Provide the MARK
   to execute Mid or Low specific integration tests:

   .. code-block:: bash

       me@local:~/ska-tmc-centralnode-mid make k8s-test MARK=SKA-mid

#. Once you have finished with the deployment, you can tear it down:

   .. code-block:: bash

       me@local:~/ska-tmc-centralnode-mid make k8s-uninstall-chart
