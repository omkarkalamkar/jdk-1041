Set up your development environment
===================================
This page is part of the :doc:`getting_started` documentation for the
CentralNode. The basic setup described here will allow you to edit code and
documentation locally. For the testing and linitng you need to follow furtehr steps
described in subsequent sections.

The basic steps are

1. Install Docker;

2. Install and setup Git, and clone the ska-tmc-centralnode-mid repository.

3. Install make.

Details on these steps are provided below.

Docker
^^^^^^

Ubuntu-specific instructions
````````````````````````````
It is assumed that the Ubuntu is 18.04 LTE, but may be relevant to
other versions / Linux variants. The detailed instructions are present at the official
docker website https://docs.docker.com/engine/install/ubuntu/.

1. Install Docker using the repository

  Set up the repository
  ````````````````````````````

  .. code-block:: shell-session

    me@local:~$ sudo apt-get update
    me@local:~$ sudo apt-get install \
      ca-certificates \
      curl \
      gnupg \
      lsb-release
    me@local:~$ curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    me@local:~$ echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    .. code-block:: shell-session

      me@local:~$ sudo apt-get update
      me@local:~$ sudo apt-get install docker-ce docker-ce-cli containerd.io

2. Test your install:

   .. code-block:: shell-session

     me@local:~$ sudo docker run hello-world
     Unable to find image 'hello-world:latest' locally
     latest: Pulling from library/hello-world
     0e03bdcc26d7: Pull complete 
     Digest: sha256:6a65f928fb91fcfbc963f7aa6d57c8eeb426ad9a20c7ee045538ef34847f44f1
     Status: Downloaded newer image for hello-world:latest

     Hello from Docker!
     This message shows that your installation appears to be working correctly.
     ...

3. At this point you can only run this command as sudo, because you are
   not a member of the docker group. Follow below steps to run doker command
   without sudo.

  Create the Docker group
  `````````````````````````````
   .. code-block:: shell-session

     me@local:~$ sudo groupadd docker

  Add your user to the docker group
  `````````````````````````````
   .. code-block:: shell-session

     me@local:~$ sudo usermod -aG docker $USER

  On Linux, you can run the following command to activate the changes to groups:
  `````````````````````````````
   .. code-block:: shell-session

     me@local:~$ newgrp docker 

4. Log out and log back in. Then verify that you can run docker without
   sudo:

   .. code-block:: shell-session

     me@local:~$ docker run hello-world

Great! You are ready to run a SKA Docker container.

Git
^^^
1. Install git. This should be simple on any operating system.

2. Set up git:

   .. code-block:: shell-session

     me@local:~$ git config --global user.name "Your Name"
     me@local:~$ git config --global user.email "youremail@domain.com"

3. Follow the instructions at the SKA `Working
   with Git`_ page.

4. Clone ska-tmc-centralnode-mid repository

  .. code-block:: bash

    git clone https://gitlab.com/ska-telescope/ska-tmc-centralnode-mid.git

Make
^^^^
Linux instructions
``````````````````
On Linux, you can install Make via your package management system. For
example, on Ubuntu:

.. code-block:: shell-session

  me@local:~$ sudo apt install build-essential

will install a number of tools common to building tool-chains, including
Make.

Execute Unit test cases and linting
^^^^^^^^^^^^^^^^^^^^^^^
You now have a basic development setup. Following page provides instructions for 
setting up Visual Studio code with 
remote container and run the unit test cases and linting:

* :doc:`setup_vscode`

Execute Integration test cases
^^^^^^^^^^^^^^^^^^^^^^^
Follow the instructions in below page to deploy CentralNode device and the other 
TMC devices (SubarrayNode and Leaf Nodes) simulated. And then run the integration test cases.

* :doc:`setup_deployment_environment`