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
Example showing how you can use a shp file for the geometry.

NOTE: You need to have geopandas installed to use this example
"""

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
    logging.config.fileConfig(__abs_path("../logging.conf"))

    # the configuration points to the custom constructional archetype factory
    main_config_path = __abs_path("shp_file_geometry_config.yml")
    output_dir = __abs_path("../results/shp_file_geometry")
    shutil.rmtree(output_dir, ignore_errors=True)

    sim_manager = SimulationManager(output_dir, main_config_path, cesarp.common.init_unit_registry())
    sim_manager.run_all_steps()

    print("====================")
    print(f"check out results in {output_dir}")
    print("check archetype assignment in worker log files in folder TIMESTAMP-cesarp-logs. depending on logging settings it is also printed to the console.")
