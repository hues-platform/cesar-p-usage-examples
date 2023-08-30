# -*- coding: utf-8 -*-
#
# Copyright (c) 2021, Empa, Leonie Fierz
#
# This file is part of CESAR-P - Combined Energy Simulation And Retrofit written in Python
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Contact: https://www.empa.ch/web/s313
#

"""
This example script has quite a lot of bits and pieces.
I do not really advice to re use the script as it is in your project. Better use the script from simple_example as a starting point 
and extend with the functionality shown here as you need.

There are kind of two interfaces included in this script. 

1. you can run it from the command line, passing the project arguments, so you do not need to adapt the script for each simulation run with different input files
   to get more details run on the console: *python basic_cesar_usage.py help*
2. adapt the pathes in   __main__ part to your needs and run then the script

The project configuration is normally stored in a YAML file. But you can also pass a dictionary as configuration. If doing so, please make sure you have the correct
hierarchy levels in your dict according to the YAML configuration file structure. Your configuration must at least contain the pointers to the site vertices, the 
and the different entries for per-building info and weather file.

Working with Jupyter Notebook might be tricky, as we use multiprocessing in the SimulationManager class and multiprocessing does not like 
scripts without that __name__ == "__main__" guard because the parent python script is re-executed in each worker process and everything without beeing
protected by that guard will be re-executed (so it will recursively create processes which is not good at all)
"""

import os
from enum import Enum
import shutil
from pathlib import Path
from typing import Union, List, Dict, Any, Optional
import sys
import logging
import logging.config

# UNCOMMENT THIS IF CESAR-P IMPORT DOES NOT WORK when you have a checkout of python source - you will have to adapt the path to the src folder of cesar-p clone
# cesar_package_path = os.path.abspath(os.path.dirname(__file__) / Path("../../"))
# print("adding cesar src to python search path: ", cesar_package_path)
# sys.path.append(cesar_package_path)

from cesarp.manager.SimulationManager import SimulationManager
import cesarp.common
from cesarp.eplus_adapter.eplus_eso_results_handling import RES_KEY_DHW_DEMAND, RES_KEY_HEATING_DEMAND
from cesarp.eplus_adapter.idf_strings import ResultsFrequency
from cesarp.manager.debug_methods import run_single_bldg


def __abs_path(path: Union[str, Path]):
    """
    helper function
    python evaluates any relative pathes relative to the location of script, module, class it is used in,
    thus, always convert relative pathes after passing them to the main script

    :param path: relative path to conevert (if it is already absolute path you pass it should be left unchanged)
    :type path: Union[str, Path]
    :return: absolute path
    :rtype: str
    """
    return cesarp.common.config_loader.abs_path(path, os.path.abspath(__file__))


def run_sim_site(base_output_folder: Union[str, Path], main_config_path: Union[str, Path, Dict[str, Any]], fids: List[int] = None, delete_old_logs: bool = True):
    """
    Normal simulation run.
    Create a ZIP including all ressources used and results.
    Get hourly results.

    :param base_output_folder: full path to folder where to store results
    :type base_output_folder: Union[str, Path]
    :param main_config_path: project specifig config, you can either pass the full file path to the config YML file or a dictionary with configuration entries
    :type main_config_path: Union[str, Path, Dict[str, Any]]
    :param fids: list of fids from your site to simulate, if None all buildings are used, defaults to None
    :type fids: List[int], optional
    :param delete_old_logs: if True, old worker log files are deleted (*-cesarp-logs folders)
    :type delete_old_logs: bool
    """
    base_output_folder = __abs_path(base_output_folder)
    assert not os.path.exists(base_output_folder), f"output folder {base_output_folder} already exists - please specify a non-existing folder for cesar-p outputs."
    sim_manager = SimulationManager(
        base_output_folder, main_config_path, cesarp.common.init_unit_registry(), fids_to_use=fids, load_from_disk=False, delete_old_logs=delete_old_logs
    )

    sim_manager.run_all_steps()
    zip_path = sim_manager.save_to_zip(main_script_path=__file__, save_folder_path=os.path.dirname(__file__), include_idfs=False, include_eplus_output=False, include_src_pck=True)
    print(f"Project has been saved to {zip_path}, including all input files so it can be transfered to another computer.")

    # if you need different result parameters, you have to make sure that energy plus reports them. Do so by using the configuration parameters from eplus_adapter package, namely
    # "OUTPUR_METER" and "OUTPUT_VARS", see cesarp.eplus_adapter.default_config.yml. You can overwrite those parameters in your project config, in this example that would be main_config.yml.
    # Also make sure that the reporting frequency in the configuration and in the collect_custom_results() call match.
    result_series_frame = sim_manager.collect_custom_results(result_keys=[RES_KEY_HEATING_DEMAND, RES_KEY_DHW_DEMAND], results_frequency=ResultsFrequency.HOURLY)
    # you can postprocess the results as you like, e.g. save to a file
    result_series_frame.to_csv(__abs_path(base_output_folder) / Path("hourly_results.csv"))

    if sim_manager.failed_fids:
        logging.warning(f"Something went wrong for following FID's {sim_manager.failed_fids}")


def load_from_disk(base_output_folder: Union[str, Path], main_config_path: Union[str, Path, Dict[str, Any]]) -> None:
    """
    Load existing project.
    If simulation results are available in the building containers the summary result file is re-created.
    But you could also re-load a project for which the simulation are not yet run to run them.

    :param base_output_folder: project folder, expecting the output structure according to cesar-p defaults or according to the configuration passed
    :type base_output_folder: Union[str, Path]
    :param main_config_path: project config used, especially if you parameters overwritten for output folders and names it is important to pass it when re-loading.
                             you can either pass the full file path to the config YML file or a dictionary with configuration entries
    :type main_config_path: Union[str, Path, Dict[str, Any]]
    """
    base_output_folder = __abs_path(base_output_folder)
    assert os.path.exists(base_output_folder), f"folder {base_output_folder} to load scenario from is not available!"
    sim_manager = SimulationManager(base_output_folder, main_config_path, cesarp.common.init_unit_registry(), load_from_disk=True)
    if sim_manager.is_demand_results_available():
        res_summary = sim_manager.get_all_results_summary()
        print(res_summary)
    else:
        print(f"are you sure simulation was run for scenario saved under {base_output_folder}?")


def debug_sim_single_bldg(fid: int, output_path: Union[str, Path], main_config_path: Union[str, Path, Dict[str, Any]], weather_file_path: Union[str, Path]) -> None:
    """
    Logging output and debugging is a bit doggy with multiprocessing. So it is helpful, if things go wrong, to run the pipeline just for one building without
    the multiprocessing.

    :param fid: building fid to debug
    :type fid: int
    :param output_path: full path of output folder to use to store results for debugged building
    :type output_path: Union[str, Path]
    :param main_config_path: project specifig config, you can either pass the full file path to the config YML file or a dictionary with configuration entries
    :type main_config_path: Union[str, Path, Dict[str, Any]]
    :param weather_file_path: full path of weather file (epw) to use for the simulation run
    :type weather_file_path: Union[str, Path]
    """
    output_path = __abs_path(output_path)
    shutil.rmtree(output_path, ignore_errors=True)
    os.mkdir(output_path)
    run_single_bldg(
        bldg_fid=fid,
        epw_file=str(weather_file_path),
        idf_path=str(output_path / Path(f"fid_{fid}.idf")),
        eplus_output_dir=str(output_path / Path("eplus_res")),
        custom_config=main_config_path,
    )


def run_specific_idf(idf_path: Union[str, Path], output_path: Union[str, Path], weather_file: Union[str, Path], main_config_path: Optional[Union[str, Path]] = None) -> None:
    """
    Run EnergyPlus simulation for a specific IDF File within your project.

    :param idf_path: full path of idf to simulate
    :type idf_path: Union[str, Path]
    :param output_path: full path to folder where to store energy plus outputs
    :type output_path: Union[str, Path]
    :param weather_file: full path to weather file (epw) to use for the simulation
    :type weather_file: Union[str, Path]
    :param main_config_path: YML configuration file in case you have any EnergyPlus specific custom configuration, otherwise None, optional, defaults to None
    :type main_config_path: Optional[Union[str, Path]]
    """
    config = {}
    if main_config_path:
        config = cesarp.common.config_loader.load_config_full(main_config_path)
    cesarp.eplus_adapter.eplus_sim_runner.run_single(idf_path, weather_file, output_path, custom_config=config)


def run_from_command_line_args():
    """
    Example for a Command Line Interface to CESAR-P
    """
    if str(sys.argv[1]).lower() == "help" or len(sys.argv) < 3 or len(sys.argv) > 4:
        print("USAGE: basic_cesar_usage.py your_config.yml output_folder debug_fid")
        print(
            "\tyour_config.yml\t- project configuration with pathes to site vertices file, building information, "
            "weather and settings for CESAR-P. use absolute path or path relative to this script"
        )
        print("\toutput_folder\t- folder where CESAR-P and EnergyPlus outputs for the site are stored.")
        print(
            "\tdebug_fid\t- optional, if you specify this third parameter only that building fid is simulated which "
            "is useful for debugging, as debug output when running multiple buildings is set to per-worker logfiles and thus not so easily to look at"
        )
        exit(0)

    main_config_path = __abs_path(str(sys.argv[1]))
    output_dir = __abs_path(str(sys.argv[2]))
    # shutil.rmtree(__abs_path(output_dir), ignore_errors=True)
    logging.warning(f"Using main config file {main_config_path}. Saving outputs to folder {output_dir}")
    # if a building fid is provided as 2nd parameter when calling the script, only simulate the given building
    if len(sys.argv) >= 4:
        bldg_fid = int(sys.argv[3])
        print("----------SINGLE BUILDING RUN (intended for debugging)----------------")
        weather_file_path = cesarp.common.abs_path(cesarp.common.load_config_full(main_config_path)["MANAGER"]["SINGLE_SITE"]["WEATHER_FILE"], main_config_path)
        debug_sim_single_bldg(bldg_fid, output_dir, main_config_path, weather_file_path)
    else:
        print("----------SITE RUN ----------------")
        run_sim_site(output_dir, main_config_path)


def init_basic_logging_config(log_file):
    """
    Setup python logging. The other option is to init from a logging config file as used in simple_example.
    """
    log_file_handler = logging.FileHandler(log_file, mode="w")
    log_file_handler.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S", handlers=[log_file_handler, console_handler])


if __name__ == "__main__":
    # Set up logging
    # logging.config.fileConfig("logging.conf")  # this logging config is only for the main process, workers log to separate log files which go into a folder, configured in SimulationManager.
    init_basic_logging_config("cesarp-log.log")

    # switch CLI / script mode
    if len(sys.argv) > 1:
        run_from_command_line_args()
    else:

        class Mode(Enum):
            NORMAL_SIM = "normal simulation run"
            DEBUG_BLDG = "debug a single building"
            LOAD_EXISTING = "load existing project from disk"

        # === FOR NON-CLI RUN: DEFINE HERE YOUR PROJECT SETTINGS - note that not all settings are used in all modes

        RUNNING_MODE = Mode.NORMAL_SIM

        MAIN_CONFIG_PATH = __abs_path("main_config.yml")
        OUTPUT_DIR = "./results/basic_cesar_usage"

        # applicable to mode NORMAL_SIM only
        FIDS_TO_USE = range(1, 3)  # set to None to use all buildings;
        DELETE_OLD_RESULTS = True
        DELETE_OLD_LOGS = True

        # applicable to mode DEBUG_BLDG only
        DEBUG_BLDG_FID = 6

        # === END USER INPUTS

        logging.info(f"Using main config file {MAIN_CONFIG_PATH} and output folder {OUTPUT_DIR}.")
        print(f"running in mode {RUNNING_MODE.name}: {RUNNING_MODE.value}")

        try:  # try - except block needed to write unexpected errors to logfile
            if RUNNING_MODE == Mode.NORMAL_SIM:
                if DELETE_OLD_RESULTS:
                    shutil.rmtree(__abs_path(OUTPUT_DIR), ignore_errors=True)
                run_sim_site(OUTPUT_DIR, MAIN_CONFIG_PATH, fids=FIDS_TO_USE, delete_old_logs=DELETE_OLD_LOGS)
                print(f"You find the results in {OUTPUT_DIR}")
                print("Note: Check TIMESTAMP-cesarp-logs folder for logfiles from worker processes and cesarp-debug.log for logfile of main process.")

            if RUNNING_MODE == Mode.DEBUG_BLDG:
                output_folder = __abs_path(f"cesar_run_fid{DEBUG_BLDG_FID}")
                # just expecting the SINGLE_SITE to point to a valid weather file
                single_site_weather = cesarp.common.abs_path(cesarp.common.load_config_full(MAIN_CONFIG_PATH)["MANAGER"]["SINGLE_SITE"]["WEATHER_FILE"], MAIN_CONFIG_PATH)
                debug_sim_single_bldg(DEBUG_BLDG_FID, output_folder, MAIN_CONFIG_PATH, single_site_weather)
                print(f"You find the results in {output_folder}")

            if RUNNING_MODE == Mode.LOAD_EXISTING:
                load_from_disk(OUTPUT_DIR, MAIN_CONFIG_PATH)

        except Exception:
            logging.getLogger("cesarp.main").exception("Exception catched in main...")

    exit(0)
