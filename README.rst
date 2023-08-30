=====================================
Example usage scripts for CESAR-P
=====================================

Collection of scripts to use the cesar-p-core library. 
Different usage scenarios are shown here, but it does not include all possibilities.

The project is NOT intended to be directly used to start your project.
Copy and paste the scripts you want to use to your project and adapt to your needs.

Project Info
============
- Main contact: Kristina Orehounig
- Developers: Léonie Fierz (Urban Energy Systems Lab at Swiss Federal Laboratories for Materials Science and Technology Empa)
- Programming Language and Version: Python 3.8 
- Dependencies (see also requirements.txt)

  - cesar-p version 2.4.0
  - geomeppy (for 3D obj generation from idf files, needed for 3dview.py example)

- Documentation: all included in this README and in the comments of the different example scripts

Project Status
===============

There is no versioning for this examples project, but they are ready to be used as a start for your own project based on cesar-p-core.
There are Tags marking the version compatible with earlier cesar-p-core lib versions in case you need to use an older cesar-p-core version.

Installation & Usage
=====================

1. Set up [cesar-p-core library](https://github.com/hues-platform/cesar-p-core) according to the [installation guide](https://cesar-p-core.readthedocs.io/en/latest/readme.html#installation-usage)

2. Activate the virtual environment you installed cesar-p-core libarary, if you followed the installation instrucctions and you are on Windows do:

    .. code-block::

      %USERPROFILE%/venv-cesar-p/Scripts/activate

3. Open a shell and navigate to the folder you want to have the examples in. 

4. Clone this project to your computer: 

  .. code-block::
     
      git clone https://github.com/hues-platform/cesar-p-usage-examples

5. Then to run e.g. the simple example:

  ..  code-block::

      cd simple_example
      python simple_run.py

  You can adapt the simple_example/simple_main_config.yml to point to your project files for site vertices, building information and weather file.

For more options what you can do with the SimulationManager API, e.g. hourly result outputs, check out *advanced_examples/basic_cesar_usage.py*

For more information about CESAR-P usage please refer to CESAR-P core project https://github.com/hues-platform/cesar-p-core

For instructions how to run CESAR-P with Docker: see Dockerfile and instruction in cesar-p-core repository https://github.com/hues-platform/cesar-p-core


Scripts overview
=================

For most of the examples in *pre_or_postprocessing_scripts* you need to first run a simulation of the *simple_example* project, see above.
Navigate to *pre_or_postprocessing_scripts* to run the scripts, as most of them have relative path specifications.

A short overview of the examples included:

=================================================== ========================================= ======================================================================================================
Folder                                              Script                                    Description
=================================================== ========================================= ======================================================================================================
example_project_files                                                                         Project input files (site vertices, BuildingInformation used by many examples)

simple_example                                      simple_run.py                             Running simulations for a site, without operational emissions & costs

advanced_examples/results                                                                     Folder where results are saved to from all advanced examples. Will be created when you run something.

advanced_examples                                   basic_cesar_usage.py                      Running simulations, re-loading existiong projects from disk, hourly output, project ZIP creation
                                                                                              Usable as command line interface, debug a single building.

advanced_examples                                   retrofit_simple_example.py                Running a base-case and retrofit scenario, retrofitting all builings

advanced_examples                                   retrofit_energy_strategy2050_example.py   Running a base-case and retrofit, retrofitting to match energy strategy 2050 path

advanced_examples                                   retrofit_simple_example.py                Running a base-case and retrofit scenario, retrofitting all builings 

advanced_examples                                   simulate_existing_idfs.py                 Use cesar-p to just simulate a bunch of existing IDF files and get the results in cesar-p format.

advanced_examples/custom_constr_archetype_mapping   run_example.py                            Example how to implement an own factory class to assign the construction archetype 
                                                                                              to your buildings, overwriting the default behaviour based on the construction year.
                                                                                              If you just want to use custom archetypes, you could also edit the config of cesarp.graphdb_access and 
                                                                                              assign your archetype URIs for the archetypes to use.
                                                                                              Shows also how you can merge different configuration files.

advanced_examples/operation_params_per_floor        run_example.py                            Assigning different operational parameters per floor. E.g. first floor is SHOP, rest MFH. 
                                                                                              Shows how to create your own factory for the operational parameters. 

advanced_examples/multi_scenario                    multi_scenario.py                         Run different scenarios for the same site. Changing building models or re-creating from scratch, 
                                                                                              depending on the change between the scenarios.

pre_or_postprocessing_scripts                       3dview.py                                 Convert an IDF file to a \*.obj 3D file you can load e.g. in a online 3D viewer

pre_or_postprocessing_scripts                       collect_archetype_infos.py                Query different attributes of the archetypes form the GraphDB, e.g. glazing ratio or infiltration rate

pre_or_postprocessing_scripts                       collect_per_building_infos.py             Load existing building container dumps (must include the BuildingModel) and query building properties

pre_or_postprocessing_scripts                       count_vertices_per_bldg.py                Get the number of footprint vertices per building. Helpful to see whether you have strange geometries.

pre_or_postprocessing_scripts                       postprocess_results.py                    Differetn ways to access and postprocess results after a simulation run finished

development_scripts                                 combine_all_config_files.py               Get one big file with all configuration parameters

development_scripts                                 extend_idd.py                             The default IDD file of E+ is extended to support more building vertices. This scripts helps to  
                                                                                              generates those IDD lines you need to add. Has to be done for each E+ version supported by cesar-p.

development_scripts                                 graphdb_access_test_output.py             Scripts used while developing the cesarp.graphdb_access package
                                                    profiling_graphdb_access.py

development_scripts                                 random_dist_test.py                       Compare one-by-one versus all at onece random number generation       
=================================================== ========================================= ======================================================================================================


Contributing
============

You are welcome to open issues reporting bugs or creating pull requests with bugfixes or new examples!

Before submitting your contribution as a pull request please check code formatting with *flake8* and 
proper type hints with *mppy*.