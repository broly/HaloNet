#pragma once

#include "HaloNet.h"
#include "Sockets.h"
#include "Networking.h"
#include "Future.h"
// #include "Waiter.h"
#include "MethodInfo.generated.h"



USTRUCT()
struct FClientMethodMetadata
{
	GENERATED_USTRUCT_BODY()

public:
	FClientMethodMetadata()
		: ID(0)
		, MethodName("")
		, bIsAsync(false)
		, WaiterClass(nullptr)
		, bWithDeferredReturn(false)
		, bSystemInternal(false)
	{}

	FClientMethodMetadata(int32 InID, FName InMethodName, bool InIsAsync, TSubclassOf<UWaiter> InWaiterClass, bool InWithDeferredReturn, bool InSystemInternal)
		: ID(InID)
		, MethodName(InMethodName)
		, bIsAsync(InIsAsync)
		, WaiterClass(InWaiterClass)
		, bWithDeferredReturn(InWithDeferredReturn)
		, bSystemInternal(InSystemInternal)
	{}

	UPROPERTY()
	int32 ID;

	UPROPERTY()
	FName MethodName;

	UPROPERTY()
	bool bIsAsync;

	UPROPERTY()
	TSubclassOf<UWaiter> WaiterClass;

	UPROPERTY()
	bool bWithDeferredReturn;

	UPROPERTY()
	bool bSystemInternal;
};

USTRUCT()
struct FRemoteMethodMetadata
{
	GENERATED_USTRUCT_BODY()

public:
	FRemoteMethodMetadata()
		: ID(0)
		, MethodName("")
		, bIsAsync(false)
		, FutureClass(nullptr)
	{}

	FRemoteMethodMetadata(int32 InID, FName InMethodName, bool InIsAsync, TSubclassOf<UFuture> InFutureClass)
		: ID(InID)
		, MethodName(InMethodName)
		, bIsAsync(InIsAsync)
		, FutureClass(InFutureClass)
	{}

	UPROPERTY()
	int32 ID;

	UPROPERTY()
	FName MethodName;

	UPROPERTY()
	bool bIsAsync;

	UPROPERTY()
	TSubclassOf<UFuture> FutureClass;
};
