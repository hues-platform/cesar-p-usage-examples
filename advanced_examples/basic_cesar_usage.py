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


# adding src package to python search path to be able to run this script from command line without installing cesar,
# as this is not yet possible
import os
import shutil
from pathlib import Path
import sys
import logging
import logging.config

# !!!! UNCOMMENT THIS IF CESAR IMPORT DOES NOT WORK
# cesar_package_path = os.path.abspath(os.path.dirname(__file__) / Path("../../"))
# print("adding cesar src to python search path: ", cesar_package_path)
# sys.path.append(cesar_package_path)

from cesarp.manager.SimulationManager import SimulationManager
import cesarp.common
import cesarp.eplus_adapter.eplus_eso_results_handling
from cesarp.eplus_adapter.idf_strings import ResultsFrequency
from cesarp.manager.debug_methods import run_single_bldg


def __abs_path(path):
    return cesarp.common.config_loader.abs_path(path, os.path.abspath(__file__))


def run_sim_site(base_output_folder, main_config_path, fids=None):
    base_output_folder = __abs_path(base_output_folder)
    assert not os.path.exists(base_output_folder), f"output folder {base_output_folder} already exists - please specify a non-existing folder for cesar-p outputs."
    sim_manager = SimulationManager(base_output_folder, main_config_path, cesarp.common.init_unit_registry(), fids_to_use=fids, load_from_disk=False)

    sim_manager.run_all_steps()
    zip_path = sim_manager.save_to_zip(main_script_path=__file__, save_folder_path=os.path.dirname(__file__), include_idfs=False, include_eplus_output=False, include_src_pck=True)
    print(f"Project has been saved to {zip_path}, including all input files so it can be transfered to another computer.")

    # if you need different result parameters, you have to make sure that energy plus reports them. Do so by using the configuration parameters from eplus_adapter package, namely
    # "OUTPUR_METER" and "OUTPUT_VARS", see cesarp.eplus_adapter.default_config.yml. You can overwrite those parameters in your project config, in this example that would be main_config.yml.
    # Also make sure that the reporting frequency in the configuration and in the callect_results_in_parallel() call match.
    result_series_frame = sim_manager.collect_custom_results(result_keys=["DistrictHeating:HVAC", "DistrictHeating:Building"], results_frequency=ResultsFrequency.HOURLY)
    # you can postprocess the results as you like, e.g. save to a file
    result_series_frame.to_csv(__abs_path(base_output_folder) / Path("hourly_results.csv"))

    if sim_manager.failed_fids:
        logging.warning(f"Something went wrong for following FID's {sim_manager.failed_fids}")


def load_from_disk(base_output_folder, main_config_path):
    base_output_folder = __abs_path(base_output_folder)
    assert os.path.exists(base_output_folder), f"folder {base_output_folder} to load scenario from is not available!"
    sim_manager = SimulationManager(base_output_folder, main_config_path, cesarp.common.init_unit_registry(), load_from_disk=True)
    if sim_manager.is_demand_results_available():
        res_summary = sim_manager.get_all_results_summary()
        print(res_summary)
    else:
        print(f"are you sure simulation was run for scenario saved under {base_output_folder}?")


def debug_sim_single_bldg(fid, output_path, main_config_path, weather_file_path):
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


def run_specific_idf(idf_path, output_path, weather_file, main_config_path):
    config = cesarp.common.config_loader.load_config_full(main_config_path)
    cesarp.eplus_adapter.eplus_sim_runner.run_single(idf_path, weather_file, output_path, custom_config=config)


def run_from_command_line_args():
    if str(sys.argv[1]).lower() == "help" or len(sys.argv) < 3 or len(sys.argv) > 4:
        print("USAGE: basic_cesar_usage.py your_config.yml output_folder debug_fid")
        print(
            "\tyour_config.yml\t- project configuration with pathes to site vertices file, building information, "
            "weahter and settings for CESAR-P. use absolute path or path relative to this script"
        )
        print("\toutput_folder\t- folder where CESAR-P and EnergyPlus outputs for the site are stored.")
        print(
            "\tdebug_fid\t- optional, if you specify this third parameter only that building fid is simulated which "
            "is useful for debugging, as debug output when running multiple buildings is not very readably due to parallelization"
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
        debug_sim_single_bldg(bldg_fid, output_dir, main_config_path)
    else:
        print("----------SITE RUN ----------------")
        run_sim_site(output_dir, main_config_path)


def init_basic_logging_config(log_file):
    log_file_handler = logging.FileHandler(log_file, mode="w")
    log_file_handler.setLevel(logging.DEBUG)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S", handlers=[log_file_handler, console_handler])


if __name__ == "__main__":
    # README
    # This script is an example, it makes sense that you create your own script for each project with only what you need
    # Have a look at the defined functions above as well to see what options you have or when you need custom
    # postprocessing.
    # It shows how you use the main API, the SimulationManager. For more advanced CESAR-P usage, see folder advanced_examples

    # logging.config.fileConfig("logging.conf")  # this logging config is only for the main process, workers log to separate log files which go into a folder, configured in SimulationManager.
    init_basic_logging_config("cesarp-log.log")
    if len(sys.argv) > 1:
        run_from_command_line_args()
    else:
        main_config_path = __abs_path("main_config.yml")
        output_dir = "./results/basic_example_results"
        # shutil.rmtree(__abs_path(output_dir), ignore_errors=True)
        logging.info(f"Using main config file {main_config_path} and saving outputs to {output_dir}.")

        try:  # try - except block needed to write unexpected errors to logfile

            # === run simulation for bldg fid 1,2 ===
            run_sim_site(output_dir, main_config_path, fids=range(1, 2))

            # === debug a single building ===
            # WEATHER_FILE = __abs_path(".." / Path("example_project_files") / Path("Zurich_2015.epw"))
            # bldg_fid = 9
            # debug_sim_single_bldg(bldg_fid, f"cesar_run_fid{bldg_fid}", main_config_path, WEATHER_FILE)

            # === load from disk ==== #
            # load_from_disk(output_dir, main_config_path)

        except Exception:
            logging.getLogger("cesarp.main").exception("Exception catched in main...")

        print(f"You find the results in {output_dir}")
        print("Note: Check TIMESTAMP-cesarp-logs folder for logfiles from worker processes and cesarp-debug.log for logfile of main process.")
    exit(0)
