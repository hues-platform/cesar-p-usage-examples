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
Those functions were used to create additional definitions for the EnergyPlus IDD files to allow for more vertices than 120,
this is supported by E+ but EPPY cannot handle it if the field definitions are not included in the IDD....
"""


def wall_vertices():
    # change the , to ; on the last line and in the existing IDF, change ; to , for the current last vertex
    # adapt N and i for what you need
    N = 363
    for i in range(121, 251):
        print(f"N{N}, \\field Vertex {i} X-coordinate")
        N += 1
        print("\t\\units m")
        print("\t\\type real")
        print(f"N{N}, \\field Vertex {i} Y-coordinate")
        N += 1
        print("\t\\units m")
        print("\t\\type real")
        print(f"N{N}, \\field Vertex {i} Z-coordinate")
        N += 1
        print("\t\\units m")
        print("\t\\type real")


def windowShadingControl_NrWins():
    # WindowShadingControl has list of windows only from EnergyPlus Verison >= 9
    A = 24
    for i in range(11, 101):
        print(f"\tA{A}, \\field Fenestration Surface {i} Name")
        A += 1
        print("\t\t\\type object-list")
        print("\t\t\\object-list GlazedExtSubSurfNames")


if __name__ == "__main__":
    windowShadingControl_NrWins()
