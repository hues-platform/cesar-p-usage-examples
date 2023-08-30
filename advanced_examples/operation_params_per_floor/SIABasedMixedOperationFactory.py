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
import pint
from typing import Dict, Any
from enum import Enum
from cesarp.SIA2024.SIA2024BuildingType import SIA2024BldgTypeKeys
from cesarp.SIA2024.NullParametersFactory import NullParameterFactory
from cesarp.SIA2024.SIA2024ParamsManager import SIA2024ParamsManager
from cesarp.model.BuildingOperationMapping import BuildingOperationMapping
from cesarp.model.BuildingOperation import BuildingOperation, Occupancy, InstallationOperation, HVACOperation
from cesarp.operation.protocols import PassiveCoolingOperationFactoryProtocol


class SIABasedMixedOperationFactory:
    """
    This operation parameters factory does assign different operation profiles for different floors of the building.
    SHOP is used for all groundfloor's of the buildings and MFH for all other floors.
    The CESAR-P data model and IDF generation process supports assigning different operational profile for each floor, but
    The cesar-p-core package has no function to actually make use of that possibility, so you need to implement your own
    operation parameters factory as demonstrated here if you want to do so.

    The operational factory has to implement cesarp.manager.manager_protocols.BuildingOperationFactoryProtocol
    The __init__ method needs to have the same attributes as src.cesarp.operation.fixed.FixedBuildingOperationFactory.FixedBuildingOperationFactory.__init__
    The factory is instantiated in cesarp.manager.BldgModelFactory.BldgModelFactory.__create_bldg_operation_factory depending on config.
    """

    def __init__(self, passive_cooling_op_fact: PassiveCoolingOperationFactoryProtocol, ureg: pint.UnitRegistry, custom_config: Dict[str, Any] = {}):
        """
        :param passive_cooling_op_fact: instance of passive cooling operation factory, e.g. :py:class:`cesarp.operation.PassiveCoolingOperationFactory`
        :type passive_cooling_op_fact: PassiveCoolingOperationFactoryProtocol
        :param ureg: application unit registry instance
        :type ureg: pint.UnitRegistry
        :param custom_config: custom configuration entries, defaults to {}
        :type custom_config: Dict[str, Any], optional
        """
        # we use the pre-generated sia profiles included in cesar-p-core, thus no need to link create new parameter sets
        # (SIA data which would be needed for this is not included in cesar-p-core open source package)
        params_factory = NullParameterFactory()
        self.params_manager = SIA2024ParamsManager(params_factory, ureg, custom_config)
        self.params_manager.load_param_sets_nominal(list(SIA2024BldgTypeKeys))  # load profiles for all building types, path to load from is configurable, see cesarp.SIA2024 config
        self._passive_cooling_op_fact = passive_cooling_op_fact

    def get_building_operation(self, bldg_fid: int, nr_of_floors: int) -> BuildingOperationMapping:
        """
        Returns an instance of BuildingOperationMapping for the given building, which then can be attached to the BuildingModel instance of that building.
        For all buildings the operational parameters are set as:

        * 1st floor SHOP
        * all other floors MFH (residential multi familiy home)

        :param bldg_fid: building fid for which to create the object
        :type bldg_fid: int
        :param nr_of_floors: nr of floors the building has
        :type nr_of_floors: int
        :return: initialized building operation mapping object for given building
        :rtype: BuildingOperationMapping
        """
        bldg_op_mfh = self.__init_bldg_op(bldg_fid, SIA2024BldgTypeKeys.MFH)
        bldg_op_shop = self.__init_bldg_op(bldg_fid, SIA2024BldgTypeKeys.SHOP)
        bldg_op_mapping = BuildingOperationMapping()
        bldg_op_mapping.add_operation_assignment([0], bldg_op_shop)
        if nr_of_floors > 1:
            bldg_op_mapping.add_operation_assignment(range(1, nr_of_floors), bldg_op_mfh)
        return bldg_op_mapping

    def __init_bldg_op(self, bldg_fid: int, bldg_type: Enum):
        params = self.params_manager.get_param_set(bldg_type)
        return BuildingOperation(
            params.name,
            Occupancy(params.floor_area_per_person, params.occupancy_fraction_schedule, params.activity_schedule),
            InstallationOperation(params.electric_appliances_fraction_schedule, params.electric_appliances_power_demand),
            InstallationOperation(params.lighting_fraction_schedule, params.lighting_power_demand),
            InstallationOperation(params.dhw_fraction_schedule, params.dhw_power_demand),
            HVACOperation(params.heating_setpoint_schedule, params.cooling_setpoint_schedule, params.ventilation_fraction_schedule, params.ventilation_outdoor_air_flow),
            self._passive_cooling_op_fact.create_night_vent(bldg_fid, params.cooling_setpoint_schedule),
            self._passive_cooling_op_fact.create_win_shading_ctrl(bldg_fid),
        )
