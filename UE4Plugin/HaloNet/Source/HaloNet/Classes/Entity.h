#pragma once

#include "HaloNet.h"
#include "Sockets.h"
#include "Networking.h"
#include "TCPClient.h"
#include "Entity.generated.h"

struct FClientMethodMetadata;


UINTERFACE()
class HALONET_API UEntityInterface : public UInterface
{
	GENERATED_UINTERFACE_BODY()

};

class HALONET_API IEntityInterface
{
	GENERATED_IINTERFACE_BODY()

public:
	// UFUNCTION()
	// virtual void Execute() = 0;

	virtual int32 GetEntityID() = 0;

	virtual void SetEntityID(int32 entity_id) = 0;

	virtual void SetHaloNet(class UHaloNetLibrary* InHN) = 0;

	virtual TMap<int32, FClientMethodMetadata> GetMethodsList() = 0;

	virtual void EntitySpawned(FHaloNetServiceClient* Connection) = 0;

	virtual void StartEntityDestroy() = 0;

	virtual void SetGameInstance(UGameInstance* InGameInstance) = 0;

	// UFUNCTION(BlueprintNativeEvent, Category = "HaloNet")
	// void OnEntitySpawned();


};

// UCLASS()
// class HALONET_API UEntity
// 	: public AActor
// 	, public IEntityInterface
// {
// 
// 	virtual TMap<int32, FName> GetMethodsList() override { return MethodsList; };
// 	
// 	UPROPERTY()
// 	TMap<int32, FName> MethodsList;
// };

