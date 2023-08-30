# coding=utf-8
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
Example showing the use of :py:class:`cesarp.retrofit.all_bldgs.SimpleRetrofitManager`.
Does simulate a base case and two retrofit scenario, first retrofitting the roofs, and a second retrofitting walls, windows and groundfloor for all buildings.

If you have some more specific needs for retrofit control, e.g. only some buildings shall be retrofitted according to certain criteria or a input list, 
you can create your own retrofit manager class.

For more details see :py:mod:`cesarp.retrofit`, for this example especially :py:class:`cesarp.retrofit.all_bldgs.SimpleRetrofitManager`
"""

import os
import logging.config
from pathlib import Path
from cesarp.retrofit.all_bldgs.SimpleRetrofitManager import SimpleRetrofitManager
from cesarp.model.BuildingElement import BuildingElement
import cesarp.common
from cesarp.retrofit.RetrofitLog import LOG_KEYS


def __abs_path(rel_path):
    return cesarp.common.config_loader.abs_path(rel_path, os.path.abspath(__file__))


if __name__ == "__main__":
    ureg = cesarp.common.init_unit_registry()
    logging.config.fileConfig(__abs_path("logging.conf"))

    cfg_path = __abs_path("main_config.yml")
    output_path = __abs_path(Path("results") / Path("retrofit_simple_example"))

    retfit_mgr = SimpleRetrofitManager(ureg=ureg, base_config=cfg_path, base_scenario_name="orig", project_path=output_path, year_of_retrofit=2020, fids_to_use=[3, 4, 5])
    roof_ret_sum_costs_emissions = retfit_mgr.add_retrofit_case("roof", [BuildingElement.ROOF])
    wall_win_groundf_ret_sum_costs_emissions = retfit_mgr.add_retrofit_case("wall_win_groundf", [BuildingElement.WALL, BuildingElement.WINDOW, BuildingElement.GROUNDFLOOR])
    logging.info(f"roof retrofit case:\n{roof_ret_sum_costs_emissions}")
    logging.info(f"wall and windows retrofit case:\n{wall_win_groundf_ret_sum_costs_emissions}")
    retfit_mgr.run_simulations()

    exit(0)
