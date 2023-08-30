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
Example using a custom IDF Writer

NOTE: THIS EXAMPLE ONLY WORKS WITH THE BRANCH feature/config_idf_write OF THE CESARP-CORE PROJECT
"""
import logging.config
import logging
import os
import shutil
import sys

import cesarp.common
import cesarp.common.config_loader
from cesarp.manager.SimulationManager import SimulationManager
from cesarp.manager.debug_methods import run_single_bldg
from pathlib import Path
from typing import Union, Dict, Any


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

def __abs_path(path):
    return cesarp.common.abs_path(path, os.path.abspath(__file__))


if __name__ == "__main__":
    # NOTE: THIS EXAMPLE ONLY WORKS WITH THE BRANCH feature/config_idf_write OF THE CESARP-CORE PROJECT

    # this logging config is only for the main process, workers log to separate log files which go into a folder, configured in SimulationManager.
    logging.config.fileConfig(__abs_path("../logging.conf"))

    # make sure the SIABasedMixedOperationFactory can be found
    sys.path.append(os.path.dirname(__file__))

    main_cfg_path = __abs_path("../main_config.yml")
    # the idf_writer_config.yml points to our custom factory
    idf_writer_cfg_path = __abs_path("custom_idf_writer_config.yml")
    # you could also add this configuration lines to your main config, here we just did want to reuse the main_config
    # and thus parse and merge those two custom configs before passing them to the Simulation manager
    main_config = cesarp.common.config_loader.merge_config_recursive(cesarp.common.load_config_full(main_cfg_path), cesarp.common.load_config_full(idf_writer_cfg_path))
    output_dir = __abs_path("../results/custom_idf_writer")
    shutil.rmtree(output_dir, ignore_errors=True)
    single_site_weather = cesarp.common.abs_path(main_config["MANAGER"]["SINGLE_SITE"]["WEATHER_FILE"], main_cfg_path)
    # for runing a test on a single building, uncomment the following two lines:
    # debug_sim_single_bldg(1, output_dir, main_config, single_site_weather)
    # exit()
    fids_to_use = None  # set to None to simulate all buildings or use [1]
    sim_manager = SimulationManager(output_dir, main_config, cesarp.common.init_unit_registry(), fids_to_use=fids_to_use)
    try:
        sim_manager.create_bldg_models()
        sim_manager.create_IDFs()
        sim_manager.save_bldg_containers()
    except Exception as e:
        sim_manager.save_bldg_containers()
        raise e()

    print("====================")
    print(f"check out results in {output_dir}")
    print("for a quick check if profile assignment worked as expected, you could have a look at the generated IDF files.")
