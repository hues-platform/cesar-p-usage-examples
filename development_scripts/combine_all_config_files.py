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
from typing import Dict, Any
from cesarp.common import config_loader
from shutil import copyfileobj


from cesarp.construction import _default_config_file as cstr_cfg

# emission_and_cost has no config
from cesarp.energy_strategy import _default_config_file as es_cfg
from cesarp.eplus_adapter import _default_config_file as eplus_cfg
from cesarp.geometry import _default_config_file as geom_cfg
from cesarp.graphdb_access import _default_config_file as graph_cfg
from cesarp.manager import _default_config_file as mgr_cfg
from cesarp.operation import _default_config_file as op_cfg
from cesarp.operation.fixed import _default_config_file as op_fixed_cfg
from cesarp.retrofit import _default_config_file as ret_cfg
from cesarp.retrofit.embodied import _default_config_file as ret_emb_cfg
from cesarp.retrofit.energy_perspective_2050 import _default_config_file as ret_ep2050_cfg
from cesarp.SIA2024 import _default_config_file as sia_cfg
from cesarp.site import _default_config_file as site_cfg
from cesarp.weather.swiss_communities import _default_config_file as sc_weather_cfg

"""
Does create a big YAML file with all the configuration parameters from  cesar-p.
All comments are lost, as we parse the files and re-write after merging.
"""

import yaml
from typing import List

ALL_CFG_FILES = [
    cstr_cfg,
    es_cfg,
    geom_cfg,
    graph_cfg,
    mgr_cfg,
    op_cfg,
    ret_cfg,
    sia_cfg,
    site_cfg,
    sc_weather_cfg,
    eplus_cfg,
    op_fixed_cfg,
    ret_emb_cfg,
    ret_ep2050_cfg,
]


def combine_configs_without_comments():
    all_config_dict = {}
    for cfg_file in ALL_CFG_FILES:
        cfg_entries = config_loader.load_config_full(cfg_file, ignore_metadata=False)
        all_config_dict = config_loader.merge_config_recursive(all_config_dict, cfg_entries)
    all_config_file = "all_cesarp_config.yml"
    with open(all_config_file, "w") as f:
        yaml.dump(all_config_dict, f)
    print(f"saved combined configuration to {all_config_file}")


def combine_configs_to_one_file(files_to_append: List[str], main_file: str):
    file_mod = "wb"
    with open(main_file, file_mod) as file_to_append_to:
        for filename_to_be_appended in files_to_append:
            with open(filename_to_be_appended, "rb") as to_be_appended:
                copyfileobj(to_be_appended, file_to_append_to, 1024)


if __name__ == "__main__":
    result_config_file = "cesar-p-config-overview.yaml"
    combine_configs_to_one_file(ALL_CFG_FILES, result_config_file)
    print(f"Combined configuration has been written to {result_config_file}")
    print("please do a bit manual postprocessing: remove copyright-blocks (search and replace); combine all blocks for RETROFIT and OPERATION into one block.")
