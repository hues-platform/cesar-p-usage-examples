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

# this script has the # %% tags for running in interactive mode wihtin visual studio code

"""
Get information about the standard CESAR-P archetypes from GraphDB (local, pass a custom config when initializing GraphDBFacade if you want to query remote GraphDB).

Infos queried are:

- U-Value for building elements (wall, window glass, roof, groundfloor)
- Glazing ratio
- Infiltration rate

Data is written to a csv table and printed as diagrams. This gives a view of those parameters dependent on the construction year of a building.

This script is written in Jupyter-Style. The blocks marked with # %% can be run in a Jupyter mode in Visual Studio Code
"""
# %%
import matplotlib.pyplot as plt
import pandas as pd
import cesarp.common
from cesarp.graphdb_access.GraphDBFacade import GraphDBFacade
from cesarp.graphdb_access.BldgElementConstructionReader import BldgElementConstructionReader
from cesarp.graphdb_access.ArchetypicalConstructionGraphDBBased import ArchetypicalConstructionGraphDBBased

# %% initialize archetype factory and graph db access
ureg = cesarp.common.init_unit_registry()

# pass here a custom config if you want remote db access - make sure graphdb access is set up according to installation notes in README of cesar-p-core
db_facade = GraphDBFacade(ureg)
bldg_constr_reader = BldgElementConstructionReader(db_facade._graph_reader, ureg)
years = list(range(1900, 2030))
# the archetype factory interface works with a list of buildings, thus create such a list with fictive buildings
bldg_list = {id: y for id, y in zip(range(len(years)), years)}
dummy_e_carrier = {id: None for id in bldg_list}  # we do not need energy carrier information, thus just set to None
archetype_fact = db_facade.get_graph_construction_archetype_factory(bldg_list, dummy_e_carrier, dummy_e_carrier)

# %% list the archetypes
print("Archetypes are: ")
archetype_year_list = []
for ac, uri in archetype_fact._ageclass_archetype.items():
    print(f"{ac.min_age}, {ac.max_age}, {uri}")

# %% assemble constructional parameters (defaults) depending on construction year (respectively for age classes/constructional archetype)
per_archetype_infos = []
for id, year in bldg_list.items():
    constr_archetype: ArchetypicalConstructionGraphDBBased = archetype_fact.get_archetype_for(id)
    uri = ""  # archetype_fact._get_archetype_uri_for(year) # can be activated when using cesar-p-core > 1.3.1
    u_wall = bldg_constr_reader.get_u_value(constr_archetype.wall_constr.get_value(False))
    u_roof = bldg_constr_reader.get_u_value(constr_archetype.roof_constr.get_value(False))
    u_groundfloor = bldg_constr_reader.get_u_value(constr_archetype.groundfloor_constr.get_value(False))
    u_win = bldg_constr_reader.get_u_value(constr_archetype.window_glass_constr.get_value(False))
    glz_ratio = constr_archetype.get_glazing_ratio()
    infiltration_rate = constr_archetype.get_infiltration_rate()
    per_archetype_infos.append([year, uri, glz_ratio, infiltration_rate, u_wall, u_roof, u_groundfloor, u_win])

archetype_table = pd.DataFrame(
    data=per_archetype_infos, columns=["year_of_construction", "archetyp_uri", "glazing_ratio", "infiltration_rate", "u_wall", "u_roof", "u_groundfloor", "u_windowglass"]
)
archetype_table.set_index("year_of_construction", inplace=True)
archetype_table.to_csv("construction_attributes.csv")

# %% plot glazing ratio and infiltration rate
fig = plt.figure(figsize=(16, 12), dpi=80)
ax1 = fig.add_subplot(111)
ax1.plot(list(archetype_table.index), archetype_table["glazing_ratio"], label="Glazing ratio [0...1]")
ax1.plot(list(archetype_table.index), archetype_table["infiltration_rate"], label="Infiltration rate [ACH]")
plt.grid(True)
# ax1.scatter(x[40:],y[40:], s=10, c='r', marker="o", label='second')
plt.ylabel("rate (% / ACH)", fontsize=20, labelpad=15)
plt.xlabel("construction year", fontsize=20, labelpad=15)
plt.ylim([0, 1])
plt.xlim([1900, 2030])
plt.legend(loc="upper right", fontsize=20)
plt.setp(ax1.get_xticklabels(), fontsize=16)
plt.xticks(rotation=0)
plt.setp(ax1.get_yticklabels(), fontsize=16)
# plt.title("CESAR-P construction properties for different construction years")
plt.savefig("glazing_ratio_infiltration.pdf")
plt.show()

# %% plot u-values
fig = plt.figure(figsize=(16, 12), dpi=80)
ax1 = fig.add_subplot(111)
ax1.plot(list(archetype_table.index), [val.m for val in archetype_table["u_wall"]], label="U-Value walls")
ax1.plot(list(archetype_table.index), [val.m for val in archetype_table["u_roof"]], label="U-Value roof")
ax1.plot(list(archetype_table.index), [val.m for val in archetype_table["u_groundfloor"]], label="U-Value groundfloor")
ax1.plot(list(archetype_table.index), [val.m for val in archetype_table["u_windowglass"]], label="U-Value window glass")
plt.grid(True)
# ax1.scatter(x[40:],y[40:], s=10, c='r', marker="o", label='second')
plt.ylabel("U-Value (W/Kelvin/m2)", fontsize=20, labelpad=15)
plt.xlabel("construction year", fontsize=20, labelpad=15)
plt.xlim([1900, 2030])
plt.legend(loc="upper right", fontsize=20)
plt.setp(ax1.get_xticklabels(), rotation="horizontal", fontsize=16)
plt.xticks(rotation=0)
plt.setp(ax1.get_yticklabels(), fontsize=16)
# plt.title("CESAR-P construction properties for different construction years")
plt.savefig("u-values.pdf")
plt.show()
# %%
