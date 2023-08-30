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
import pint
import logging
import cesarp.common
from cesarp.construction.construction_protocols import ArchetypicalBuildingConstruction
from cesarp.construction.ConstructionBasics import ConstructionBasics
from cesarp.model.EnergySource import EnergySource

from cesarp.graphdb_access.BldgElementConstructionReader import BldgElementConstructionReader, GraphReaderProtocol, BuildingElementConstrcutionsArchetype
from cesarp.graphdb_access.ArchetypicalConstructionGraphDBBased import ArchetypicalConstructionGraphDBBased
from cesarp.graphdb_access import _default_config_file


class BuildingSpecificArchetypConstructionFactory:
    """
    This construction archetype factory assigns the construction archetype for each building based on a lookup
    where the building archetype is specified for each of the buildings individually.
    For the lookup the same file as specified for the building type lookup (in the config "MANAGER"-"BLDG_TYPE_PER_BLDG_FILE")
    and expecting a column named "ConstructionArchetype". The entries must be valid constructional archetypes either in the
    local TTL DB file or the remote GraphDB connected.

    The class must implement the protocol/interface specified in cesarp.construction.construction_protocols.ArchetypicalConstructionFactoryProtocol
    The __init__ must take same arguments as cesarp.graphdb_access.GraphDBArchetypicalConstructionFactory.GraphDBArchetypicalConstructionFactory.__init__ due to the fact that the
    factory is created from cesar-p-core code depending on config (namely in cesarp.graphdb_access.GraphDBFacade).
    """

    def __init__(
        self,
        bldg_fid_to_age_lookup: Dict[int, int],
        bldg_fid_to_dhw_ecarrier_lookup: Dict[int, EnergySource],
        bldg_fid_to_heating_ecarrier_lookup: Dict[int, EnergySource],
        graph_data_reader: GraphReaderProtocol,
        ureg: pint.UnitRegistry,
        custom_config: Dict[str, Any] = {},
    ):
        """
        :param bldg_fid_to_age_lookup: lookup of building age
        :type bldg_fid_to_age_lookup: Dict[int, int]
        :param bldg_fid_to_dhw_ecarrier_lookup: lookup of energy carrier
        :type bldg_fid_to_dhw_ecarrier_lookup: Dict[int, EnergySource]
        :param bldg_fid_to_heating_ecarrier_lookup: lookup for heating energy carriere
        :type bldg_fid_to_heating_ecarrier_lookup: Dict[int, EnergySource]
        :param graph_data_reader: access to graph database
        :type graph_data_reader: GraphReaderProtocol
        :param ureg: the application unit registry instance
        :type ureg: pint.UnitRegistry
        :param custom_config: any custom configuration parameters, defaults to {}
        :type custom_config: Dict[str, Any], optional
        """
        self._ureg = ureg
        self._custom_config = custom_config
        self._cfg = cesarp.common.config_loader.load_config_for_package(_default_config_file, "cesarp.graphdb_access", custom_config)
        self._bldg_fid_to_age_lookup = bldg_fid_to_age_lookup
        self._bldg_fid_to_dhw_ecarrier_lookup = bldg_fid_to_dhw_ecarrier_lookup
        self._bldg_fid_to_heating_ecarrier_lookup = bldg_fid_to_heating_ecarrier_lookup
        self._constr_reader = BldgElementConstructionReader(graph_data_reader, ureg, custom_config)
        self._construction_basics = ConstructionBasics(self._ureg, custom_config)
        self._archetypes_cache: Dict[str, ArchetypicalConstructionGraphDBBased] = dict()
        self._bldg_fid_to_archetype_lookup: Dict[int, str] = self._read_bldg_fid_to_archetype_lookup()
        self._construction_cache: Dict[str, BuildingElementConstrcutionsArchetype] = dict()  # key is archetype URI

    def _read_bldg_fid_to_archetype_lookup(self) -> Dict[int, str]:
        bldg_type_cfg = self._custom_config["MANAGER"]["BLDG_TYPE_PER_BLDG_FILE"]
        bldg_fid_to_archetype = cesarp.common.csv_reader.read_csvy(
            bldg_type_cfg["PATH"],
            ["gis_fid", "ConstructionArchetype"],
            {"gis_fid": "ORIG_FID", "ConstructionArchetype": "ConstructionArchetype"},
            bldg_type_cfg["SEPARATOR"],
            "gis_fid",
        )
        return bldg_fid_to_archetype["ConstructionArchetype"].to_dict()

    def get_archetype_for(self, bldg_fid: int) -> ArchetypicalBuildingConstruction:

        archetype_uri = self._bldg_fid_to_archetype_lookup[bldg_fid]

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

        logging.getLogger(__name__).info(f"assigned {archetype_uri} for building fid {bldg_fid}")
        print(f"assigned {archetype_uri} for building fid {bldg_fid}")
        return archetype
