# coding=utf-8
#
# Copyright (c) 2021, Empa, Leonie Fierz, Aaron Bojarski
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
This script was used while developing the graphdb_access package and might
be useful to see how you can work with the graphdb_access package or 
if you want to test accessing new data.

To get properties of the archetypes, there is also the pre_or_postprocessing_scripts/collect_archetype_infos.py
which is actually a bit more tidy.
"""

from cesarp.graphdb_access.BldgElementConstructionReader import BldgElementConstructionReader
from cesarp.graphdb_access.GraphDBReader import GraphDBReader
from cesarp.graphdb_access.GraphDBArchetypicalConstructionFactory import GraphDBArchetypicalConstructionFactory
from cesarp.graphdb_access.LocalFileReader import LocalFileReader
import cesarp.common
from cesarp.model.EnergySource import EnergySource
from cesarp.model.BuildingElement import BuildingElement


def get_some_infos_on_archetype(reader: GraphDBReader, archetype_uri: str):
    myArchetype = reader.get_bldg_elem_construction_archetype(archetype_uri)

    print("\nwall options")
    for wall in myArchetype.walls:
        print(f"{wall.name} with {len(wall.layers)} layers")

    print("\nretrofit for first wall")
    construction = myArchetype.walls[0]
    retrofitted_constr = reader.get_retrofitted_construction(construction)

    for layer in retrofitted_constr.layers:
        if retrofitted_constr.bldg_element == BuildingElement.WINDOW and retrofitted_constr.retrofitted:
            print("Added layer:", layer.short_name, layer.material.short_name)
        elif layer.retrofitted:
            print("Added layer:", layer.short_name, layer.material.short_name, layer.function)
        else:
            print("Same layer: ", layer.short_name, layer.material.short_name, layer.function)

    print("\nDefault Win-Construction:")
    print(reader.get_default_construction(myArchetype.windows, archetype_shortname=myArchetype.short_name))

    myArchetype = reader.get_bldg_elem_construction_archetype(archetype_uri)
    print("\nInfiltration Rate:", reader.get_infiltration_rate(myArchetype.name))
    print(f"\nGlazing Ratio {reader.get_glazing_ratio(myArchetype.name)._min} to {reader.get_glazing_ratio(myArchetype.name)._max}")


def check_archetype_construction_factory(graph_reader):
    bldg_construction_years = {1: 2001, 2: 1950, 3: 2016, 4: 1960}
    factory = GraphDBArchetypicalConstructionFactory(
        bldg_construction_years, {fid: EnergySource.DHW_OTHER for fid in range(1, 5)}, {fid: EnergySource.HEATING_OTHER for fid in range(1, 5)}, graph_reader, ureg
    )

    print("\nchek building archetypes from factory")
    for bldg_id, year_of_constr in bldg_construction_years.items():
        archetype = factory.get_archetype_for(bldg_id)
        print(f"Archetype for building {bldg_id} with construction year {year_of_constr}")
        print(f"infiltration rate: {archetype.get_infiltration_rate()}")
        print(f"wall construction name: {archetype.get_wall_construction().name}")


if __name__ == "__main__":
    ureg = cesarp.common.init_unit_registry()
    graph_reader = LocalFileReader()
    # graph_reader = GraphDBReader()
    custom_config = {"GRAPHDB_ACCESS": {"RETROFIT": {"target_requirement": True}}}
    reader = BldgElementConstructionReader(graph_reader, ureg, custom_config)
    archetype_uri = "http://uesl_data/sources/archetypes/2001_SFH_Archetype"
    get_some_infos_on_archetype(reader, archetype_uri)
    check_archetype_construction_factory(graph_reader)
