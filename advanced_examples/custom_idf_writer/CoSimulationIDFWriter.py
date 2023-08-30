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
import logging
import pint
import os
import shutil
import copy
import cesarp.common.ScheduleTypeLimits
from typing import TypeVar, Mapping, Optional, Union, Tuple, Dict, List, Any
from eppy.modeleditor import IDF
from eppy.bunch_subclass import EpBunch
from six import StringIO

from cesarp.common.ScheduleFile import ScheduleFile
from cesarp.common.ScheduleFixedValue import ScheduleFixedValue
from cesarp.common import config_loader
from cesarp.eplus_adapter import _default_config_file
from cesarp.eplus_adapter import idf_writer_geometry
from cesarp.eplus_adapter import idf_strings
from cesarp.eplus_adapter import idf_writer_operation
from cesarp.eplus_adapter import idf_writing_helpers
from cesarp.eplus_adapter.eplus_sim_runner import get_eplus_version, get_idd_path
from cesarp.model.BldgShape import BldgShapeEnvelope, BldgShapeDetailed
from cesarp.model.BuildingModel import BuildingModel
from cesarp.model.BuildingConstruction import BuildingConstruction, InstallationsCharacteristics
from cesarp.model.WindowConstruction import WindowShadingMaterial
from cesarp.model.BuildingOperationMapping import BuildingOperationMapping
from cesarp.model.SiteGroundTemperatures import SiteGroundTemperatures
from cesarp.eplus_adapter.ConstructionIDFWritingHandler import ConstructionIDFWritingHandler
from cesarp.eplus_adapter.CesarIDFWriter import CesarIDFWriter
from cesarp.model.BuildingOperation import BuildingOperation, HVACOperation
from cesarp.eplus_adapter.ConstructionIDFWritingHandler import FLORR_CONSTR_SUFFIX

ConstrType = TypeVar("ConstrType")


def no_constr_writer(constr, idf: IDF):
    return idf


def no_idf_constr_files(constr):
    return []


class CoSimulationIDFWriter:
    """
    Handels the IDF Writing process

    For each building, you create a new instance of CesarIDFWriter and call write_bldg_model() to create a full IDF file.

    """

    def __init__(self, idf_file_path, unit_registry, profiles_files_handler=None, custom_config={}, package_config: Dict[str, Any] = None):
        """
        You can only use one construction type at a time. All three constr_xxx callables take a construction object as the first argument.
        Either constr_writer or constr_get_idf_files should point to a method of your construction, you can also assign both method if you wish.

        :param constr_name_lookup: function which returns the name for a given construction object
        :param constr_writer: function which writes the passed construction object to the idf file passed as a second parameter
        :param constr_get_idf_files: function which returns partial idf files for that construction which shall be appended at the end of IDF-Writing process. files are collected
               and before writing duplicated files are removed. this allows that you return the same file several
               times and it will only be appended once, but means that you have to make sure files with different content have different file names.
        :param idf_file_path: file name including full path to write IDF to. file should not exist.
        :param geometry_writer: instance of class to write geometry properties from the model to the IDF
        :param custom_config: dictionary containing configuration entries overwriting package default config
        :param package_config: allow that the package configuration is passed as dict, to avoid that we need to load the config from file in the IDFWriterFactory and here..., Optional, if not provided config is loaded as normal from default config file and custom_config dict.
        """
        self.basewriter = CesarIDFWriter(idf_file_path, unit_registry, profiles_files_handler, custom_config, package_config)

    def write_bldg_model(self, bldg_model: BuildingModel) -> None:
        """
        :param bldg_model: Building model to write to IDF
        :type bldg_model: BuildingModel
        """
        idf = IDF(str(self.basewriter.idf_file_path))
        self.basewriter.add_basic_simulation_settings(idf, bldg_model.site.site_ground_temperatures)
        self.add_cosimulation_control_settings(idf)
        constr_handler = ConstructionIDFWritingHandler(bldg_model.bldg_construction, bldg_model.neighbours_construction_props, self.basewriter.unit_registry)
        constr_and_mat_idfs = self.basewriter.add_building_geometry(idf, bldg_model.bldg_shape, constr_handler)
        self.add_plant_sizing_settings(idf)
        self.add_plnt_size(idf)
        self.add_plnt_loop(idf)
        self.add_sch_compact(idf)
        self.basewriter.add_neighbours(idf, bldg_model.neighbours, constr_handler)
        self.add_cosim_building_properties(
            idf,
            bldg_model.bldg_operation_mapping,
            bldg_model.bldg_construction.installation_characteristics,
            bldg_model.bldg_construction.infiltration_rate,
            self.basewriter._handle_profile_file(bldg_model.bldg_construction.infiltration_profile),
            bldg_model.bldg_construction.window_constr.shade,
        )
        idf = self.add_floor_heating(idf, bldg_model.bldg_construction)
        idf = self.basewriter.add_output_settings(idf)
        idf.save(filename=str(self.basewriter.idf_file_path))
        # self.basewriter.__append_files(constr_and_mat_idfs)

    def add_cosimulation_control_settings(self, idf) -> IDF:
        """
        adds to the idf simulation control settings needed to run the simulation in the way we want

        :return: idf object
        """
        simulationCtrl = idf.newidfobject(idf_strings.IDFObjects.simulation_control)
        simulationCtrl.Run_Simulation_for_Sizing_Periods = idf_strings.no
        simulationCtrl.Do_Zone_Sizing_Calculation = idf_strings.yes
        simulationCtrl.Do_System_Sizing_Calculation = idf_strings.yes
        simulationCtrl.Do_Plant_Sizing_Calculation = idf_strings.yes

        return idf

    def add_plant_sizing_settings(self, idf):
        plant_sizing = idf.newidfobject("SizingPeriod:DesignDay".upper())
        plant_sizing.Name = "Summer Design Day Jul"
        plant_sizing.Month = 7
        plant_sizing.Day_of_Month = 15
        plant_sizing.Day_Type = "SummerDesignDay"
        plant_sizing.Maximum_DryBulb_Temperature = 28.8
        plant_sizing.Daily_DryBulb_Temperature_Range = 8.7
        plant_sizing.DryBulb_Temperature_Range_Modifier_Type = ""
        plant_sizing.Wetbulb_or_DewPoint_at_Maximum_DryBulb = 19.7
        plant_sizing.Barometric_Pressure = 96056.4
        plant_sizing.Wind_Speed = 0
        plant_sizing.Wind_Direction = 0
        plant_sizing.Daylight_Saving_Time_Indicator = "Yes"
        plant_sizing.Solar_Model_Indicator = "ASHRAEClearSky"
        plant_sizing.Sky_Clearness = 0.98

        plant_sizing = idf.newidfobject("SizingPeriod:DesignDay".upper())
        plant_sizing.Name = "Winter Design Day Dec"
        plant_sizing.Month = 1
        plant_sizing.Day_of_Month = 15
        plant_sizing.Day_Type = "WinterDesignDay"
        plant_sizing.Maximum_DryBulb_Temperature = -8.4
        plant_sizing.Daily_DryBulb_Temperature_Range = 0
        plant_sizing.DryBulb_Temperature_Range_Modifier_Type = ""
        plant_sizing.Wetbulb_or_DewPoint_at_Maximum_DryBulb = -8.4
        plant_sizing.Barometric_Pressure = 96056.4
        plant_sizing.Wind_Speed = 12.1
        plant_sizing.Wind_Direction = 0

        return idf
    def add_cosim_building_properties(
        self,
        idf,
        building_operation_mapping: BuildingOperationMapping,
        installation_characteristics: InstallationsCharacteristics,
        infiltrationRate: pint.Quantity,
        infiltrationProfile: Union[ScheduleFile, ScheduleFixedValue],
        window_shading_material: WindowShadingMaterial,
    ) -> IDF:
        """
        Adding internal conditions according to the passed definition to each zone of the building.

        :param building_operation: model object holding all operational parameters
        :param installation_characteristics: model object holding all installation specific characteristics, e.g. the efficiency of lighting
        :return: nothing, changes are saved to the idf
        """
        assert (
            self.basewriter.zone_data is not None
        ), "make sure that prior to calling add_buidlding_properties attribute zone_data is initialized, e.g. by calling add_buidling_geometry"
        assert (
            list(self.basewriter.zone_data.keys()) == building_operation_mapping.all_assigned_floor_nrs  # type: ignore  # checked self.basewriter.zone_data for none in assert on line 288
        ), f"zones/floors {list(self.basewriter.zone_data.keys())} in geometry do not match with the floors in the building operation mapping ({building_operation_mapping.all_assigned_floor_nrs})"  # type: ignore  # checked self.basewriter.zone_data for none in assert on line 288

        for (floor_nrs, bldg_op) in building_operation_mapping.get_operation_assignments():
            bldg_op_local_profiles = copy.deepcopy(bldg_op)
            bldg_op_local_profiles.electric_appliances.fraction_schedule = self.basewriter._handle_profile_file(bldg_op_local_profiles.electric_appliances.fraction_schedule)
            bldg_op_local_profiles.lighting.fraction_schedule = self.basewriter._handle_profile_file(bldg_op_local_profiles.lighting.fraction_schedule)
            bldg_op_local_profiles.occupancy.occupancy_fraction_schedule = self.basewriter._handle_profile_file(bldg_op_local_profiles.occupancy.occupancy_fraction_schedule)
            bldg_op_local_profiles.dhw.fraction_schedule = self.basewriter._handle_profile_file(bldg_op_local_profiles.dhw.fraction_schedule)
            bldg_op_local_profiles.hvac.ventilation_fraction_schedule = self.basewriter._handle_profile_file(bldg_op_local_profiles.hvac.ventilation_fraction_schedule)
            bldg_op_local_profiles.hvac.cooling_setpoint_schedule = self.basewriter._handle_profile_file(bldg_op_local_profiles.hvac.cooling_setpoint_schedule)
            bldg_op_local_profiles.hvac.heating_setpoint_schedule = self.basewriter._handle_profile_file(bldg_op_local_profiles.hvac.heating_setpoint_schedule)
            bldg_op_local_profiles.occupancy.activity_schedule = self.basewriter._handle_profile_file(bldg_op_local_profiles.occupancy.activity_schedule)

            if bldg_op_local_profiles.night_vent.is_active:
                bldg_op_local_profiles.night_vent.maximum_indoor_temp_profile = self.basewriter._handle_profile_file(bldg_op_local_profiles.night_vent.maximum_indoor_temp_profile)
            for floor_nr, (zone_name, windows_in_zone) in self.basewriter.zone_data.items():  # type: ignore  # checked self.basewriter.zone_data for none in assert on line 288
                if floor_nr in floor_nrs:
                    self.add_building_operation(idf, zone_name, bldg_op_local_profiles, installation_characteristics, self.basewriter.unit_registry)
                    idf_writer_operation.add_zone_infiltration(idf, zone_name, infiltrationRate, infiltrationProfile, self.basewriter.unit_registry)
                    idf_writer_operation.add_passive_cooling(idf, zone_name, windows_in_zone, bldg_op_local_profiles, window_shading_material)

        return idf

    def add_floor_heating(self, idf, building_construction: BuildingConstruction):  # only works with graph DB , does not work with snippet idf
        bldg_ground_floor = building_construction.groundfloor_constr.name
        bldg_intenal_floor = f"{building_construction.internal_ceiling_constr.name}{FLORR_CONSTR_SUFFIX}"

        grnd_floor_ht = idf.newidfobject("ConstructionProperty:InternalHeatSource".upper())
        grnd_floor_ht.Name = "groundfloor_with_heat_source"
        grnd_floor_ht.Construction_Name = bldg_ground_floor
        grnd_floor_ht.Thermal_Source_Present_After_Layer_Number = 5
        grnd_floor_ht.Temperature_Calculation_Requested_After_Layer_Number = 5
        grnd_floor_ht.Dimensions_for_the_CTF_Calculation = 1
        grnd_floor_ht.Tube_Spacing = 0.3

        int_floor_ht = idf.newidfobject("ConstructionProperty:InternalHeatSource".upper())
        int_floor_ht.Name = "floor_with_heat_source"
        int_floor_ht.Construction_Name = bldg_intenal_floor
        int_floor_ht.Thermal_Source_Present_After_Layer_Number = 1
        int_floor_ht.Temperature_Calculation_Requested_After_Layer_Number = 1
        int_floor_ht.Dimensions_for_the_CTF_Calculation = 1
        int_floor_ht.Tube_Spacing = 0.3

        return idf

    def add_plnt_size(self, idf):
        plnt_size_obj = idf.newidfobject("Sizing:Plant".upper())
        plnt_size_obj.Plant_or_Condenser_Loop_Name = "HW-plnt"
        plnt_size_obj.Loop_Type = "Heating"
        plnt_size_obj.Design_Loop_Exit_Temperature = 35
        plnt_size_obj.Loop_Design_Temperature_Difference = 10

        return idf

    def add_plnt_loop(self, idf):
        plnt_loop_obj = idf.newidfobject("PlantLoop".upper())
        plnt_loop_obj.Name = "HW-plnt"
        plnt_loop_obj.Plant_Equipment_Operation_Scheme_Name = "HW-plnt Operation"
        plnt_loop_obj.Loop_Temperature_Setpoint_Node_Name = "HW-plnt Supply Side Outlet"
        plnt_loop_obj.Maximum_Loop_Temperature = 35
        plnt_loop_obj.Minimum_Loop_Temperature = 25
        plnt_loop_obj.Maximum_Loop_Flow_Rate = "autosize"
        plnt_loop_obj.Plant_Side_Inlet_Node_Name = "HW-plnt Supply Side Inlet"
        plnt_loop_obj.Plant_Side_Outlet_Node_Name = "HW-plnt Supply Side Outlet"
        plnt_loop_obj.Plant_Side_Branch_List_Name = "HW-plnt Supply Side Branches"
        plnt_loop_obj.Plant_Side_Connector_List_Name = "HW-plnt Supply Side Connectors"
        plnt_loop_obj.Demand_Side_Inlet_Node_Name = "HW-plnt Demand Side Inlet"
        plnt_loop_obj.Demand_Side_Outlet_Node_Name = "HW-plnt Demand Side Outlet"
        plnt_loop_obj.Demand_Side_Branch_List_Name = "HW-plnt Demand Side Branches"
        plnt_loop_obj.Demand_Side_Connector_List_Name = "HW-plnt Demand Side Connectors"
        plnt_loop_obj.Availability_Manager_List_Name = "HW-plnt AvailabilityManager List"

        plnt_loop_obj = idf.newidfobject("PlantEquipmentOperationSchemes".upper())
        plnt_loop_obj.Name = "HW-plnt Operation"
        plnt_loop_obj.Control_Scheme_1_Object_Type = "PlantEquipmentOperation:HeatingLoad"
        plnt_loop_obj.Control_Scheme_1_Name = "HW-plnt Scheme 1"
        plnt_loop_obj.Control_Scheme_1_Schedule_Name = "Plnt_ctrl_scheme"

        plnt_loop_obj = idf.newidfobject("NodeList".upper())
        plnt_loop_obj.Name = "HW-plnt Setpoint Manager Node List"
        plnt_loop_obj.Node_1_Name = "HW-plnt Supply Side Outlet"

        plnt_loop_obj = idf.newidfobject("SetpointManager:Scheduled".upper())
        plnt_loop_obj.Name = "HW-plnt Setpoint Manager"
        plnt_loop_obj.Control_Variable = "Temperature"
        plnt_loop_obj.Schedule_Name = "HW_plnt_setpoint"
        plnt_loop_obj.Setpoint_Node_or_NodeList_Name = "HW-plnt Setpoint Manager Node List"

        plnt_loop_obj = idf.newidfobject("PlantEquipmentOperation:HeatingLoad".upper())
        plnt_loop_obj.Name = "HW-plnt Scheme 1"
        plnt_loop_obj.Load_Range_1_Lower_Limit = 0
        plnt_loop_obj.Load_Range_1_Upper_Limit = 1000000000000000
        plnt_loop_obj.Range_1_Equipment_List_Name = "HW-plnt Scheme 1 Range 1 Equipment List"

        plnt_loop_obj = idf.newidfobject("PlantEquipmentList".upper())
        plnt_loop_obj.Name = "HW-plnt Scheme 1 Range 1 Equipment List"
        plnt_loop_obj.Equipment_1_Object_Type = "DistrictHeating"
        plnt_loop_obj.Equipment_1_Name = "District Heating"

        plnt_loop_obj = idf.newidfobject("AvailabilityManagerAssignmentList".upper())
        plnt_loop_obj.Name = "HW-plnt AvailabilityManager List"
        plnt_loop_obj.Availability_Manager_1_Object_Type = "AvailabilityManager:Scheduled"
        plnt_loop_obj.Availability_Manager_1_Name = "HW-plnt Availability"

        plnt_loop_obj = idf.newidfobject("AvailabilityManager:Scheduled".upper())
        plnt_loop_obj.Name = "HW-plnt Availability"
        plnt_loop_obj.Schedule_Name = "ON_24_7"

        plnt_loop_obj = idf.newidfobject("BranchList".upper())
        plnt_loop_obj.Name = "HW-plnt Demand Side Branches"
        plnt_loop_obj.Branch_1_Name = "HW-plnt Demand Side Inlet Branch"
        plnt_loop_obj.Branch_2_Name = "HW-plnt Demand Side Bypass Branch"
        for floor_nr, (zone_name, x) in self.basewriter.zone_data.items():
            branch_name = f"{zone_name}{' Radiant surface HW-plnt Demand Side Branch'}"
            attr_name = f"{'Branch_'}{floor_nr+3}{'_Name'}"
            setattr(plnt_loop_obj, attr_name, branch_name)
        branch_name = "HW-plnt Demand Side Outlet Branch"
        attr_name = f"{'Branch_'}{len(self.basewriter.zone_data)+3}{'_Name'}"
        setattr(plnt_loop_obj, attr_name, branch_name)

        plnt_loop_obj = idf.newidfobject("Branch".upper())
        plnt_loop_obj.Name = "HW-plnt Demand Side Inlet Branch"
        plnt_loop_obj.Component_1_Object_Type = "Pipe:Adiabatic"
        plnt_loop_obj.Component_1_Name = "HW-plnt Demand Side Inlet Branch Pipe"
        plnt_loop_obj.Component_1_Inlet_Node_Name = "HW-plnt Demand Side Inlet"
        plnt_loop_obj.Component_1_Outlet_Node_Name = "HW-plnt Demand Side Inlet Branch Pipe Outlet"

        plnt_loop_obj = idf.newidfobject("Pipe:Adiabatic".upper())
        plnt_loop_obj.Name = "HW-plnt Demand Side Inlet Branch Pipe"
        plnt_loop_obj.Inlet_Node_Name = "HW-plnt Demand Side Inlet"
        plnt_loop_obj.Outlet_Node_Name = "HW-plnt Demand Side Inlet Branch Pipe Outlet"

        plnt_loop_obj = idf.newidfobject("Branch".upper())
        plnt_loop_obj.Name = "HW-plnt Demand Side Bypass Branch"
        plnt_loop_obj.Component_1_Object_Type = "Pipe:Adiabatic"
        plnt_loop_obj.Component_1_Name = "HW-plnt Demand Side Bypass Pipe"
        plnt_loop_obj.Component_1_Inlet_Node_Name = "HW-plnt Demand Side Bypass Pipe Inlet Node"
        plnt_loop_obj.Component_1_Outlet_Node_Name = "HW-plnt Demand Side Bypass Pipe Outlet Node"

        plnt_loop_obj = idf.newidfobject("Pipe:Adiabatic".upper())
        plnt_loop_obj.Name = "HW-plnt Demand Side Bypass Pipe"
        plnt_loop_obj.Inlet_Node_Name = "HW-plnt Demand Side Bypass Pipe Inlet Node"
        plnt_loop_obj.Outlet_Node_Name = "HW-plnt Demand Side Bypass Pipe Outlet Node"

        plnt_loop_obj = idf.newidfobject("Branch".upper())
        plnt_loop_obj.Name = "HW-plnt Demand Side Outlet Branch"
        plnt_loop_obj.Component_1_Object_Type = "Pipe:Adiabatic"
        plnt_loop_obj.Component_1_Name = "HW-plnt Demand Side Outlet Branch Pipe"
        plnt_loop_obj.Component_1_Inlet_Node_Name = "HW-plnt Demand Side Outlet Branch Pipe Inlet"
        plnt_loop_obj.Component_1_Outlet_Node_Name = "HW-plnt Demand Side Outlet"

        plnt_loop_obj = idf.newidfobject("Pipe:Adiabatic".upper())
        plnt_loop_obj.Name = "HW-plnt Demand Side Outlet Branch Pipe"
        plnt_loop_obj.Inlet_Node_Name = "HW-plnt Demand Side Outlet Branch Pipe Inlet"
        plnt_loop_obj.Outlet_Node_Name = "HW-plnt Demand Side Outlet"

        plnt_loop_obj = idf.newidfobject("ConnectorList".upper())
        plnt_loop_obj.Name = "HW-plnt Demand Side Connectors"
        plnt_loop_obj.Connector_1_Object_Type = "Connector:Splitter"
        plnt_loop_obj.Connector_1_Name = "HW-plnt Demand Splitter"
        plnt_loop_obj.Connector_2_Object_Type = "Connector:Mixer"
        plnt_loop_obj.Connector_2_Name = "HW-plnt Demand Mixer"

        plnt_loop_obj = idf.newidfobject("Connector:Splitter".upper())
        plnt_loop_obj.Name = "HW-plnt Demand Splitter"
        plnt_loop_obj.Inlet_Branch_Name = "HW-plnt Demand Side Inlet Branch"
        plnt_loop_obj.Outlet_Branch_1_Name = "HW-plnt Demand Side Bypass Branch"
        for floor_nr, (zone_name, x) in self.basewriter.zone_data.items():
            branch_name = f"{zone_name}{' Radiant surface HW-plnt Demand Side Branch'}"
            attr_name = f"{'Outlet_Branch_'}{floor_nr+2}{'_Name'}"
            setattr(plnt_loop_obj, attr_name, branch_name)

        plnt_loop_obj = idf.newidfobject("Connector:Mixer".upper())
        plnt_loop_obj.Name = "HW-plnt Demand Mixer"
        plnt_loop_obj.Outlet_Branch_Name = "HW-plnt Demand Side Outlet Branch"
        for floor_nr, (zone_name, x) in self.basewriter.zone_data.items():
            branch_name = f"{zone_name}{' Radiant surface HW-plnt Demand Side Branch'}"
            attr_name = f"{'Inlet_Branch_'}{floor_nr+1}{'_Name'}"
            setattr(plnt_loop_obj, attr_name, branch_name)
        branch_name = "HW-plnt Demand Side Bypass Branch"
        attr_name = f"{'Inlet_Branch_'}{len(self.basewriter.zone_data)+1}{'_Name'}"
        setattr(plnt_loop_obj, attr_name, branch_name)

        plnt_loop_obj = idf.newidfobject("BranchList".upper())
        plnt_loop_obj.Name = "HW-plnt Supply Side Branches"
        plnt_loop_obj.Branch_1_Name = "HW-plnt Supply Side Inlet Branch"
        plnt_loop_obj.Branch_2_Name = "HW-plnt Supply Side Bypass Branch"
        plnt_loop_obj.Branch_3_Name = "District Heating HW-plnt Supply Side Branch"
        plnt_loop_obj.Branch_4_Name = "HW-plnt Supply Side Outlet Branch"

        plnt_loop_obj = idf.newidfobject("Branch".upper())
        plnt_loop_obj.Name = "HW-plnt Supply Side Inlet Branch"
        plnt_loop_obj.Component_1_Object_Type = "Pump:VariableSpeed"
        plnt_loop_obj.Component_1_Name = "HW-plnt Supply Pump"
        plnt_loop_obj.Component_1_Inlet_Node_Name = "HW-plnt Supply Side Inlet"
        plnt_loop_obj.Component_1_Outlet_Node_Name = "HW-plnt Supply Pump Water Outlet Node"

        plnt_loop_obj = idf.newidfobject("Pump:VariableSpeed".upper())
        plnt_loop_obj.Name = "HW-plnt Supply Pump"
        plnt_loop_obj.Inlet_Node_Name = "HW-plnt Supply Side Inlet"
        plnt_loop_obj.Outlet_Node_Name = "HW-plnt Supply Pump Water Outlet Node"
        plnt_loop_obj.Design_Maximum_Flow_Rate = "autosize"
        plnt_loop_obj.Design_Pump_Head = 20000
        plnt_loop_obj.Design_Power_Consumption = "autosize"
        plnt_loop_obj.Design_Minimum_Flow_Rate = 0
        plnt_loop_obj.Pump_Control_Type = "Intermittent"

        plnt_loop_obj = idf.newidfobject("Branch".upper())
        plnt_loop_obj.Name = "HW-plnt Supply Side Bypass Branch"
        plnt_loop_obj.Component_1_Object_Type = "Pipe:Adiabatic"
        plnt_loop_obj.Component_1_Name = "HW-plnt Supply Side Bypass Pipe"
        plnt_loop_obj.Component_1_Inlet_Node_Name = "HW-plnt Supply Side Bypass Pipe Inlet Node"
        plnt_loop_obj.Component_1_Outlet_Node_Name = "HW-plnt Supply Side Bypass Pipe Outlet Node"

        plnt_loop_obj = idf.newidfobject("Pipe:Adiabatic".upper())
        plnt_loop_obj.Name = "HW-plnt Supply Side Bypass Pipe"
        plnt_loop_obj.Inlet_Node_Name = "HW-plnt Supply Side Bypass Pipe Inlet Node"
        plnt_loop_obj.Outlet_Node_Name = "HW-plnt Supply Side Bypass Pipe Outlet Node"

        plnt_loop_obj = idf.newidfobject("Branch".upper())
        plnt_loop_obj.Name = "District Heating HW-plnt Supply Side Branch"
        plnt_loop_obj.Component_1_Object_Type = "DistrictHeating"
        plnt_loop_obj.Component_1_Name = "District Heating"
        plnt_loop_obj.Component_1_Inlet_Node_Name = "District Heating Water Inlet Node"
        plnt_loop_obj.Component_1_Outlet_Node_Name = "District Heating Water Outlet Node"

        plnt_loop_obj = idf.newidfobject("DistrictHeating".upper())
        plnt_loop_obj.Name = "District Heating"
        plnt_loop_obj.Hot_Water_Inlet_Node_Name = "District Heating Water Inlet Node"
        plnt_loop_obj.Hot_Water_Outlet_Node_Name = "District Heating Water Outlet Node"
        plnt_loop_obj.Nominal_Capacity = "Autosize"
        plnt_loop_obj.Capacity_Fraction_Schedule_Name = "Plnt_ctrl_scheme"

        plnt_loop_obj = idf.newidfobject("Branch".upper())
        plnt_loop_obj.Name = "HW-plnt Supply Side Outlet Branch"
        plnt_loop_obj.Component_1_Object_Type = "Pipe:Adiabatic"
        plnt_loop_obj.Component_1_Name = "HW-plnt Supply Side Outlet Branch Pipe"
        plnt_loop_obj.Component_1_Inlet_Node_Name = "HW-plnt Supply Side Outlet Branch Pipe Inlet"
        plnt_loop_obj.Component_1_Outlet_Node_Name = "HW-plnt Supply Side Outlet"

        plnt_loop_obj = idf.newidfobject("Pipe:Adiabatic".upper())
        plnt_loop_obj.Name = "HW-plnt Supply Side Outlet Branch Pipe"
        plnt_loop_obj.Inlet_Node_Name = "HW-plnt Supply Side Outlet Branch Pipe Inlet"
        plnt_loop_obj.Outlet_Node_Name = "HW-plnt Supply Side Outlet"

        plnt_loop_obj = idf.newidfobject("ConnectorList".upper())
        plnt_loop_obj.Name = "HW-plnt Supply Side Connectors"
        plnt_loop_obj.Connector_1_Object_Type = "Connector:Splitter"
        plnt_loop_obj.Connector_1_Name = "HW-plnt Supply Splitter"
        plnt_loop_obj.Connector_2_Object_Type = "Connector:Mixer"
        plnt_loop_obj.Connector_2_Name = "HW-plnt Supply Mixer"

        plnt_loop_obj = idf.newidfobject("Connector:Splitter".upper())
        plnt_loop_obj.Name = "HW-plnt Supply Splitter"
        plnt_loop_obj.Inlet_Branch_Name = "HW-plnt Supply Side Inlet Branch"
        plnt_loop_obj.Outlet_Branch_1_Name = "HW-plnt Supply Side Bypass Branch"
        plnt_loop_obj.Outlet_Branch_2_Name = "District Heating HW-plnt Supply Side Branch"

        plnt_loop_obj = idf.newidfobject("Connector:Mixer".upper())
        plnt_loop_obj.Name = "HW-plnt Supply Mixer"
        plnt_loop_obj.Outlet_Branch_Name = "HW-plnt Supply Side Outlet Branch"
        plnt_loop_obj.Inlet_Branch_1_Name = "District Heating HW-plnt Supply Side Branch"
        plnt_loop_obj.Inlet_Branch_2_Name = "HW-plnt Supply Side Bypass Branch"

        plnt_loop_obj = idf.newidfobject("HVACTEMPLATE:THERMOSTAT".upper())
        plnt_loop_obj.Name = "MFH_NOMINAL_Residential_thermostat"
        plnt_loop_obj.Heating_Setpoint_Schedule_Name = "MFH_NOMINAL_heating_setpoint_schedule"
        plnt_loop_obj.Constant_Heating_Setpoint = ""
        plnt_loop_obj.Cooling_Setpoint_Schedule_Name = "MFH_NOMINAL_cooling_setpoint_schedule"
        plnt_loop_obj.Constant_Cooling_Setpoint = ""

        plnt_loop_obj = idf.newidfobject("DESIGNSPECIFICATION:OUTDOORAIR".upper())
        plnt_loop_obj.Name = "MFH_NOMINAL_Residential_outdoorair"
        plnt_loop_obj.Outdoor_Air_Method = "Flow/Area"
        plnt_loop_obj.Outdoor_Air_Flow_per_Person = 0
        plnt_loop_obj.Outdoor_Air_Flow_per_Zone_Floor_Area = 3.055556e-04
        plnt_loop_obj.Outdoor_Air_Flow_per_Zone = 0
        plnt_loop_obj.Outdoor_Air_Flow_Air_Changes_per_Hour = 0
        plnt_loop_obj.Outdoor_Air_Schedule_Name = "MFH_NOMINAL_ventilation_fraction_schedule"

        plnt_loop_obj = idf.newidfobject("DesignSpecification:ZoneAirDistribution".upper())
        plnt_loop_obj.Name = "MFH_NOMINAL_Residential_zone_outdoorair"
        plnt_loop_obj.Zone_Air_Distribution_Effectiveness_in_Cooling_Mode = 1
        plnt_loop_obj.Zone_Air_Distribution_Effectiveness_in_Heating_Mode = 1
        plnt_loop_obj.Zone_Air_Distribution_Effectiveness_Schedule_Name = ""
        plnt_loop_obj.Zone_Secondary_Recirculation_Fraction = 0

        for floor_nr, (zone_name, x) in self.basewriter.zone_data.items():
            plnt_loop_obj = idf.newidfobject("Branch".upper())
            plnt_loop_obj.Name = f"{zone_name}{' Radiant surface HW-plnt Demand Side Branch'}"
            plnt_loop_obj.Component_1_Object_Type = "ZoneHVAC:LowTemperatureRadiant:VariableFlow"
            plnt_loop_obj.Component_1_Name = f"{zone_name}{' Radiant surface'}"
            plnt_loop_obj.Component_1_Inlet_Node_Name = f"{zone_name}{' Radiant surface Hot Water Inlet Node'}"
            plnt_loop_obj.Component_1_Outlet_Node_Name = f"{zone_name}{' Radiant surface Hot Water Outlet Node'}"

            plnt_loop_obj = idf.newidfobject("ZoneControl:Thermostat".upper())
            plnt_loop_obj.Name = f"{zone_name}{' Thermostat'}"
            plnt_loop_obj.Zone_or_ZoneList_Name = f"{zone_name}"
            plnt_loop_obj.Control_Type_Schedule_Name = "Dual_setpoint_schedule_type"
            plnt_loop_obj.Control_1_Object_Type = "ThermostatSetpoint:DualSetpoint"
            plnt_loop_obj.Control_1_Name = f"{zone_name}{' Dual SP'}"

            plnt_loop_obj = idf.newidfobject("ThermostatSetpoint:DualSetpoint".upper())
            plnt_loop_obj.Name = f"{zone_name}{' Dual SP'}"
            plnt_loop_obj.Heating_Setpoint_Temperature_Schedule_Name = "MFH_NOMINAL_heating_setpoint_schedule"
            plnt_loop_obj.Cooling_Setpoint_Temperature_Schedule_Name = "MFH_NOMINAL_cooling_setpoint_schedule"

            plnt_loop_obj = idf.newidfobject("ZoneHVAC:LowTemperatureRadiant:VariableFlow:Design".upper())
            plnt_loop_obj.Name = f"{zone_name}{' Radiant surface Design Object'}"
            plnt_loop_obj.Setpoint_Control_Type = "ZeroFlowPower"
            plnt_loop_obj.Heating_Control_Temperature_Schedule_Name = "MFH_NOMINAL_heating_setpoint_schedule"
            plnt_loop_obj.Condensation_Control_Type = "Off"

            plnt_loop_obj = idf.newidfobject("ZoneHVAC:LowTemperatureRadiant:VariableFlow".upper())
            plnt_loop_obj.Name = f"{zone_name}{' Radiant surface'}"
            plnt_loop_obj.Design_Object = f"{zone_name}{' Radiant surface Design Object'}"
            plnt_loop_obj.Availability_Schedule_Name = "Plnt_ctrl_scheme"
            plnt_loop_obj.Zone_Name = f"{zone_name}"
            plnt_loop_obj.Surface_Name_or_Radiant_Surface_Group_Name = f"{zone_name}{' Radiant surface list'}"
            plnt_loop_obj.Maximum_Hot_Water_Flow = "autosize"
            plnt_loop_obj.Heating_Water_Inlet_Node_Name = f"{zone_name}{' Radiant surface Hot Water Inlet Node'}"
            plnt_loop_obj.Heating_Water_Outlet_Node_Name = f"{zone_name}{' Radiant surface Hot Water Outlet Node'}"
            plnt_loop_obj.Number_of_Circuits = "CalculateFromCircuitLength"

            plnt_loop_obj = idf.newidfobject("ZoneHVAC:LowTemperatureRadiant:SurfaceGroup".upper())
            plnt_loop_obj.Name = f"{zone_name}{' Radiant surface list'}"
            if zone_name == "ZoneFloor0":
                plnt_loop_obj.Surface_1_Name = f"{zone_name}{'_GroundFloor'}"
            else:
                plnt_loop_obj.Surface_1_Name = f"{zone_name}{'_Floor'}"
            plnt_loop_obj.Flow_Fraction_for_Surface_1 = 1

            plnt_loop_obj = idf.newidfobject("Sizing:Zone".upper())
            plnt_loop_obj.Zone_or_ZoneList_Name = f"{zone_name}"
            plnt_loop_obj.Zone_Cooling_Design_Supply_Air_Temperature = 14
            plnt_loop_obj.Zone_Cooling_Design_Supply_Air_Temperature_Difference = 5
            plnt_loop_obj.Zone_Heating_Design_Supply_Air_Temperature = 35
            plnt_loop_obj.Zone_Heating_Design_Supply_Air_Temperature_Difference = 10
            plnt_loop_obj.Zone_Cooling_Design_Supply_Air_Humidity_Ratio = 0.009
            plnt_loop_obj.Zone_Heating_Design_Supply_Air_Humidity_Ratio = 0.004
            plnt_loop_obj.Design_Specification_Outdoor_Air_Object_Name = "MFH_NOMINAL_Residential_outdoorair"
            plnt_loop_obj.Zone_Heating_Sizing_Factor = 1.25
            plnt_loop_obj.Zone_Cooling_Sizing_Factor = 1.15
            plnt_loop_obj.Cooling_Minimum_Air_Flow_Fraction = 0
            plnt_loop_obj.Design_Specification_Zone_Air_Distribution_Object_Name = "MFH_NOMINAL_Residential_zone_outdoorair"

            plnt_loop_obj = idf.newidfobject("ZoneHVAC:EquipmentConnections".upper())
            plnt_loop_obj.Zone_Name = f"{zone_name}"
            plnt_loop_obj.Zone_Conditioning_Equipment_List_Name = f"{zone_name}{' Equipment'}"
            plnt_loop_obj.Zone_Air_Node_Name = f"{zone_name}{' Zone Air Node'}"
            plnt_loop_obj.Zone_Return_Air_Node_or_NodeList_Name = f"{zone_name}{' Return Outlet'}"

            plnt_loop_obj = idf.newidfobject("ZoneHVAC:EquipmentList".upper())
            plnt_loop_obj.Name = f"{zone_name}{' Equipment'}"
            plnt_loop_obj.Zone_Equipment_1_Object_Type = "ZoneHVAC:LowTemperatureRadiant:VariableFlow"
            plnt_loop_obj.Zone_Equipment_1_Name = f"{zone_name}{' Radiant surface'}"
            plnt_loop_obj.Zone_Equipment_1_Cooling_Sequence = 1
            plnt_loop_obj.Zone_Equipment_1_Heating_or_NoLoad_Sequence = 1
            plnt_loop_obj.Zone_Equipment_1_Sequential_Cooling_Fraction_Schedule_Name = "ON_24_7"
            plnt_loop_obj.Zone_Equipment_1_Sequential_Heating_Fraction_Schedule_Name = "ON_24_7"

        return idf

    def add_sch_compact(self, idf):
        compact_sch_obj = idf.newidfobject("Schedule:Compact".upper())
        compact_sch_obj.Name = "ON_24_7"
        compact_sch_obj.Schedule_Type_Limits_Name = "Fraction"
        compact_sch_obj.Field_1 = "Through: 12/31"
        compact_sch_obj.Field_2 = "For: AllDays"
        compact_sch_obj.Field_3 = "Until: 24:00,1"

        compact_sch_obj = idf.newidfobject("Schedule:Compact".upper())
        compact_sch_obj.Name = "Dual_setpoint_schedule_type"
        compact_sch_obj.Schedule_Type_Limits_Name = "ANY"
        compact_sch_obj.Field_1 = "Through: 12/31"
        compact_sch_obj.Field_2 = "For: AllDays"
        compact_sch_obj.Field_3 = "Until: 24:00,4"

        compact_sch_obj = idf.newidfobject("Schedule:Compact".upper())
        compact_sch_obj.Name = "HW_plnt_setpoint"
        compact_sch_obj.Schedule_Type_Limits_Name = "ANY"
        compact_sch_obj.Field_1 = "Through: 12/31"
        compact_sch_obj.Field_2 = "For: AllDays"
        compact_sch_obj.Field_3 = "Until: 24:00,36"

        compact_sch_obj = idf.newidfobject("Schedule:Compact".upper())
        compact_sch_obj.Name = "Plnt_ctrl_scheme"
        compact_sch_obj.Schedule_Type_Limits_Name = "ANY"
        compact_sch_obj.Field_1 = "Through: 12/31"
        compact_sch_obj.Field_2 = "For: AllDays"
        compact_sch_obj.Field_3 = "Until: 24:00,1"

        # compact_sch_obj = idf.newidfobject('SCHEDULE:FILE'.upper())
        # compact_sch_obj.Name = 'MFH_NOMINAL_ventilation_fraction_schedule'
        # compact_sch_obj.Schedule_Type_Limits_Name = 'FRACTION'
        # compact_sch_obj.File_Name = ScheduleFile
        # compact_sch_obj.Column_Number = 9
        # compact_sch_obj.Rows_to_Skip_at_Top = 86
        # compact_sch_obj.Number_of_Hours_of_Data = 8760
        # compact_sch_obj.Column_Separator = 'Semicolon'
        # compact_sch_obj.Interpolate_to_Timestep = 'No'

        return idf

    @staticmethod
    def add_building_operation(idf, zone_idf_name, bldg_operation: BuildingOperation, install_characteristics: InstallationsCharacteristics, ureg):
        """
        :param idf: IDF
        :param bldg_operation: cesarp.operation.BuildingOperation
        :return:
        """
        idf_writer_operation.add_people(idf, zone_idf_name, bldg_operation.occupancy, install_characteristics.fraction_radiant_from_activity, ureg)
        idf_writer_operation.add_lights(idf, zone_idf_name, bldg_operation.lighting, install_characteristics.lighting_characteristics, ureg)
        idf_writer_operation.add_electric_equipment(
            idf,
            zone_idf_name,
            bldg_operation.electric_appliances,
            install_characteristics.electric_appliances_fraction_radiant,
            ureg,
        )
        idf_writer_operation.add_hot_water_equipment(idf, zone_idf_name, bldg_operation.dhw, install_characteristics.dhw_fraction_lost, ureg)
        CoSimulationIDFWriter.add_HVAC_template(idf, zone_idf_name, bldg_operation.hvac, bldg_operation.name, ureg)

    @staticmethod
    def add_HVAC_template(idf, zone_idf_name, hvac: HVACOperation, name_prefix: str, ureg):
        thermostat_templ_idf_name = CoSimulationIDFWriter.cosimulation_thermostat_template(idf, hvac.heating_setpoint_schedule, hvac.cooling_setpoint_schedule, name_prefix)
        outdoor_air_spec_idf_name = CoSimulationIDFWriter.cosimulation_outdoor_air_sepc(
            idf, hvac.ventilation_fraction_schedule, hvac.outdoor_air_flow_per_zone_floor_area, name_prefix, ureg
        )
        # hvac_idf_obj = idf.newidfobject(idf_strings.IDFObjects.hvac_template_zone_idealloadsairsystem)
        # hvac_idf_obj.Zone_Name = zone_idf_name
        # hvac_idf_obj.Template_Thermostat_Name = thermostat_templ_idf_name
        # hvac_idf_obj.Outdoor_Air_Method = idf_strings.HVACOutdoorAirMethod.detailed_specification
        # hvac_idf_obj.Design_Specification_Outdoor_Air_Object_Name = outdoor_air_spec_idf_name
        # # clean up unused defaults due to change of outdoor air method
        # hvac_idf_obj.Outdoor_Air_Flow_Rate_per_Person = 0

    def cosimulation_thermostat_template(idf, heating_setpoint_schedule, cooling_setpoint_schedule, name_prefix: str):
        # calling add_schedule before checking if the thremostat template already exists only to have the schedule name to create thermostat template idf name,
        # which must be different in case different schedules for different zones shall be used...
        heating_sched_idf_name = idf_writing_helpers.add_schedule(idf, heating_setpoint_schedule, required_type=cesarp.common.ScheduleTypeLimits.TEMPERATURE())
        cooling_sched_idf_name = idf_writing_helpers.add_schedule(idf, cooling_setpoint_schedule, required_type=cesarp.common.ScheduleTypeLimits.TEMPERATURE())
        # name = name_prefix + "_" + idf_strings.CustomObjNames.thermostat_template
        # idf_obj_type = idf_strings.IDFObjects.hvac_template_thermostat
        # if not idf_writing_helpers.exists_in_idf(idf, idf_obj_type, name):
        #     templ_thermostat_idf_obj = idf.newidfobject(idf_obj_type)
        #     templ_thermostat_idf_obj.Name = name
        #     templ_thermostat_idf_obj.Heating_Setpoint_Schedule_Name = heating_sched_idf_name
        #     templ_thermostat_idf_obj.Cooling_Setpoint_Schedule_Name = cooling_sched_idf_name
        #     templ_thermostat_idf_obj.Constant_Cooling_Setpoint = ""

        # return name

    def cosimulation_outdoor_air_sepc(idf, ventilation_schedule, outdoor_air_flow_per_floor_area: pint.Quantity, name_prefix: str, ureg):
        ventilation_sched_idf_name = idf_writing_helpers.add_schedule(idf, ventilation_schedule, required_type=cesarp.common.ScheduleTypeLimits.FRACTION())
        # idf_obj_type = idf_strings.IDFObjects.design_specifictaion_outdoor_air
        # name = name_prefix + "_" + idf_strings.CustomObjNames.outdoor_air_spec
        # if not idf_writing_helpers.exists_in_idf(idf, idf_obj_type, name):
        #     outdoor_air_spec_idf_obj = idf.newidfobject(idf_obj_type)
        #     outdoor_air_spec_idf_obj.Name = name
        #     outdoor_air_spec_idf_obj.Outdoor_Air_Method = idf_strings.OutdoorAirCalcMethod.flow_per_area
        #     outdoor_air_spec_idf_obj.Outdoor_Air_Flow_per_Zone_Floor_Area = outdoor_air_flow_per_floor_area.to(ureg.m ** 3 / ureg.s / ureg.m ** 2).m
        #     # clean up default values: set to zero because calc method changed to flow/area
        #     outdoor_air_spec_idf_obj.Outdoor_Air_Flow_per_Person = 0
        #     if idf.idd_version[0] < 9 and idf.idd_version[1] < 6:
        #         outdoor_air_spec_idf_obj.Outdoor_Air_Flow_Rate_Fraction_Schedule_Name = ventilation_sched_idf_name
        #     else:
        #         outdoor_air_spec_idf_obj.Outdoor_Air_Schedule_Name = ventilation_sched_idf_name

        # return name
