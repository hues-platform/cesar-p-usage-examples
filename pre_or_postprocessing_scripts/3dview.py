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
this script converts a IDF file to a 3d geometry you can view e.g. in an online viewer
useful to check your building footprints are as you expect and to check how cesar-p creates the building geometry incl adjacencies, neighbours and windows

it might be that the process does flip buildings overhead or so, so be careful when using it

run the basic example prior to running this script to have idf files available to convert
"""
from geomeppy import IDF  # install geomeppy in your environment with pip install geomeppy
from pathlib import Path
import os

if __name__ == "__main__":
    IDF.setiddname("C:/EnergyPlusV9-3-0/Energy+.idd")  # make sure to set IDD matching your IDF
    base = os.path.dirname(__file__) / Path("..") / Path("simple_example") / Path("results") / Path("example") / Path("idfs")
    idf_path = f"{base}/fid_2.idf"
    dest_path = f"{base}/fid_2.obj"
    idf = IDF(idf_path)
    idf.to_obj(fname=dest_path)
    print(f"building 3D object has been saved to {dest_path}. ZIP the .obj an .mtl file and upload to www.creators3d.com/online-viewer to visualize.")
