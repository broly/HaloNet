// Fill out your copyright notice in the Description page of Project Settings.

#include "HaloNet.h"
#include "HaloNetLibrary.h"
#include "Mailbox.h"


UMailbox::UMailbox(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
	, ClientConnection(nullptr)
	, RemoteID(0)
	, HaloNetLibrary(nullptr)
{
}

void UMailbox::SetConnection(TSharedPtr<FHaloNetServiceClient> client_conn)
{
	ClientConnection = client_conn;
	ClientConnection->OnErrorReceived.AddUObject(this, &UMailbox::OnErrorReceived);
}

void UMailbox::SetHaloNet(UHaloNetLibrary* halo_net)
{
	HaloNetLibrary = halo_net;
}

bool UMailbox::MethodCaller(int32 method_index, int32 future_id, TArray<uint8> args) const
{
	auto serialized_call = FBinarySerialization();
	serialized_call << RemoteID;
	serialized_call << IHaloNetCommon::Get().GetGeneratorSignature();
	serialized_call << method_index;
	serialized_call << future_id; // future data
	serialized_call << HaloNetLibrary->GetAccessToken();
	serialized_call << args;

	auto message = FBinarySerialization();
	message << int32(EConnectionMessageTypes::RPC_Call);
	message << serialized_call;


	return !ClientConnection->Send(message.GetArchived());
}

void UMailbox::ExecuteMethodCall(FName method_name, FFrame& Stack, RESULT_DECL)
{
	if (!IsValid())
	{
		WARN_MSGHN("Call to invalid mailbox method %s: disconnected", *method_name.ToString());
		*(UFuture**)RESULT_PARAM = nullptr;
		return;
	}

	UFunction* func = FindFunction(method_name);
	FBinarySerialization serialized;
	UProperty* return_prop = func->GetReturnProperty();

	UFuture* future = nullptr;
	
	for (UProperty* prop : TFieldRange<UProperty>(func))
	{
		if (prop == return_prop)
		{
			auto obj_prop = Cast<UObjectPropertyBase>(prop);
			future = HaloNetLibrary->NewFuture(obj_prop->PropertyClass, ClientConnection);
			// Stack.StepCompiledIn<UObjectPropertyBase>(&future);
			*(UFuture**)RESULT_PARAM = future;
			continue;
		}

		void* value_ptr = FMemory::Malloc(prop->GetSize());
		prop->InitializeValue(value_ptr);
		Stack.StepCompiledIn<UProperty>(value_ptr);
		serialized << FBinarySerializer::_PropertyValue2BinaryArray(prop, value_ptr);
		FMemory::Free(value_ptr);
	}

	int32 future_id = future != nullptr ? future->GetID() : -1;
	int32 method_index = MethodsIndices[method_name];

	bool called = MethodCaller(method_index, future_id, serialized.GetArchived());

	if (!called)
		ERROR_MSGHN("Call to invalid mailbox %s! %s::%s(). Probably connection is broken", 
			*GetNameSafe(this), *GetNameSafe(GetClass()), *method_name.ToString());
}

void UMailbox::SetRemoteID(int32 InID)
{
	RemoteID = InID;
}

void UMailbox::SetEndpoint(FIPv4Endpoint InEndpoint)
{
	Endpoint = InEndpoint;
}

bool UMailbox::IsValid() const
{
	return ::IsValid(this) && ClientConnection.IsValid() && ClientConnection->IsConnected() && !bDisconnected;
}

void UMailbox::OnErrorReceived(FHaloNetServiceClient* client, TArray<uint8> data)
{
	bDisconnected = true;
	OnDisconnected.Broadcast();
}

void UMailbox::ForceSendDataToConnection()
{
	ClientConnection->ForceSendData();
}


void UService_TellPID_Future::Execute()
{
	if (bExecuteAnyway || (FutureContext && FutureContext->IsValidLowLevel()))
		OnSetResultStatic.ExecuteIfBound();
	OnSetResult.Broadcast();
}




UServiceMailbox::UServiceMailbox(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	MethodsIndices.Add(TEXT("TellPID"), 0);

}


UService_TellPID_Future* UServiceMailbox::TellPID(int32 pid) REMOTE_CALLER_RETVAL(UService_TellPID_Future*, TellPID, int32, pid);

