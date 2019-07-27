import random
from traceback import print_exc
from typing import List, Dict

from copy import deepcopy

from Core import WARN_MSG, ERROR_MSG, INFO_MSG
from Core.LocalDatatypes import int32, FName
from Core.Transaction import ensure_locked
from Storages import CitizenAbilities, CitizenAbilitiesLeveling
from Types import *

def get_citizen_ability_info(citizen: FCitizen, ability_name: str) -> (int, FCitizenAbility):
    for a_name, a_value in citizen.Abilities:
        ability_info = CitizenAbilities.get_by("Name", a_name)


def get_citizens_with_ability_names_by_ids_and_ability_type(city, citizens_ids, ability_type_name, building_name) -> Dict[str, List[FCitizen]]:
    result = dict()


    for cid in citizens_ids:
        if cid not in city.Citizens:
            WARN_MSG(f"Failed to get citizen with id {cid}")
            continue
        citizen = city.Citizens[cid]
        for ability_name, ability_experience in citizen.Abilities.items():
            ability_info = CitizenAbilities.get_by("Name", ability_name)
            if ability_info['AbilityType'] == ability_type_name and building_name in ability_info['BuildingTypes']:
                if ability_name not in result:
                    result[ability_name] = list()
                result[ability_name].append(citizen)
    return result

def get_ability_level(experience, multiplier):
    level_by_exp = dict()
    for entry in CitizenAbilitiesLeveling.get():
        level_by_exp[entry['Experience'] * multiplier] = entry['Level']

    prev_exp = 0
    for exp in level_by_exp.keys():
        if experience > exp:
            return level_by_exp[prev_exp]
        prev_exp = exp
    return 0


class CityCitizensConsts:
    MAX_NAME = 5
    MAX_CAMEO = 0
    MAX_BODY = 0
    MAX_CHEST = 3
    MAX_LEGS = 2
    MAX_SHOES = 2


def random_citizen_appearance():
    return FAppearance(
        Gender=random.choice(EGender.__members__),
        Complexion=random.choice(EHumanComplexion.__members__),
        CameoID=random.randint(0, CityCitizensConsts.MAX_CAMEO),
        NameID=random.randint(0, CityCitizensConsts.MAX_NAME),
        BodyID=random.randint(0, CityCitizensConsts.MAX_BODY),
        ChestID=random.randint(0, CityCitizensConsts.MAX_CHEST),
        LegsID=random.randint(0, CityCitizensConsts.MAX_LEGS),
        ShoesID=random.randint(0, CityCitizensConsts.MAX_SHOES),
    )


class WorkingResult:
    def __init__(self):
        self.data = None

    def empty(self):
        return self.data is None

    def get(self):
        return self.data

    def set(self, data):
        self.data = data


class CityCitizens:

    @staticmethod
    def get_work_result(city, building_name: str, citizens_ids: List[int32], ability_type_name: str, **kwargs):
        return CityCitizens.work(city, building_name, citizens_ids, ability_type_name, 0, **kwargs)

    @staticmethod
    def work(city, building_name: str, citizens_ids: List[int32], ability_type_name: str, amount: int = 1, **kwargs) -> WorkingResult:
        result = WorkingResult()
        if city.Citizens.locked or amount == 0:
            citizens_by_abilities = get_citizens_with_ability_names_by_ids_and_ability_type(city, citizens_ids, ability_type_name, building_name)
            for ability_name, citizens in citizens_by_abilities.items():
                ability_info = CitizenAbilities.get_by("Name", ability_name)
                for citizen in citizens:
                    current_experince = citizen.Abilities[ability_name]
                    multiplier = ability_info['ExperienceMultiplier']
                    ability_level = get_ability_level(current_experince, multiplier)
                    leveled_ability_info = CitizenAbilitiesLeveling.get_by("Level", ability_level)
                    parameters = deepcopy(ability_info['BaseParameters'])
                    if leveled_ability_info:
                        for parameter_name in parameters.keys():
                            if parameter_name in ability_info['BaseParameters']:
                                if isinstance(parameters[parameter_name], (int, float)):
                                    parameters[parameter_name] += leveled_ability_info['Parameters'][parameter_name] * ability_info['LeveledParametersMultipliers'][parameter_name]
                                else:
                                    if parameter_name in leveled_ability_info['Parameters']:
                                        parameters[parameter_name] = leveled_ability_info['Parameters'][parameter_name]

                    func = getattr(CityCitizens, ability_type_name, None)
                    if func is not None:
                        INFO_MSG(f"Working {ability_type_name} in {building_name} with citizen {citizen}")
                        try:
                            func(result, **parameters, **kwargs)
                        except Exception as e:
                            ERROR_MSG(f"Something went wrong in CityCitizens::{ability_type_name}")
                            print_exc()
                    else:
                        ERROR_MSG(f"Ability {ability_type_name} not released")
                    if amount > 0:
                        citizen.Abilities[ability_name] += amount
        return result


    @staticmethod
    def ResourceChance(working_result: WorkingResult, ItemName, ResourceChance, MUTATED_resources=dict()):
        if working_result.data is None:
            working_result.data = []
        if ItemName in MUTATED_resources:
            MUTATED_resources[ItemName]['Chance'] += ResourceChance
            # working_result.data.append({"ItemName": ItemName,
            #                             "Chance": ResourceChance})

    @staticmethod
    def ReduceTick(working_result: WorkingResult, TickMultiplier, MUTATED_tick_info=dict()):
        if 'TickReduce' not in MUTATED_tick_info:
            MUTATED_tick_info['TickReduce'] = 1
        MUTATED_tick_info['TickReduce'] += TickMultiplier
