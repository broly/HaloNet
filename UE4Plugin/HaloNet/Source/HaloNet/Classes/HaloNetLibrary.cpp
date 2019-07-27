#include "HaloNet.h"
#include "Entity.h"
#include "Classes/Future.h"
#include "Classes/SliceReplicationHandlers.h"
#include "HaloNetLibrary.h"

UHaloNetLibrary::UHaloNetLibrary()
{
	Clients = MakeShareable(new TMap<FIPv4Endpoint, TSharedPtr<FHaloNetServiceClient>>());

	AccessToken = TEXT("");
	WaitersCounter = 0;
}

// void UHaloNetLibrary::Init(UObject* initializer, FString generator_signature, TSet<FName> ExecClasses)
void UHaloNetLibrary::Init()
{
	UObject* Outer = GetOuter();

	if ensure(Outer->Implements<UEntityInterface>())
		Entities.Add(0, Outer); // This is initiator!
	int32 causer_port;
	FString causer_ip;
	FString access_token;
	int32 port;
	FString base_ip;
	FString base_port;
	PRINTHN("HaloNet Init start");
	// SetGeneratorSignature(generator_signature);
	// ExecCapableClasses = ExecClasses;
	
	if (FParse::Value(FCommandLine::Get(), TEXT("-causer_port="), causer_port) && 
		FParse::Value(FCommandLine::Get(), TEXT("-causer_ip="), causer_ip) &&
		FParse::Value(FCommandLine::Get(), TEXT("-access_token="), access_token) &&
		FParse::Value(FCommandLine::Get(), TEXT("-service_port="), port) &&
		FParse::Value(FCommandLine::Get(), TEXT("-base_ip="), base_ip) &&
		FParse::Value(FCommandLine::Get(), TEXT("-base_port="), base_port))
	{
		PRINTHN("HaloNet params: %i, %s, %s, %i", causer_port, *causer_ip, *access_token, port);
		auto endp = IPPort2Endpoint(causer_ip, causer_port);
		auto mbox = CreateMailbox<UServiceMailbox>(endp);
		int32 pid = FPlatformProcess::GetCurrentProcessId();
		SetAccessToken(access_token);
		mbox->TellPID(pid);
		PRINTHN("HaloNetnetwork pid: %i", pid);
		auto server_endpoint = IPPort2Endpoint(causer_ip, port);
		CreateServer(server_endpoint);
	}
}

void UHaloNetLibrary::OnDataReceived(FHaloNetServiceClient* client_connection, const TArray<uint8> data)
{
	// SILENT_INFO_MSGHN("Got data %s", *Bytes2String(data));
	auto serialized = FBinarySerialization(data);
	auto message_proxy = serialized.Proxy();
	int32 message_type;
	TArray<uint8> message_data;
	// auto datas = serialized.GetDatas();
	//UE_LOG(TestLog, Log, TEXT("qwe %i"), datas.Num());

	message_proxy >> message_type;
	message_proxy >> message_data;



	switch (EConnectionMessageTypes(message_type))
	{
	case EConnectionMessageTypes::RPC_Call:
	{
		auto sr = FBinarySerialization(message_data);
		auto call_proxy = sr.Proxy();
		int32 entity_id;
		int32 method_index;
		int32 future_id;
		FString gen_signature;
		FString access_token;
		TArray<uint8> params;

		call_proxy >> entity_id;
		call_proxy >> gen_signature;
		call_proxy >> method_index;
		call_proxy >> future_id;
		call_proxy >> access_token;
		call_proxy >> params;

		IHaloNetCommon& halo_net_common = IHaloNetCommon::Get();
		if (gen_signature != halo_net_common.GetGeneratorSignature())
			WARN_MSGHN("Generator signature mismatch"); 



		ExecuteRPC(client_connection, entity_id, method_index, future_id, params);

		break; 
	}
	case EConnectionMessageTypes::RPC_Future: 
	{
		auto sr = FBinarySerialization(message_data);
		auto giveback_proxy = sr.Proxy();
		int32 entity_id;
		int32 method_index;
		int32 future_id;
		TArray<uint8> returns;
		
		giveback_proxy >> entity_id;
		giveback_proxy >> method_index;
		giveback_proxy >> future_id;
		giveback_proxy >> returns;

		if (future_id != -1)
			SetFutureResult(entity_id, method_index, future_id, returns);

		break; 
	}
	case EConnectionMessageTypes::RPC_Error:
	{
		auto sr = FBinarySerialization(message_data);
		auto error_proxy = sr.Proxy();
		FString error_source;
		FString error_message;
		int32 future_id;

		error_proxy >> error_source;
		error_proxy >> error_message;
		error_proxy >> future_id;

		WARN_MSGHN("Error from %s: %s", *error_source, *error_message);

		SetFutureError(future_id, error_message);

		break;
	}
	case EConnectionMessageTypes::RPC_Exception:
	{
		auto sr = FBinarySerialization(message_data);
		auto exc_proxy = sr.Proxy();
		FString exc_source;
		FString exc_class;
		FString exc_args;
		int32 future_id;

		exc_proxy >> exc_source;
		exc_proxy >> exc_class;
		exc_proxy >> exc_args;
		exc_proxy >> future_id;


		const FString error_message = FString::Printf(TEXT("%s (%s)"), *exc_class, *exc_args);

		WARN_MSGHN("Exception from %s: %s", *exc_source, *error_message);


		SetFutureError(future_id, error_message);

		break;
	}
	default:
	{
		ERROR_MSGHN("Invalid message incomed");
	};
	}
}

void UHaloNetLibrary::OnErrorReceived(FHaloNetServiceClient* client_connection, const TArray<uint8> data)
{
	FIPv4Endpoint addr = client_connection->RemoteAddress;
	if (Clients->Contains(addr))
		Clients->Remove(addr);
	client_connection->Stop();
}

void UHaloNetLibrary::ExecuteRPC(FHaloNetServiceClient* executor_connection, int32 entity_id, int32 method_index, int32 future_id, TArray<uint8> serialized_params)
{
	if ensureMsgf(Entities.Contains(entity_id), TEXT("There is no entity with ID=%i"), entity_id)
	{
		UObject* entity = Entities[entity_id];
		IEntityInterface* ientity = Cast<IEntityInterface>(entity);
		if ensureMsgf(ientity != nullptr, TEXT("Wrong entity %s with ID=%i"), *GetNameSafe(entity), entity_id)
		{
			TMap<int32, FClientMethodMetadata> methods_list = ientity->GetMethodsList();
			if ensureMsgf(methods_list.Contains(method_index), TEXT("There is no method with index %i"), method_index)
			{
				const FClientMethodMetadata& method_data = methods_list[method_index];
				FName func_name = method_data.MethodName;


				if (method_data.bSystemInternal)
					checkf(entity_id == 0, TEXT("SystemInternal functions can't be called inside entities with id != 0. It's only for service"));

				// if function is SystemInternal, we using this class
				UFunction* function = method_data.bSystemInternal ? FindFunction(func_name) : entity->FindFunction(func_name);

				// ... and this instance
				if (method_data.bSystemInternal)
					entity = this;
				

				if ensure(function)
				{
					FBinarySerialization sr(serialized_params);

					uint8* params = (uint8*)FMemory::Malloc(function->ParmsSize);
					int32 i = 0;

					bool failed = false;

					UProperty* ret_property = function->GetReturnProperty();
					uint8* return_value_ptr = nullptr;

					for (auto prop : TFieldRange<UProperty>(function))
					{
						const int32 offset = prop->GetOffset_ForUFunction();
						uint8* value_ptr = params + offset;

						const bool bIsGivebackParam = method_data.bIsAsync && method_data.bWithDeferredReturn && i == function->NumParms - 1;
						const bool bIsReturnParam = method_data.bIsAsync && !method_data.bWithDeferredReturn && prop == ret_property;

						if (!bIsGivebackParam && !bIsReturnParam)
						{
							if (i > sr.Num())
							{
								failed = true;
								WARN_MSGHN("Serialized data mismatch with method signature %s (not generated or corrupted)", *func_name.ToString());
								break;
							}
							TArray<uint8> param = sr[i++];
							FBinarySerializer::_BinaryArray2PropertyValue(prop, value_ptr, param, this);
						} 

						if (bIsReturnParam)
						{
							return_value_ptr = value_ptr;
						}

						if (bIsGivebackParam)
						{
							if (auto waiter_cls = method_data.WaiterClass)
							{
								UWaiter* future = NewObject<UWaiter>(this, waiter_cls);
								future->SetID(future_id);
								future->SetOwnerObject(entity);
								future->SetMethodIndex(method_index);
								future->SetConnection(executor_connection);
								Waiters.Add(future_id, future);
								// WaitersCounter++;
								FMemory::Memcpy(value_ptr, &future, sizeof(UWaiter*));
							}
						}
					}
					// INFO_MSGHN("Call function at entity_id=%i, method %s", entity_id, *GetNameSafe(function));
					
					if (!failed)
					{
						entity->ProcessEvent(function, params);

						if (method_data.bIsAsync && !method_data.bWithDeferredReturn)
						{
							UWaiter* future = NewObject<UWaiter>(this, UWaiter::StaticClass());
							future->SetID(future_id);
							future->SetOwnerObject(entity);
							future->SetMethodIndex(method_index);
							future->SetConnection(executor_connection);
							Waiters.Add(future_id, future);

							FBinarySerialization retval_sr;
							if (ret_property && return_value_ptr)
								retval_sr << FBinarySerializer::_PropertyValue2BinaryArray(ret_property, return_value_ptr);

							future->SendSerializedData(retval_sr.GetArchived());
						} 


					}


					FMemory::Free(params);
				}
			}
		}
	}
}

void UHaloNetLibrary::SetFutureResult(int32 entity_id, int32 method_index, int32 future_id, TArray<uint8> serialized_returns)
{
	
	if ensure(Futures.Contains(future_id))
	{
		UFuture* future = Futures[future_id];

		UFunction* function = future->FindFunction("Execute");
		if ensure(function)
		{
			FBinarySerialization sr(serialized_returns);
			FBinarySerializationProxy serialized_proxy = sr.Proxy();

			uint8* params = (uint8*)FMemory::Malloc(function->ParmsSize);
			int32 i = 0;
			for (auto prop : TFieldRange<UProperty>(function))
			{
				int32 offset = prop->GetOffset_ForUFunction();
				uint8* value_ptr = params + offset;
				TArray<uint8> param = sr[i++];
				FBinarySerializer::_BinaryArray2PropertyValue(prop, value_ptr, param, this);
			}
			future->ProcessEvent(function, params);

			FMemory::Free(params);
		}
	}
}


UFuture* UHaloNetLibrary::NewFuture(UClass* future_class, TSharedPtr<FHaloNetServiceClient> caller_client)
{
	UFuture* future = NewObject<UFuture>(this, future_class);
	caller_client->OnErrorReceived.AddUObject(future, &UFuture::OnErrorReceivedFunc);
	int32 future_id = Futures.Num();
	Futures.Add(future_id, future);
	future->SetID(future_id);
	return future;
}

void UHaloNetLibrary::SetFutureError(int32 future_id, const FString& error_message)
{
	if ensure(Futures.Contains(future_id))
	{
		UFuture* future = Futures[future_id];
		future->Fail(error_message);
	}
}

void UHaloNetLibrary::SetRecentUsedBaseApp(UMailbox* base_mailbox)
{
	RecentUsedBaseApp = base_mailbox;
}

TSharedPtr<FHaloNetServiceClient> UHaloNetLibrary::CreateClient(FIPv4Endpoint remote_endpoint) const
{
	if (!Clients->Contains(remote_endpoint))
	{
		TSharedPtr<FHaloNetServiceClient> client = MakeShareable(new FHaloNetServiceClient(remote_endpoint, TEXT("HaloNet connection")));
		client->OnDataReceived.BindUObject(this, &UHaloNetLibrary::OnDataReceived);
		client->OnErrorReceived.AddUObject(this, &UHaloNetLibrary::OnErrorReceived);
		Clients->Add(remote_endpoint, client);
	}

	return (*Clients)[remote_endpoint];
}

void UHaloNetLibrary::CreateServer(FIPv4Endpoint server_endpoint)
{
	Server = MakeShareable(new FHaloNetTCPServer(server_endpoint));
	Server->OnSocketAccepted.BindUObject(this, &UHaloNetLibrary::OnClientAccepted);
}

void UHaloNetLibrary::SetAccessToken(FString InAccessToken)
{
	AccessToken = InAccessToken;

}

FString UHaloNetLibrary::GetAccessToken() const
{
	return AccessToken;
}

void UHaloNetLibrary::NewEntity(UObject* entity, int32 entity_id)
{
	Entities.Add(entity_id, entity);
}

void UHaloNetLibrary::SetEntityPropertyValue(int32 entity_id, FString property_name, TArray<uint8> serialized_value)
{
	if (Entities.Contains(entity_id))
	{
		UObject* entity = Entities[entity_id];
		if ensure(entity)
		{
			for (auto prop : TFieldRange<UProperty>(entity->GetClass()))
			{
				if (prop->GetName() == property_name)
				{
					void* value_ptr = prop->ContainerPtrToValuePtr<void>(entity);
					FBinarySerializer::_BinaryArray2PropertyValue(prop, value_ptr, serialized_value, this);

					UFunction* rep_func = entity->FindFunction(*FString::Printf(TEXT("OnBaseRep_%s"), *property_name));
					if (rep_func)
						entity->ProcessEvent(rep_func, nullptr);

					break;
				}
			}
		}
	}
}

void UHaloNetLibrary::SetEntityPropertyValueSlice(int32 entity_id, FString property_name, TArray<uint8> serialized_value)
{
	FBinarySerializationProxy serialization_proxy = FBinarySerializationProxy(serialized_value);

	int32 rep_type;
	serialization_proxy >> rep_type;


	UProperty* prop;
	UObject* entity;

	if (GetEntityAndProperty_WithWarn(entity_id, *property_name, entity, prop))
	{
		switch (ESliceReplicationDataType(rep_type))
		{
		case ESliceReplicationDataType::Map:
			FSliceReplicationHandler<ESliceReplicationDataType::Map>::Handle(entity, prop, serialization_proxy, this);
			break;
		case ESliceReplicationDataType::Array:
			FSliceReplicationHandler<ESliceReplicationDataType::Array>::Handle(entity, prop, serialization_proxy, this);
			break;
		}
	}
}

void UHaloNetLibrary::OnClientAccepted(TSharedPtr<FAddressPair> accepted_pair)
{
	TMap<FName, FName> q; q.Add(NAME_None, NAME_None);
	TSharedPtr<FHaloNetServiceClient> connection = MakeShareable(new FHaloNetServiceClient(accepted_pair->endpoint, TEXT("Connected client"), accepted_pair->socket));
	connection->OnDataReceived.BindUObject(this, &UHaloNetLibrary::OnDataReceived);
	Clients->Add(connection->RemoteAddress, connection);
}

bool UHaloNetLibrary::ProcessConsoleExec(const TCHAR* Cmd, FOutputDevice& Ar, UObject* Executor)
{
	bool handled = false;

	for (auto& exec_capable_mb : ExecCapableMailboxes)
	{
		handled |= exec_capable_mb->ProcessConsoleExec(Cmd, Ar, Executor);
		if (handled)
			return handled;
	}

	for (auto& pair : Entities)
	{
		if (pair.Value)
		{
			if (pair.Key != 0)
			{
				handled |= pair.Value->ProcessConsoleExec(Cmd, Ar, Executor);
				if (handled)
					return handled;
			}
		}
	}
	
	return handled;
}

void UHaloNetLibrary::BeginDestroy()
{
	if (Clients.IsValid())
		for (auto& client_pair : *Clients)
			client_pair.Value->Stop();
	Super::BeginDestroy();
}

UObject* UHaloNetLibrary::GetEntity(int32 id)
{
	if (Entities.Contains(id))
		return Entities[id];
	return nullptr;
}

void UHaloNetLibrary::DestroyEntity(int32 id)
{
	if (Entities.Contains(id))
		if (auto entity = Entities.FindAndRemoveChecked(id))
		{
			auto as_client_interface = Cast<IEntityInterface>(entity);
			as_client_interface->StartEntityDestroy();
			if (auto as_actor = Cast<AActor>(entity))
			{
				as_actor->Destroy();
			}
			else
			{
				entity->ConditionalBeginDestroy();
			}
		}
}

FString UHaloNetLibrary::GetStoragesDigest()
{
	FString storages_digest = TEXT("None");
	GConfig->GetString(TEXT("HaloNet"), TEXT("StoragesDigest"), storages_digest, GEngineIni);
	return storages_digest;
}

void UHaloNetLibrary::SaveStoragesData(TArray<uint8> InData, FString InNewDigest)
{
	GConfig->SetString(TEXT("HaloNet"), TEXT("StoragesDigest"), *InNewDigest, GEngineIni);

	//FString filename = FString::Printf(TEXT("%s/HaloNet/Storages.dat"), *FPaths::GameSavedDir()); 4.15
	FString filename = FString::Printf(TEXT("%s/HaloNet/Storages.dat"), *FPaths::ProjectSavedDir()); //4.18

	if (!FFileHelper::SaveArrayToFile(InData, *filename))
		ERROR_MSGHN("Failed to save storages");
}

void UHaloNetLibrary::LoadStoragesData(TArray<uint8>& OutData)
{
	//FString filename = FString::Printf(TEXT("%s/HaloNet/Storages.dat"), *FPaths::GameSavedDir()); 4.15
	FString filename = FString::Printf(TEXT("%s/HaloNet/Storages.dat"), *FPaths::ProjectSavedDir()); //4/18

	if (!FFileHelper::LoadFileToArray(OutData, *filename))
		ERROR_MSGHN("Failed to load storages");
}

void UHaloNetLibrary::DestroySession()
{
	AccessToken = TEXT("");
	for (auto& entity : Entities)
	{
		if (entity.Key != 0 && entity.Value->IsValidLowLevel() && !entity.Value->IsPendingKill())
		{
			if (auto as_actor = Cast<AActor>(entity.Value))
				as_actor->Destroy();
			else
				entity.Value->ConditionalBeginDestroy();
		}
	}
	ExecCapableMailboxes.Empty();
}

UWaiter* UHaloNetLibrary::GetWaiter(int32 waiter_id)
{
	UWaiter** waiter = Waiters.Find(waiter_id);
	return waiter ? *waiter : nullptr;
}

void UHaloNetLibrary::CreateClientEntity(const FString& entity_class_name, int32 entity_id, UEmptyWaiter* __waiter__)
{
	auto& client_entities_mapping = IHaloNetCommon::Get().GetClientEntitiesMapping();

	if (client_entities_mapping.Contains(entity_class_name))
	{
		FString entity_using_class_name = client_entities_mapping[entity_class_name];
		UClass* cls = LoadClass<UObject>(this, *entity_using_class_name);
		FTransform spawn_transform = FTransform(FRotator(0.f, 0.f, 0.f), FVector(0.f, 0.f, 0.f), FVector(1.f));
		UObject* op_entity = nullptr;
		if (cls->IsChildOf<AActor>())
		{
			FActorSpawnParameters sp;
			sp.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			if (auto entity = GetWorld()->SpawnActor<AActor>(cls, FVector(0.f, 0.f, 0.f), FRotator(0.f, 0.f, 0.f), sp))
				op_entity = entity;

		}
		else
		{
			if (cls)
				op_entity = NewObject<UObject>(this, cls);
			else
				ERROR_MSGHN("Unable to create entity with class name %s", *entity_using_class_name);
		}
		if ensure(op_entity != nullptr)
		{
			NewEntity(op_entity, entity_id);
			if (auto i_entity = Cast<IEntityInterface>(op_entity))
			{
				// i_entity->SetGameInstance(GameInstance);
				int32 waiter_id = __waiter__->GetID();

				auto BaseApp = (UBaseAppExtended*)RecentUsedBaseApp;

				BaseApp->OnClientEntityCreated(entity_id) await [=](bool success)
				{
					UObject* local_op_entity = GetEntity(entity_id);

					if (auto local_i_entity = Cast<IEntityInterface>(local_op_entity))
					{
						UWaiter* waiter = GetWaiter(waiter_id);
						if (success &&
							ensure(local_op_entity->IsValidLowLevel()) &&
							ensure(!local_op_entity->IsPendingKill()) &&
							ensureMsgf(waiter, TEXT("Waiter not found!")))
						{
							local_i_entity->SetHaloNet(this);
							local_i_entity->SetEntityID(entity_id);
							local_i_entity->EntitySpawned(waiter->GetConnection());
						}
					}
				};
			}
		}
	}

	giveback NoneResult;
}

void UHaloNetLibrary::DestroyClientEntity(int32 entity_id)
{
	DestroyEntity(entity_id);
}

void UHaloNetLibrary::UpdateClientEntityVariable(int32 entity_id, const FString& property_name, FBytes data)
{
	SetEntityPropertyValue(entity_id, property_name, data.Data);
}

void UHaloNetLibrary::UpdateClientEntityVariableSlice(int32 entity_id, const FString& property_name, FBytes data)
{
	SetEntityPropertyValueSlice(entity_id, property_name, data.Data);
}

TSharedPtr<IHaloNetCommon> IHaloNetCommon::Instance = nullptr;
