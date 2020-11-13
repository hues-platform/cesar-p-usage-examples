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
from cesarp.geometry.csv_input_parser import read_sitevertices_from_csv
import cesarp.common


def __abs_path(path):
    return cesarp.common.config_loader.abs_path(path, os.path.abspath(__file__))


label_mapping = {"gis_fid": "TARGET_FID", "height": "HEIGHT", "x": "POINT_X", "y": "POINT_Y"}

site_vertices_path = os.path.dirname(__file__) / Path("..") / Path("example_project_files") / Path("SiteVertices.csv")
all_vertices = read_sitevertices_from_csv(__abs_path(site_vertices_path), label_mapping, separator=",")
nr_of_vertices_per_bldg = all_vertices[["gis_fid", "x"]].groupby("gis_fid").count().rename(columns={"x": "nr_of_vertices"}).sort_values(ascending=False, by="nr_of_vertices")
nr_entries_to_print = 30
print(nr_of_vertices_per_bldg.head(nr_entries_to_print))
if len(nr_of_vertices_per_bldg.index) > nr_entries_to_print:
    print(f"only first {nr_entries_to_print} entries were printed, but there are {len(nr_of_vertices_per_bldg.index)}")
