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
Does parse a site vertices file (csv) and counts the number of vertices per building.
Might be useful to check your building geometries and to find building with many vertices, 
which will be slow to simulate. Their footprints might be made less complex without loosing
much accuracy. Note that cesar-p support up to 250 vertices (limiting is the IDD respectively eppy)

Run simple example prior to run this script or adapt pathes to your project.
"""

import os
from pathlib import Path
from cesarp.geometry.csv_input_parser import read_sitevertices_from_csv
import cesarp.common


def __abs_path(path):
    return cesarp.common.config_loader.abs_path(path, os.path.abspath(__file__))


SITE_VERTICES_PATH = os.path.dirname(__file__) / Path("..") / Path("example_project_files") / Path("SiteVertices.csv")
LABEL_MAPPING = {"gis_fid": "TARGET_FID", "height": "HEIGHT", "x": "POINT_X", "y": "POINT_Y"}  # labels in your SiteVertices.csv
NR_ENTRIES_TO_PRINT = 30  # just how many buildings shall be shown (building are sorted by number of vertices)

all_vertices = read_sitevertices_from_csv(__abs_path(SITE_VERTICES_PATH), LABEL_MAPPING, separator=",")
nr_of_vertices_per_bldg = all_vertices[["gis_fid", "x"]].groupby("gis_fid").count().rename(columns={"x": "nr_of_vertices"}).sort_values(ascending=False, by="nr_of_vertices")


print(nr_of_vertices_per_bldg.head(NR_ENTRIES_TO_PRINT))
if len(nr_of_vertices_per_bldg.index) > NR_ENTRIES_TO_PRINT:
    print(f"only first {NR_ENTRIES_TO_PRINT} entries were printed, but there are {len(nr_of_vertices_per_bldg.index)}")
