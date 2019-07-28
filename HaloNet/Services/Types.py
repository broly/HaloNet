# -*- coding: utf-8 -*-
import json

from Core import ERROR_MSG
from Core.Common.Enum import member
from Core.Declarators.Specs import BlueprintType, Blueprintable, Hidden
from Core.LocalDatatypes import *
from Core.LocalDatatypes import FPropertyInfo
from Core.Utils import CODE
from Core.Storage import Storages
from Core.Type import STORAGE, USTRUCT, TArray, TMap, UENUM, TAssetSubclassOf, TSubclassOf, TSet, \
    validate_container, validate_containers, UJsonRaw, reconstruct, FDateTime, TBaseMailbox, TUE4Mailbox

if False:
    from UE4App import UE4App

@USTRUCT()
class FOnlineStatisticEntry:
    AppName: FString
    Date: FDateTime
    OnlineCount: int32
    InGameCount: int32


@UENUM(BlueprintType, Blueprintable)
class EGameType:
    Simple:         member()
    Survival:       member()


@UENUM(Blueprintable, BlueprintType)
class EReqGameResponse:
    Denied: member()
    Wait: member()
    Success: member()


@UENUM()
class EMatchState:
    Idle:       member()
    Preparing:  member()
    InGame:     member()


@USTRUCT(Blueprintable, BlueprintType)
class FDedicatedServerInfo:
    """
    Информация о Dedicated server
    @cvar GamePort: dedicated server listen port
    @cvar PID: process identifier
    @cvar TextData: text data of this process
    @cvar AccessToken: access token for authority
    """
    ID: int32
    State: EMatchState
    GamePort: int32
    PID: int32
    TextData: FString
    AccessToken: FString
    MapName: FString
    GameModeInfo: FString


@USTRUCT()
class FMatchInfo:
    MatchState: EMatchState
    MatchMax: int32
    MatchUsers: TArray[FString]
    MapName: FName
    GameType: EGameType
    Additional: UJsonRaw
    ID: int32
    # Game: TUE4Mailbox('UE4App')


@USTRUCT()
class FBaseAppGenericStateInfo:
    AppName: FString
    Players: TArray[UJsonRaw]
    Games: TArray[FMatchInfo]

@USTRUCT(Blueprintable, BlueprintType)
class FMapInfo:
    """ Информация о карте: имя, путь к карте, какой гейм-мод и максимум игроков возможных для игры """
    Name: FString
    Asset: FString
    GameMode: UClass
    PlayersMax: int32
    Type: EGameType




@UENUM(Blueprintable, BlueprintType)
class EEquipmentSlot:
    NoSlot: member()
    Skin: member()
    Head: member()
    Lighting: member()


@USTRUCT(BlueprintType, Blueprintable)
class FViperItemInfo:
    Name: FName
    # Asset: TSubclassOf['UViperItem']
    MaxStack: int32
    CompatibleSlot: EEquipmentSlot


@USTRUCT(BlueprintType, Blueprintable)
class FItemInstance:
    Name: FName
    InstanceID: int32
    Count: int32

@USTRUCT(BlueprintType, Blueprintable)
class FSlotItemPair:
    Slot: EEquipmentSlot
    Item: FItemInstance

@USTRUCT(Blueprintable, BlueprintType)
class FStatisticsRecord:
    Username: FString
    Score: int32

# *** <SECTION> Container types definitions </SECTION> ***
# TODO: You must define new container type before using in code
validate_containers(
    TMap[FName, int32],
    TArray[FString],
    TMap[FString, FString],
    TArray[int32],
    TArray[uint8],
    TMap[FString, TArray[FString]],
    TArray[FPropertyInfo],
    TSet[FName],
    TArray[FMatchInfo],
    TArray[FDedicatedServerInfo],
    TArray[FMapInfo],
    # TMap[FName, Float],
    TMap[int32, FString],
    TMap[int32, int32],
    TArray[UJsonRaw],
    TArray[FOnlineStatisticEntry],
    TArray[FViperItemInfo],
    TArray[FItemInstance],
    TMap[int32, FItemInstance],
    TMap[EEquipmentSlot, int32],
    TMap[EEquipmentSlot, FItemInstance],
    TArray[FSlotItemPair],
    TArray[TBaseMailbox('BaseApp')],
    TArray[FBaseAppGenericStateInfo],
    TArray[FStatisticsRecord]
)
