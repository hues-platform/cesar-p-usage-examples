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
but just change some attributes. This is helpful especially if you are using variable profile and you want to keep
the assignment constant over different runs. Some things, as the geometry can only be changed when fully re-creating, 
which you can do with the create_scenario() method of ProjectManager. But keep in mind that with this you do not 
have consistent assignment of profiles in case you use variability.


Limitations of this approach:

- Note that for chaning heating or cooling setpoint you have to generate new operational profils, e.g. based on SIA2024 and 
  edit the heating/cooling setpoint in the input excel data sheet.

- You can theoretically do retrofitting with this approach, however there is a more sophisticated pipeline including a log which
  enables e.g. to track emissions and costs

- If you have the same weather file for the whole site, but you want to do several runs with a different weather file
  a even more custom approach to re-run the IDF to avoid copying too much data without significant information gain is better.

"""
import os
from enum import Enum
import pint
import cesarp.common
from cesarp.manager.ProjectManager import ProjectManager
import logging
import logging.config
from cesarp.model.BuildingModel import BuildingModel
from cesarp.model.WindowConstruction import WindowFrameConstruction
from pint import unit


def __abs_path(path):
    return cesarp.common.config_loader.abs_path(path, os.path.abspath(__file__))


class MyScenarios(Enum):
    BASE = "2015_BASE"
    GLZ_RATIO = "2020_GLZ_RATIO"
    WIN_FRAME = "2015_WIN_FRAME"
    APPLIANCE_EFF = "2015_APPLIANCE_EFF"

    def __str__(self):
        return self.value

    def __lt__(self, other):
        # implementing < operator because it is needed to sort results in collect_result_summaries
        return self.value < other.value


def improve_electric_appliances_efficiency(bldg_model: BuildingModel):
    # assign half of the original electricity demand
    bldg_model.bldg_operation_mapping.get_operation_assignments()[0][1].electric_appliances.power_demand_per_area *= 0.5


def improve_window_frame(bldg_model: BuildingModel):
    # exchanging construction for window frame
    # it is best to assign a new instanc to each model to avoid shared instances accross buildings,
    # which would have unexpected behavior if you want to do changes to one building, because it would then apply to all due to the shared instance.
    ureg = pint.get_application_registry()
    # actually I do not know if that frame is "imporved" compared to the definition in config of cesarp.construction
    new_win_frame_constr = WindowFrameConstruction(
        name="custom_example_win_frame",
        short_name="custom_example_win_frame",
        frame_conductance=7.5 * ureg("W/m**2/K"),
        frame_solar_absorptance=0.4 * ureg("solar_absorptance"),
        frame_visible_absorptance=0.4 * ureg("visible_absorptance"),
        outside_reveal_solar_absorptance=0.4 * ureg("solar_absorptance"),
        emb_co2_emission_per_m2=None,
        emb_non_ren_primary_energy_per_m2=None,
    )
    bldg_model.bldg_construction.window_constr.frame = new_win_frame_constr


def improvement_scenarios(fids_to_use=None):
    ureg = cesarp.common.init_unit_registry()
    # use the set/get unit registry approach as we do not get passed a unit reg instance in the modify methods above...
    pint.set_application_registry(ureg)
    myProj = ProjectManager(__abs_path("../main_config.yml"), __abs_path("../results/scenario_comparison"), fids_to_use=fids_to_use, unit_reg=ureg)

    logging.info(f"trying to load scenario {MyScenarios.BASE}")
    if not myProj.load_saved_scenario(MyScenarios.BASE):
        myProj.create_scenario(MyScenarios.BASE, specific_config_path=None)

    # the configuration sets a different weather file and simulation year, and different glazing ratio input file
    # you would probably only change one parameter to be able to see the effects, but just to show what is possible I adapted two things at once
    logging.info(f"trying to load scenario {MyScenarios.GLZ_RATIO}")
    if not myProj.load_saved_scenario(MyScenarios.GLZ_RATIO):
        myProj.create_scenario(MyScenarios.GLZ_RATIO, specific_config_path=__abs_path("scenario_glz_ratio.yml"))

    logging.info(f"trying to load scenario {MyScenarios.WIN_FRAME}")
    if not myProj.load_saved_scenario(MyScenarios.WIN_FRAME):
        myProj.derive_scenario(MyScenarios.BASE, MyScenarios.WIN_FRAME, improve_window_frame)

    logging.info(f"trying to load scenario {MyScenarios.APPLIANCE_EFF}")
    if not myProj.load_saved_scenario(MyScenarios.APPLIANCE_EFF):
        logging.info(f"derive {MyScenarios.APPLIANCE_EFF} from {MyScenarios.BASE}")
        myProj.derive_scenario(MyScenarios.BASE, MyScenarios.APPLIANCE_EFF, improve_electric_appliances_efficiency)

    logging.info("run necessary simulations")
    myProj.run_not_simulated_scenarios()

    # you can get only part of the result summary columns collected, for more details see method descrIption
    myProj.collect_all_scenario_summaries(summary_res_columns=["Heating Annual", "DHW Annual"], do_overwrite=True)

    [logging.warning(f"In {name} something went wrong for following FID's {sz.failed_fids}") for name, sz in myProj._scenarios.items() if sz.failed_fids]


if __name__ == "__main__":
    logging.config.fileConfig(__abs_path("../logging.conf"))
    logging.getLogger("rdflib").setLevel(logging.ERROR)

    improvement_scenarios([1, 2])
