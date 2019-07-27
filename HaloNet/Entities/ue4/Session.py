from Core import INFO_MSG
from Core.BaseEntity import UE4Entity
from Core.Declarators.rmi import rmi
from Core.Declarators.Specs import Exposed, BlueprintNativeEvent, BlueprintImplementableEvent
from Core.Entity import Entity
from Core.LocalDatatypes import *
from Core.Type import TArray
from Types import EMatchState


class Session(UE4Entity):
    is_exposed = True
    base_entity_class = 'UObject'
    using_class = "/Game/Viper/Blueprints/HaloNet/Session_BP.Session_BP_C"
    context_name = "ue4"

    @rmi(Exposed)
    async def test(self):
        pass

    # @rmi(Exposed, BlueprintNativeEvent)
    # def InformPresent(self, archetype_name: FName, character_id: int32, archetype_exp: int32, character_exp: int32, given_items: TArray[FCityResource]):
    #     """
    #     Informs client about present
    #
    #     @param archetype_exp:
    #     @param character_exp:
    #     @param given_items:
    #     @return:
    #     """

    @rmi(Exposed, BlueprintNativeEvent)
    def UpdateMatchState(self, match_state: EMatchState):
        """

        @param match_state:
        @return:
        """