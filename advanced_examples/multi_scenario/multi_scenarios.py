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
This example does demonstrate how you can run multiple scenarios without re-generating the building models from scratch,
but just change some attributes.

If you have the same weather file for the whole site, but you want to do several runs with a different weather file
a even more custom approach to re-run the IDF to avoid copying too much data without significant information gain.
"""
import os
from enum import Enum
import cesarp.common
from cesarp.manager.ProjectManager import ProjectManager
import logging
import logging.config
from cesarp.model.BuildingModel import BuildingModel


def __abs_path(path):
    return cesarp.common.config_loader.abs_path(path, os.path.abspath(__file__))


class MyScnearios(Enum):
    ZH_2015 = "ZH_2015"
    ZH_2020 = "ZH_2020"
    ZH_2020_EL_EFF = "ZH_2020_EL_EFF"

    def __str__(self):
        return self.value

    def __lt__(self, other):
        # implementing < operator because it is needed to sort results in collect_result_summaries
        return self.value < other.value


def improve_electric_appliances_efficiency(bldg_model: BuildingModel):
    # assign half of the original electricity demand
    bldg_model.bldg_operation_mapping.get_operation_assignments()[0][1].electric_appliances.power_demand_per_area *= 0.5


def climate_change_scenarios(fids_to_use=None):
    myProj = ProjectManager(__abs_path("../main_config.yml"), __abs_path("../results/climate_comparison"), fids_to_use=fids_to_use)

    logging.info(f"trying to load scenario {MyScnearios.ZH_2015}")
    if not myProj.load_saved_scenario(MyScnearios.ZH_2015):
        myProj.create_scenario(MyScnearios.ZH_2015, specific_config_path=None)

    logging.info(f"trying to load scenario {MyScnearios.ZH_2020}")
    if not myProj.load_saved_scenario(MyScnearios.ZH_2020):
        myProj.create_scenario(MyScnearios.ZH_2020, specific_config_path=__abs_path("scenario_ZH2020.yml"))

    logging.info(f"trying to load scenario {MyScnearios.ZH_2020_EL_EFF}")
    if not myProj.load_saved_scenario(MyScnearios.ZH_2020_EL_EFF):
        logging.info(f"derive {MyScnearios.ZH_2020_EL_EFF} from {MyScnearios.ZH_2020}")
        myProj.derive_scenario(MyScnearios.ZH_2020, MyScnearios.ZH_2020_EL_EFF, improve_electric_appliances_efficiency)

    logging.info("run necessary simulations")
    myProj.run_not_simulated_scenarios()

    # you can get only part of the result summary columns collected, for more details see method descrIption
    myProj.collect_all_scenario_summaries(summary_res_columns=["Heating Annual", "DHW Annual"], do_overwrite=True)

    [logging.warning(f"In {name} something went wrong for following FID's {sz.failed_fids}") for name, sz in myProj._scenarios.items() if sz.failed_fids]


if __name__ == "__main__":
    logging.config.fileConfig(__abs_path("../logging.conf"))
    logging.getLogger("rdflib").setLevel(logging.ERROR)

    climate_change_scenarios([1, 2])
