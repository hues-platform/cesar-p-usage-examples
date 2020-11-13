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
import os
import logging.config
from pathlib import Path
from cesarp.retrofit.energy_perspective_2050.EnergyPerspective2050RetrofitManager import EnergyPerspective2050RetrofitManager
import cesarp.common


def __abs_path(rel_path: str) -> Path:
    return cesarp.common.config_loader.abs_path(rel_path, os.path.abspath(__file__))


if __name__ == "__main__":
    ureg = cesarp.common.init_unit_registry()
    logging.config.fileConfig("logging.conf")

    cfg_path = __abs_path("main_config.yml")
    output_path = __abs_path("results/energystrategy2050_retrofit_example")
    ressources_path = __abs_path("../example_project_files")
    weather_mapping = {
        2015: str(ressources_path / Path("Zurich_2015.epw")),
        2020: str(ressources_path / Path("Zurich_2020.epw")),
        2030: str(ressources_path / Path("Zurich_2030.epw")),
        2035: str(ressources_path / Path("Zurich_2035.epw")),
        2040: str(ressources_path / Path("Zurich_2040.epw")),
        2050: str(ressources_path / Path("Zurich_2050.epw")),
    }

    retfit_mgr = EnergyPerspective2050RetrofitManager(
        ureg=ureg, base_config_path=cfg_path, project_base_path=output_path, weather_per_period=weather_mapping, fids_to_use=range(1, 3)
    )
    retfit_mgr.run()

    exit(0)
