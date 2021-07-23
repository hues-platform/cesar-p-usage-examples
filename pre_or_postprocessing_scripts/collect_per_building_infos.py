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
Does get some example properties of the building models from a existing project.

Run simple example prior to run this script or adapt pathes to your project.
"""

import os
from pathlib import Path
from cesarp.manager.SimulationManager import SimulationManager
import cesarp.common


base_cesarp_output = os.path.dirname(__file__) / Path("..") / Path("simple_example") / Path("results") / Path("example")  # must contain folder named bldg_containers
main_cfg_path = os.path.dirname(__file__) / Path("..") / Path("simple_example") / Path("simple_main_config.yml")


sim_manager = SimulationManager(base_cesarp_output, main_cfg_path, cesarp.common.init_unit_registry(), load_from_disk=True)

roof_constructions = {
    fid: ctr.get_bldg_model().bldg_construction.roof_constr.short_name if ctr.has_bldg_model() else "bldg model is missing" for fid, ctr in sim_manager.bldg_containers.items()
}
print("Roof construction: " + str(roof_constructions))
neighbours_per_bldg = {fid: len(ctr.get_bldg_model().neighbours) if ctr.has_bldg_model() else 0 for fid, ctr in sim_manager.bldg_containers.items()}
print("Number of neighbouring buildings: " + str(neighbours_per_bldg))
