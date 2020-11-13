=====================================
Example usage scripts for CESAR-P
=====================================

Collection of scripts to use the cesar-p-core library. 
Different usage scenarios are shown here, but it does not include all possibilities.

The project is NOT intended to be directly used to start your project.
Copy and paste the scripts you need to your project and adapt to your needs.

Please feel free to add more examples to this project that might be useful to others.

Project Info
============
- Main contact: Léonie Fierz (leonie.fierz@empa.ch)
- Developers: Léonie Fierz (Urban Energy Systems Lab at Swiss Federal Laboratories for Materials Science and Technology Empa)
- Programming Language and Version: Python 3.8 
- Dependencies (see also requirements.txt)

  - cesar-p-core version 1.3.0
  - geomeppy (for 3D obj generation from idf files)
- Development dependencies:

  - flake8
  - mypy
  - black

- Documentation: all included in this README and in the comments of the different scripts


Project Status
===============
"Released", examples are OK to be used to start your project.
No project version tracking is set up.
There are Tags marking the version compatible with earlier cesar-p-core lib versions in case you need to use an older cesar-p-core version.


Installation & Usage
=====================

It's a showcase project, in order to get it running on your machine do the following:

- Open a shell, e.g. git bash or windows command line. Navigate to the folder where you want to have the examples.
- Clone the project files: git clone https://github.com/hues-platform/cesar-p-usage-examples
- Change to the project directory (cd cesar-p-usage-examples) 
- Download and Install the version matching the project's Python version from https://www.python.org/downloads/.
  - If you already have a Python installation, do not tick 'Add Python X.Y to Path' during installation procedure.
  - Note: using Anaconda is not recommended, but should work
- Create a new Python virtual environment and activate it, e.g.:

    .. code-block::

        python -m venv venv-cesar-p
        venv-cesar-p/Scripts/activate


- Install project dependencies

    .. code-block::

        pip install -r requirements.txt


- For developers - if you want static code checkers: 

    .. code-block::

        pip install flake8, black



Usage
-----


For more information about CESAR-P usage please refer to CESAR-P core project https://github.com/hues-platform/cesar-p-core

For the most simple example, run the simple_example.

You can run with the provided example project files from example_project_files folder or you can 
adapt the simple_example/simple_main_config.yml to point to your project files for site vertices, building information and weather file.

..  code-block::

    cd simple_example
    python simple_run.py


For most of the examples in pre_or_postprocessing_scripts you need to first run a simulation of the simple_example project, see above.
Navigate to pre_or_postprocessing_scripts to run the scripts, as most of them have relative path specifications.

Run CESAR-P with Docker
========================

See Dockerfile and instruction in cesar-p-core repository (https://github.com/hues-platform/cesar-p-core)
