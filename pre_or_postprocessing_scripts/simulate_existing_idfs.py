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
from pathlib import Path

import cesarp.common
import cesarp.common.filehandling
import cesarp.eplus_adapter.eplus_sim_runner
import cesarp.eplus_adapter.eplus_eso_results_handling as eplus_eso_results_handling
from cesarp.results.ResultProcessor import ResultProcessor


def __abs_path(path):
    return cesarp.common.config_loader.abs_path(path, os.path.abspath(__file__))


_RESULT_FOLDER = __abs_path(Path("..") / Path("simple_example") / Path("results") / Path("simulation_weather2020"))
_IDF_FOLDER = __abs_path(Path("..") / Path("simple_example") / Path("results") / Path("example") / Path("idfs"))
_CONFIG = __abs_path(Path("..") / Path("simple_example") / Path("simple_main_config.yml"))


if __name__ == "__main__":
    my_config = cesarp.common.config_loader.load_config_full(_CONFIG)

    idf_pathes = cesarp.common.filehandling.scan_directory(_IDF_FOLDER, "fid_{}.idf")
    weather_file_path = __abs_path(Path("..") / Path("example_project_files") / Path("Zurich_2020.epw"))
    weather_files = {idx: weather_file_path for idx in idf_pathes.keys()}
    result_folders = {idx: str(_RESULT_FOLDER / Path("fid_{}".format(idx))) for idx in idf_pathes.keys()}
    cesarp.eplus_adapter.eplus_sim_runner.run_batch(idf_pathes, weather_files, result_folders, -1, my_config)
    ureg = cesarp.common.init_unit_registry()
    summary_res = {idx: eplus_eso_results_handling.collect_cesar_simulation_summary(res_folder, ureg) for idx, res_folder in result_folders.items()}
    summary_res_as_df = ResultProcessor.convert_demand_results_to_df(summary_res, ureg)
    summary_res_file = _RESULT_FOLDER / Path("summary.csv")
    summary_res_as_df.to_csv(summary_res_file, sep=";", float_format="%.4f")
    print(f"result summary written to {summary_res_file}")
