#pragma once

#include "HaloNet.h"

struct HALONET_API FStorageInfo
{
	FStorageInfo(FString InStorageName, UStruct* InStorageType)
	{
		StorageName = InStorageName;
		StorageType = InStorageType;
	}

	FString StorageName;
	UStruct* StorageType;
};


/** 
 * Interface used to access to generated common info such as GeneratorSignature, StorageStructTypes
 */
class HALONET_API IHaloNetCommon
{
public:

	static IHaloNetCommon& Get()
	{
		check(Instance.IsValid());
		return *Instance;
	}

	static void SetInstance(TSharedPtr<IHaloNetCommon> InInstance)
	{
		Instance = InInstance;
	}

	virtual ~IHaloNetCommon() {}

	virtual TMap<FString, FString>& GetClientEntitiesMapping() = 0;

	virtual TSet<FName>& GetExecCapableClasses() = 0;

	virtual const FString& GetGeneratorSignature() const = 0;

	virtual TArray<FStorageInfo> GetStorageStructTypes() = 0;

	static bool IsValid() { return Instance.IsValid(); };

protected:


	static TSharedPtr<IHaloNetCommon> Instance;
};
