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
import sys

import cesarp.common
import cesarp.common.config_loader
from cesarp.manager.SimulationManager import SimulationManager


def __abs_path(path):
    return cesarp.common.abs_path(path, os.path.abspath(__file__))


if __name__ == "__main__":
    # this logging config is only for the main process, workers log to separate log files which go into a folder, configured in SimulationManager.
    logging.config.fileConfig(__abs_path("../logging.conf"))

    # make sure the SIABasedMixedOperationFactory can be found
    sys.path.append(os.path.dirname(__file__))

    main_cfg_path = __abs_path("../main_config.yml")
    op_param_cfg_path = __abs_path("additional_op_params_config.yml")
    main_config = cesarp.common.config_loader.merge_config_recursive(cesarp.common.load_config_full(main_cfg_path), cesarp.common.load_config_full(op_param_cfg_path))
    output_dir = __abs_path("../results/op_params_per_floor")
    shutil.rmtree(output_dir, ignore_errors=True)

    fids_to_use = [1, 2, 3]  # set to None to simulate all buildings
    sim_manager = SimulationManager(output_dir, main_config, cesarp.common.init_unit_registry(), fids_to_use=fids_to_use)
    sim_manager.run_all_steps()

    print("====================")
    print(f"check out results in {output_dir}")
    print("for a quick check if profile assignment worked as expected, you could have a look at the generated IDF files.")
    print("If there are errors, make sure you did run the pre_generate_sia_params.py")
