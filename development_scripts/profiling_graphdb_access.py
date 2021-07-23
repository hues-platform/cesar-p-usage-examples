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
Querying the information for the GraphDB was not performant.
This script uses the python profiling to figure out which parts did make up most of the time.
Based on this, the caching mechanism for materials was introduced in *cesarp.graphdb_access.BldgElementConstructionReader*
"""
import logging
import cProfile
import pstats

import cesarp.common
from cesarp.model.EnergySource import EnergySource
from cesarp.graphdb_access.GraphDBArchetypicalConstructionFactory import GraphDBArchetypicalConstructionFactory
from cesarp.graphdb_access.LocalFileReader import LocalFileReader


def get_archetype():
    ureg = cesarp.common.init_unit_registry()
    local_reader = LocalFileReader()
    custom_config = {"GRAPHDB_ACCESS": {"ARCHETYPES": {"1948_SFH_ARCHETYPE": {"DEFAULT_CONSTRUCTION_SPECIFIC": {"ACTIVE": False}}}}}

    factory = GraphDBArchetypicalConstructionFactory(
        {1: 2001, 2: 1950, 3: 2018, 4: 2017},
        {fid: EnergySource.DHW_OTHER for fid in range(1, 5)},
        {fid: EnergySource.HEATING_OTHER for fid in range(1, 5)},
        local_reader,
        ureg,
        custom_config,
    )
    archetype2001 = factory.get_archetype_for(1)
    archetype2001 = factory.get_archetype_for(2)
    archetype2001 = factory.get_archetype_for(3)
    archetype2001 = factory.get_archetype_for(4)
    inf_rate = archetype2001.get_infiltration_rate()
    print(inf_rate)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    cProfile.run("get_archetype()", "get_archetype_stats")
    p = pstats.Stats("get_archetype_stats")
    p.sort_stats(pstats.SortKey.CUMULATIVE).print_stats(100)
