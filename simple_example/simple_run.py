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
import logging.config
import logging
import os
import shutil

import cesarp.common
import cesarp.common.config_loader
from cesarp.manager.SimulationManager import SimulationManager


def __abs_path(path):
    return cesarp.common.abs_path(path, os.path.abspath(__file__))


if __name__ == "__main__":
    # note: expected to be run in simple_example folder - otherwise adapt the path specifications as needed

    logging.config.fileConfig(
        __abs_path("logging.conf")
    )  # this logging config is only for the main process, workers log to separate log files which go into a folder, configured in SimulationManager.

    main_config_path = __abs_path("simple_main_config.yml")
    output_dir = __abs_path("./results/example")
    shutil.rmtree(output_dir, ignore_errors=True)

    fids_to_use = [1, 2, 3]  # set to None to simulate all buildings
    sim_manager = SimulationManager(output_dir, main_config_path, cesarp.common.init_unit_registry(), fids_to_use=fids_to_use)
    sim_manager.run_all_steps()
    zip_path = sim_manager.save_to_zip(main_script_path=__file__)
    print("\n=========PROCESS FINISHED ===========")
    print(f"You find the results in {output_dir}")
    print(f"Project has been saved to {zip_path}, including all input files so it can be transfered to another computer.")
