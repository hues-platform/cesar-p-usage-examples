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
Options for postprocessing your results after a finished simulation.

- A: Reload the summary result, combine it with per-building input data used and aggregate as you wish.
- B: Get some more results out of raw EnergyPlus results
- C: Get results values from saved BuildingContainer objects

Do run simple example prior to run this script. 
To process the data of your own simulation, adapt the variables *base_cesarp_output* and *main_cfg_path*.

"""
import os
import pandas as pd
from pathlib import Path
from cesarp.manager.SimulationManager import SimulationManager
from cesarp.eplus_adapter.idf_strings import ResultsFrequency
from cesarp.eplus_adapter.EPlusEioResultAnalyzer import EPlusEioResultAnalyzer
import cesarp.common
from cesarp.common.csv_reader import read_csvy_raw


def aggreagte_from_summary(sim_manager: SimulationManager):
    """A - RELOAD AND AGGREGATE ANNUAL RESULTS BASED ON SUMMARY OUTPUT FILES"""
    summary_results_file = sim_manager._storage.get_result_summary_filepath()
    per_bldg_inputs_file = sim_manager._storage.get_bldg_infos_used_filepath()
    (metadata, all_results) = read_csvy_raw(summary_results_file, separator=";", header=[0, 1], index_col=0)
    (metadata, per_bldg_inputs_used) = read_csvy_raw(per_bldg_inputs_file, separator=";", index_col="gis_fid")

    # add unit columns index level, so that the join works smoothly
    # (just to show how it would work, as we drop the unit level before the group by it would be more
    # efficient to drop unit level of summary res before joining than adding the level to the per bldg infos)
    per_bldg_inputs_used.columns = pd.MultiIndex.from_product([[""], per_bldg_inputs_used.columns])
    all_data = all_results.join(per_bldg_inputs_used)

    # I did not manage to get the groupby working with the columns multiindex
    all_data = all_data.droplevel("unit", axis="columns")
    # for the simple example this does nothing as each building has a different year of construction
    sum_per_construction_year = all_data.groupby(by=["year_of_construction"], axis="index").sum()
    print("\n\n===== A: Sum of annual results grouped by construction year =====\n")
    print(sum_per_construction_year)


def extract_from_raw_eplus_res(sim_manager: SimulationManager):
    """B - EXTRACT VALUES FROM RAW ENERGY PLUS OUTPUT"""

    # make sure the results you query here are actually in the ESO result file
    # to get the names of the variables that can be queried check the rdd/mdd files after a first test-run
    # (more details: https://www.energyplus.net/sites/default/files/docs/site_v8.3.0/InputOutputReference/05-InputForOutput/index.html)
    # once you have those names, add them in the configuration of package cesarp.eplus_adapter OUTPUT_VARS / OUTPUT_METER
    hourly_air_temp = sim_manager.collect_custom_results(["Zone Air Temperature"], results_frequency=ResultsFrequency.HOURLY)
    print("\n\n===== B: Hourly Zone Air Temperature =====\n")
    print(hourly_air_temp)

    # if you need results from *.eio results file, you can access with
    # eppy does not provide a parser, so we did have to parse the file ourselfes - only the total floor area can be queried currently, if you need any other
    # information please extend the EPlusEioResultAnalyzer
    # to access the total floor area you better use the summary results file
    print("\n\n===== B: Reading variable form eio results - total floor area =====\n")
    print({fid: EPlusEioResultAnalyzer(res_folder, sim_manager._unit_reg, custom_config={}).get_total_floor_area() for fid, res_folder in sim_manager.output_folders.items()})


def results_from_bldg_container(sim_manager: SimulationManager):
    """C - QUERY RESULTS FROM Building Container FROM RAW ENERGY PLUS OUTPUT"""

    # make sure the results you query here are actually in the ESO result file
    # to get the names of the variables that can be queried check the rdd/mdd files after a first test-run
    # (more details: https://www.energyplus.net/sites/default/files/docs/site_v8.3.0/InputOutputReference/05-InputForOutput/index.html)
    # once you have those names, add them in the configuration of package cesarp.eplus_adapter OUTPUT_VARS / OUTPUT_METER
    per_bldg_data_dict = {
        fid: [ctr.get_energy_demand_sim_res().tot_heating_demand / ctr.get_energy_demand_sim_res().total_floor_area, ctr.get_bldg_model().bldg_construction.glazing_ratio]
        if ctr.has_demand_result() and ctr.has_bldg_model()
        else []
        for fid, ctr in sim_manager.bldg_containers.items()
    }
    per_bldg_data = pd.DataFrame.from_dict(per_bldg_data_dict, columns=["heating demand", "glazing_ratio"], orient="index")
    print("\n\n===== C: Get results from building containers - Heating demand along with glazing ratio =====\n")
    print(per_bldg_data.sort_values("glazing_ratio", ascending=False))


# the name guard is important if we use SimulationManager and call any method using the worker pool - without this guard each worker will execute all lines of this main script again....
if __name__ == "__main__":
    base_cesarp_output = os.path.dirname(__file__) / Path("..") / Path("simple_example") / Path("results") / Path("example")  # must contain folder named bldg_containers
    main_cfg_path = os.path.dirname(__file__) / Path("..") / Path("simple_example") / Path("simple_main_config.yml")

    sim_manager = SimulationManager(base_cesarp_output, main_cfg_path, cesarp.common.init_unit_registry(), load_from_disk=True)

    aggreagte_from_summary(sim_manager)
    extract_from_raw_eplus_res(sim_manager)
    results_from_bldg_container(sim_manager)
