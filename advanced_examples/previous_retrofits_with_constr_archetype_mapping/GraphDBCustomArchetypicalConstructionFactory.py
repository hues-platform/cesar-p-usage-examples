# coding=utf-8
#
# Copyright (c) 2021, Empa, Leonie Fierz, Aaron Bojarski, Ricardo Parreira da Silva, Sven Eggimann.
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
from typing import Dict, Any
import pint
import logging
import yaml
import cesarp.common
from cesarp.common.AgeClass import AgeClass
from cesarp.construction.construction_protocols import ArchetypicalBuildingConstruction
from cesarp.construction.ConstructionBasics import ConstructionBasics
from cesarp.model.Construction import Construction, BuildingElement
from cesarp.model.EnergySource import EnergySource

from cesarp.graphdb_access.BldgElementConstructionReader import BldgElementConstructionReader, GraphReaderProtocol, BuildingElementConstrcutionsArchetype
from cesarp.graphdb_access.ArchetypicalConstructionGraphDBBased import ArchetypicalConstructionGraphDBBased
from cesarp.graphdb_access import _default_config_file
from cesarp.model.WindowConstruction import WindowGlassConstruction


class GraphDBCustomArchetypicalConstructionFactory:
    """
    Manages the constructional archetype.
    In the initialization you have to pass the information per building needed to get the appropriate archetype.
    After initialization, you call get_archetype_for(bldg_fid) for each of your buildings.
    Note that archetypes are cached, if several buildings use the same archetype they are not re-constructed.
    """

    def __init__(
        self,
        bldg_fid_to_year_of_constr_lookup: Dict[int, int],
        bldg_fid_to_dhw_ecarrier_lookup: Dict[int, EnergySource],
        bldg_fid_to_heating_ecarrier_lookup: Dict[int, EnergySource],
        graph_data_reader: GraphReaderProtocol,
        ureg: pint.UnitRegistry,
        custom_config: Dict[str, Any] = {},
    ):
        self._ureg = ureg
        self._cfg = cesarp.common.config_loader.load_config_for_package(_default_config_file, "graphdb_access", custom_config)
        self._bldg_fid_to_year_of_constr_lookup = bldg_fid_to_year_of_constr_lookup
        self._bldg_fid_to_dhw_ecarrier_lookup = bldg_fid_to_dhw_ecarrier_lookup
        self._bldg_fid_to_heating_ecarrier_lookup = bldg_fid_to_heating_ecarrier_lookup
        self._constr_reader = BldgElementConstructionReader(graph_data_reader, ureg, custom_config)
        self._construction_basics = ConstructionBasics(self._ureg, custom_config)
        self._ageclass_archetype = self._init_age_class_lookup()
        self._construction_cache: Dict[str, BuildingElementConstrcutionsArchetype] = dict()  # key is archetype URI
        self._bldg_fid_to_year_of_retrofit_per_constr_lookup = self._init_year_of_retrofit_per_constr_lookup()

    def _init_age_class_lookup(self) -> Dict[AgeClass, str]:
        ageclass_archetype = {}
        for archetype_shortname, archetype_cfg in self._cfg["ARCHETYPES"].items():
            arch_uri = archetype_cfg["URI"]
            age_class = self._constr_reader.get_age_class_of_archetype(arch_uri)
            ageclass_archetype[age_class] = arch_uri

        if not AgeClass.are_age_classes_consecutive(list(ageclass_archetype.keys())):
            logging.error("age classes retrieved from database are not consecutive. check min/max age of the used age classes so that there are neighter gaps nor overlaps.")
        return ageclass_archetype

    def _init_year_of_retrofit_per_constr_lookup(self) -> Dict[int, Dict[str, int]]:
        config_file = os.path.dirname(os.path.abspath(__file__)) + "/graph_db_custom_archetypical_config.yml"
        with open(config_file, "r", encoding="utf-8") as ymlfile:
            config = yaml.load(ymlfile, Loader=yaml.SafeLoader)
            config["BLDG_PAST_RETROFIT_PER_BLDG_FILE"]["PATH"] = cesarp.common.abs_path(config["BLDG_PAST_RETROFIT_PER_BLDG_FILE"]["PATH"], __file__)
        all_bldgs_year_of_retrofit = cesarp.common.csv_reader.read_csvy(
            config["BLDG_PAST_RETROFIT_PER_BLDG_FILE"]["PATH"],
            ["gis_fid", "year_of_wall_retrofit", "year_of_roof_retrofit", "year_of_groundfloor_retrofit", "year_of_window_retrofit"],
            config["BLDG_PAST_RETROFIT_PER_BLDG_FILE"]["LABELS"],
            config["BLDG_PAST_RETROFIT_PER_BLDG_FILE"]["SEPARATOR"],
            "gis_fid",
        )
        return all_bldgs_year_of_retrofit.to_dict(orient="index")

    def get_archetype_for(self, bldg_fid: int) -> ArchetypicalBuildingConstruction:
        year_of_construction = self._bldg_fid_to_year_of_constr_lookup[bldg_fid]
        try:
            archetype_uri = self._get_archetype_uri_for(year_of_construction)
        except Exception:
            logging.error(f"no archetype found for building with fid {bldg_fid} and year of construction {year_of_construction}")

        if archetype_uri in self._construction_cache.keys():
            constr_from_graph_db = self._construction_cache[archetype_uri]
        else:
            constr_from_graph_db = self._constr_reader.get_bldg_elem_construction_archetype(archetype_uri)
            self._construction_cache[archetype_uri] = constr_from_graph_db

        archetype = ArchetypicalConstructionGraphDBBased(
            window_glass_constr_options=constr_from_graph_db.windows,
            window_glass_constr_default=self._constr_reader.get_default_construction(constr_from_graph_db.windows, constr_from_graph_db.short_name),
            window_frame_construction=self._construction_basics.get_fixed_window_frame_construction(),
            window_shade_constr=self._constr_reader.get_window_shading_constr(archetype_uri),
            roof_constr_options=constr_from_graph_db.roofs,
            roof_constr_default=self._constr_reader.get_default_construction(constr_from_graph_db.roofs, constr_from_graph_db.short_name),
            groundfloor_constr_options=constr_from_graph_db.grounds,
            groundfloor_constr_default=self._constr_reader.get_default_construction(constr_from_graph_db.grounds, constr_from_graph_db.short_name),
            wall_constr_options=constr_from_graph_db.walls,
            wall_constr_default=self._constr_reader.get_default_construction(constr_from_graph_db.walls, constr_from_graph_db.short_name),
            internal_ceiling_options=constr_from_graph_db.internal_ceilings,
            internal_ceiling_default=self._constr_reader.get_default_construction(constr_from_graph_db.internal_ceilings, constr_from_graph_db.short_name),
            glazing_ratio=self._constr_reader.get_glazing_ratio(constr_from_graph_db.name),
            infiltration_rate=self._constr_reader.get_infiltration_rate(constr_from_graph_db.name),
            infiltration_fraction_profile_value=self._cfg["FIXED_INFILTRATION_PROFILE_VALUE"] * self._ureg.dimensionless,
            installations_characteristics=self._construction_basics.get_inst_characteristics(
                self._bldg_fid_to_dhw_ecarrier_lookup[bldg_fid],
                self._bldg_fid_to_heating_ecarrier_lookup[bldg_fid],
            ),
        )

        retr_archetype = self.create_modified_archetype_constructions(archetype, bldg_fid)

        return retr_archetype

    def create_modified_archetype_constructions(self, archetype: ArchetypicalConstructionGraphDBBased, bldg_fid: int):
        year_of_construction = self._bldg_fid_to_year_of_constr_lookup[bldg_fid]
        construction_age_class = self._year_to_ageclass_lookup(year_of_construction)
        infiltration_rate = archetype.infiltration_rate
        wall_constr_default = archetype.wall_constr._default
        roof_constr_default = archetype.roof_constr._default
        ground_constr_default = archetype.groundfloor_constr._default
        window_glass_constr_default = archetype.window_glass_constr._default
        walls = archetype.wall_constr._all_options
        roofs = archetype.roof_constr._all_options
        grounds = archetype.groundfloor_constr._all_options
        windows = archetype.window_glass_constr._all_options

        wall_ret_year = self._bldg_fid_to_year_of_retrofit_per_constr_lookup[bldg_fid]["year_of_wall_retrofit"]
        wall_ret_year_age_class_num = self._year_to_ageclass_lookup(wall_ret_year)
        if wall_ret_year_age_class_num > construction_age_class:
            new_wall_uri = archetype.wall_constr._default.name + "_R_" + str(wall_ret_year_age_class_num)
            wall_constr_default = Construction(name=new_wall_uri, layers=self._constr_reader.get_layers(new_wall_uri), bldg_element=BuildingElement.WALL)
            walls = [wall_constr_default]

        roof_ret_year = self._bldg_fid_to_year_of_retrofit_per_constr_lookup[bldg_fid]["year_of_roof_retrofit"]
        roof_ret_year_age_class_num = self._year_to_ageclass_lookup(roof_ret_year)
        if roof_ret_year_age_class_num > construction_age_class:
            new_roof_uri = archetype.roof_constr._default.name + "_R_" + str(roof_ret_year_age_class_num)
            roof_constr_default = Construction(name=new_roof_uri, layers=self._constr_reader.get_layers(new_roof_uri), bldg_element=BuildingElement.ROOF)
            roofs = [roof_constr_default]

        ground_ret_year = self._bldg_fid_to_year_of_retrofit_per_constr_lookup[bldg_fid]["year_of_groundfloor_retrofit"]
        ground_ret_year_age_class_num = self._year_to_ageclass_lookup(ground_ret_year)
        if ground_ret_year_age_class_num > construction_age_class:
            new_ground_uri = archetype.groundfloor_constr._default.name + "_R_" + str(ground_ret_year_age_class_num)
            ground_constr_default = Construction(name=new_ground_uri, layers=self._constr_reader.get_layers(new_ground_uri), bldg_element=BuildingElement.GROUNDFLOOR)
            grounds = [ground_constr_default]

        window_ret_year = self._bldg_fid_to_year_of_retrofit_per_constr_lookup[bldg_fid]["year_of_window_retrofit"]
        window_ret_year_age_class_num = self._year_to_ageclass_lookup(window_ret_year)
        if window_ret_year_age_class_num > construction_age_class:
            new_window_uri = self._cfg["ARCHETYPES"][str(window_ret_year_age_class_num) + "_SFH_ARCHETYPE"]["DEFAULT_CONSTRUCTION_SPECIFIC"]["WINDOW"]
            window_glass_constr_default = WindowGlassConstruction(name=new_window_uri, layers=self._constr_reader.get_window_layers(new_window_uri))
            infiltration_rate = self._constr_reader.get_infiltration_rate(self._get_archetype_uri_for(window_ret_year_age_class_num))
            windows = [window_glass_constr_default]

        retr_archetype = ArchetypicalConstructionGraphDBBased(
            window_glass_constr_options=windows,
            window_glass_constr_default=window_glass_constr_default,
            window_frame_construction=self._construction_basics.get_fixed_window_frame_construction(),
            window_shade_constr=self._constr_reader.get_window_shading_constr(self._get_archetype_uri_for(window_ret_year_age_class_num)),
            roof_constr_options=roofs,
            roof_constr_default=roof_constr_default,
            groundfloor_constr_options=grounds,
            groundfloor_constr_default=ground_constr_default,
            wall_constr_options=walls,
            wall_constr_default=wall_constr_default,
            internal_ceiling_options=archetype.internal_ceiling_constr._all_options,
            internal_ceiling_default=archetype.internal_ceiling_constr._default,
            glazing_ratio=archetype.glazing_ratio,
            infiltration_rate=infiltration_rate,
            infiltration_fraction_profile_value=self._cfg["FIXED_INFILTRATION_PROFILE_VALUE"] * self._ureg.dimensionless,
            installations_characteristics=self._construction_basics.get_inst_characteristics(
                self._bldg_fid_to_dhw_ecarrier_lookup[bldg_fid],
                self._bldg_fid_to_heating_ecarrier_lookup[bldg_fid],
            ),
        )

        return retr_archetype

    def _get_archetype_uri_for(self, year_of_construction) -> str:
        """
        :param year_of_construction: [description]
        :type year_of_construction: [type]
        :return: [description]
        :rtype: [type]
        :raises: Exception if no archetype for given year_of_construction was found
        """
        age_class = AgeClass.get_age_class_for(year_of_construction, self._ageclass_archetype.keys())
        return self._ageclass_archetype[age_class]

    def _year_to_ageclass_lookup(self, year) -> int:
        age_class = AgeClass.get_age_class_for(year, self._ageclass_archetype.keys())
        if age_class.max_age:
            return age_class.max_age
        elif age_class.min_age:
            return age_class.min_age
        else:
            raise Exception("AgeClass has no min or max value")
