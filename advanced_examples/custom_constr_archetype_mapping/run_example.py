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
Example showing how you can control the mapping of constructional archetypes to your building using 
a file defining the archetype to use for each building.

If you just want to use other archetypes than the default ones and map them by construction year of the building you can 
do so by adapting the archetype URIs in the configuration for package cesarp.graphdb_access.

Note that this is example only is applicable if you use the construction package based on the GraphDB (graphdb_access) 
and not when using the IDF based oen (idf_constructions_db_access).
"""

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

    # make sure the BuildingSpecificArechtypConstrctionFactory can be found
    sys.path.append(os.path.dirname(__file__))

    # the configuration points to the custom constructional archetype factory
    main_config_path = __abs_path("custom_constr_archetype_config.yml")
    output_dir = __abs_path("../results/custom_constr_archetype")
    shutil.rmtree(output_dir, ignore_errors=True)

    fids_to_use = [1, 2, 8]  # set to None to simulate all buildings
    sim_manager = SimulationManager(output_dir, main_config_path, cesarp.common.init_unit_registry(), fids_to_use=fids_to_use)
    sim_manager.run_all_steps()

    print("====================")
    print(f"check out results in {output_dir}")
    print("check archetype assignment in worker log files in folder TIMESTAMP-cesarp-logs. depending on logging settings it is also printed to the console.")
