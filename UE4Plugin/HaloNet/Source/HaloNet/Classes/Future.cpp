#include "HaloNet.h"
#include "Utils.h"
#include "HaloNetLibrary.h"
#include "Future.h"
#include "Entity.h"

void UWaiter::SetID(int32 InID)
{
	WaiterID = InID;
}

int32 UWaiter::GetID() const
{
	return WaiterID;
}


void UWaiter::SetMethodIndex(int32 InMethodIndex)
{
	MethodIndex = InMethodIndex;
}

void UWaiter::SetEntityID(int32 InEntityID)
{
	EntityID = InEntityID;
}

void UWaiter::SetHaloNet(UHaloNetLibrary* InHaloNet)
{
	HaloNet = InHaloNet;
}

void UWaiter::SetOwnerObject(UObject* InOwnerObject)
{
	OwnerObject = InOwnerObject;
}

void UWaiter::SetConnection(FHaloNetServiceClient* Conn)
{
	RemoteConnection = Conn;
}

void UWaiter::ProcessExecuteReturn(UFunction* func, FFrame& Stack)
{
	FBinarySerialization serialized;
	for (auto prop : TFieldRange<UProperty>(func))
	{
		void* value_ptr = FMemory::Malloc(prop->GetSize());
		prop->InitializeValue(value_ptr);
		Stack.StepCompiledIn<UProperty>(value_ptr);
		serialized << FBinarySerializer::_PropertyValue2BinaryArray(prop, value_ptr);
		FMemory::Free(value_ptr);
	}

	// P_FINISH;
	// INFO_MSGHN("Send return values %i %i %i", WaiterID, EntityID, MethodIndex);
	
	SendSerializedData(serialized.GetArchived());
}


void UWaiter::SendSerializedData(TArray<uint8> bytes)
{
	auto serialized_ret = FBinarySerialization();
	serialized_ret << EntityID;
	serialized_ret << MethodIndex;
	serialized_ret << WaiterID; // future data
	serialized_ret << bytes;

	auto message = FBinarySerialization();
	message << int32(EConnectionMessageTypes::RPC_Future);
	message << serialized_ret;

	RemoteConnection->Send(message.GetArchived());
}

FHaloNetServiceClient* UWaiter::GetConnection() const
{
	return RemoteConnection;
}

UFuture::UFuture(const FObjectInitializer& ObjectInitializer)
{
	FutureID = 0;
	bIsDone = false;
	bExecuteAnyway = false;
}

void UFuture::SetID(int32 InID)
{
	FutureID = InID;
}

int32 UFuture::GetID() const
{
	return FutureID;
}

void UFuture::SetResult(const TArray<uint8>& return_values)
{
	if ensure(!bIsDone)
	{
		UFunction* exec_func = FindFunction("Execute");
		if ensure(exec_func)
		{
			FBinarySerialization sr(return_values);

			uint8* params = (uint8*)FMemory::Malloc(exec_func->ParmsSize);
			int32 i = 0;
			for (auto prop : TFieldRange<UProperty>(exec_func))
			{
				int32 offset = prop->GetOffset_ForUFunction();
				uint8* value_ptr = params + offset;
				TArray<uint8> param = sr[i++];
				FBinarySerializer::_BinaryArray2PropertyValue(prop, value_ptr, param, Cast<UHaloNetLibrary>(GetOuter()));
			}
			ProcessEvent(exec_func, params);
			bIsDone = true;
		}
	}
}

void UFuture::SetContext(UObject* context)
{
	FutureContext = context;
}

void UFuture::Fail(const FString& error)
{
	WARN_MSGHN("Future %s (%i) failed: %s", *GetClass()->GetName(), FutureID, *error);
	OnErrorReceived.Broadcast(error);
	OnErrorReceivedStatic.ExecuteIfBound(error);
	bIsDone = true;
}

