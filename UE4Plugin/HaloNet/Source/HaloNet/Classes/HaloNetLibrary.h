#pragma once

#include "HaloNet.h"
#include "Sockets.h"
#include "Networking.h"
#include "Mailbox.h"
#include "TCPClient.h"
#include "TCPServer.h"
#include "MethodInfo.h"
#include "IHaloNetCommon.h"
#include "HaloNetLibrary.generated.h"

/**
 * The management core of communication with remote HaloNet's services
 */
UCLASS()
class HALONET_API UHaloNetLibrary
	: public UObject
	, public FExec
{
	GENERATED_BODY()

public:
	UHaloNetLibrary();

	/**
	 * Core initializer, called from GameInstance
	 * @param initializer (GameInstance)
	 */
	// void Init(UObject* initializer, FString generator_signature, TSet<FName> ExecClasses);
	void Init();

	/**
	 * Called when receiving any data from connetion	 
	 * @param client_connection connection to data source
	 * @param data the date from connection
	 */
	void OnDataReceived(FHaloNetServiceClient* client_connection, const TArray<uint8> data);

	/**
	 */
	void OnErrorReceived(FHaloNetServiceClient* client_connection, const TArray<uint8> data);

	/**
	 * Call local RPC method according to parameters	 
	 * @param executor_connection connection of the caller
	 * @param entity_id the identifier of the entity on which you want to call the method
	 * @param method_index index of the called method
	 * @param future_id the ID of the future, which will be waiting for the result of the method
	 * @param params serialized parameters to the method call
	 */
	void ExecuteRPC(FHaloNetServiceClient* executor_connection, int32 entity_id, int32 method_index, int32 future_id, TArray<uint8> params);

	/**
	 * Notifies you of the result of calling a remote method
	 * @param entity_id The ID of the entity on which the method was called
	 * @param method_index index of the invoked method
	 * @param future_id ID future of called method
	 * @param serialized_returns sterilized return values 
	 */
	void SetFutureResult(int32 entity_id, int32 method_index, int32 future_id, TArray<uint8> serialized_returns);
	
	/**
	 * Creation of the new future
	 * @param future_class class of the future
	 * @returns new future
	 */
	class UFuture* NewFuture(UClass* future_class, TSharedPtr<FHaloNetServiceClient> caller_client);

	void SetFutureError(int32 future_id, const FString& error_message);

	/**
	 * Creation of the mailbox of the remote entity
	 * @param remote_endpoint service enpoint
	 * @param entity_id remote entity's id (0 = service mailbox itself)
	 */
	template<typename T = UMailbox>
	T* CreateMailbox(FIPv4Endpoint remote_endpoint, int32 entity_id = 0, UClass* mailbox_class = T::StaticClass())
	{
		TSharedPtr<FHaloNetServiceClient> client = CreateClient(remote_endpoint);
		auto mbox = NewObject<T>(this, mailbox_class);
		mbox->SetConnection(client);
		mbox->SetHaloNet(this);
		mbox->SetRemoteID(entity_id);
		mbox->SetEndpoint(remote_endpoint);

		const FName cls_name = mailbox_class->GetFName();

		IHaloNetCommon& halo_net_common = IHaloNetCommon::Get();
		if (halo_net_common.GetExecCapableClasses().Contains(cls_name))
			ExecCapableMailboxes.Add(mbox);

		return mbox;
	}

	template<typename T = UMailbox>
	T* CreateMailboxWithoutConnection(FIPv4Endpoint remote_endpoint, int32 entity_id = 0, UClass* mailbox_class = T::StaticClass())
	{
		auto mbox = NewObject<T>(this, mailbox_class);
		mbox->SetHaloNet(this);
		mbox->SetRemoteID(entity_id);
		mbox->SetEndpoint(remote_endpoint);

		const FName cls_name = mailbox_class->GetFName();

		IHaloNetCommon& halo_net_common = IHaloNetCommon::Get();
		if (halo_net_common.GetExecCapableClasses().Contains(cls_name))
			ExecCapableMailboxes.Add(mbox);

		return mbox;
	}

	void SetRecentUsedBaseApp(UMailbox* base_mailbox);

	/** 
	 * Create a new connection
	 * @param remote_endpoint endpoint remote service 
	 * @returns pointer to the new connction
	 */
	TSharedPtr<FHaloNetServiceClient> CreateClient(FIPv4Endpoint remote_endpoint) const;

	void CreateServer(FIPv4Endpoint server_endpoint);

	void SetAccessToken(FString InAccessToken);

	FString GetAccessToken() const;

	void NewEntity(UObject* entity, int32 entity_id);

	void SetDefaultEndpoint(FIPv4Endpoint InEndpoint) { DefaultEndpoint = InEndpoint; };

	FIPv4Endpoint& GetDefaultEndpoint() { return DefaultEndpoint; }

	void SetEntityPropertyValue(int32 entity_id, FString property_name, TArray<uint8> serialized_value);

	void SetEntityPropertyValueSlice(int32 entity_id, FString property_name, TArray<uint8> serialized_value);

	void OnClientAccepted(TSharedPtr<FAddressPair> accepted_pair);
	
	virtual bool ProcessConsoleExec(const TCHAR* Cmd, FOutputDevice& Ar, UObject* Executor) override;

	virtual void BeginDestroy() override;

	UObject* GetEntity(int32 id);

	void DestroyEntity(int32 id);

	FString GetStoragesDigest();

	void SaveStoragesData(TArray<uint8> InData, FString InNewDigest);

	void LoadStoragesData(TArray<uint8>& OutData);

	void DestroySession();

	template<typename TProperty>
	bool GetEntityAndProperty_WithWarn(int32 entity_id, FName property_name, UObject*& OutEntity, TProperty*& OutProperty)
	{
		if (Entities.Contains(entity_id))
		{
			UObject* entity = Entities[entity_id];
			if ensure(entity)
				for (auto prop : TFieldRange<TProperty>(entity->GetClass()))
					if (prop->GetFName() == property_name)
					{
						OutEntity = entity;
						OutProperty = prop;
						return true;
					}
		}
		return false;
	}

	UWaiter* GetWaiter(int32 waiter_id);

public:  /// SystemInternal Service API

	UFUNCTION()
	void CreateClientEntity(const FString& entity_class_name, int32 entity_id, UEmptyWaiter* __waiter__);

	UFUNCTION()
	void DestroyClientEntity(int32 entity_id);

	UFUNCTION()
	void UpdateClientEntityVariable(int32 entity_id, const FString& property_name, FBytes data);

	UFUNCTION()
	void UpdateClientEntityVariableSlice(int32 entity_id, const FString& property_name, FBytes data);


protected:
	/** List of the clients */
	TSharedPtr<TMap<FIPv4Endpoint, TSharedPtr<FHaloNetServiceClient>>> Clients;

	TSharedPtr<FHaloNetTCPServer> Server;
	
	/** List of the local entities */
	UPROPERTY()
	TMap<int32, UObject*> Entities;

	/** List of the futures */
	UPROPERTY()
	TMap<int32, UFuture*> Futures;

	/** [DEPRECATED] List of the removed futures (Waiters) */
	UPROPERTY()
	TMap<int32, UWaiter*> Waiters;

	/// DEPRECATED
	UPROPERTY()
	int32 WaitersCounter;

	UPROPERTY()
	FString AccessToken;

	UPROPERTY()
	TSet<UMailbox*> ExecCapableMailboxes;

	FIPv4Endpoint DefaultEndpoint;

	UMailbox* RecentUsedBaseApp;

};



/// BOILERPLATE CODE

UCLASS()
class HALONET_API UBaseAppExtended_OnClientEntityCreated_Future : public UFuture
{
	GENERATED_BODY()

public:
	DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnSetResult, bool, RetVal1);
	UPROPERTY(BlueprintAssignable, BlueprintReadWrite, Category = "Future")
	FOnSetResult OnSetResult;

	DECLARE_DELEGATE_OneParam(FOnSetResultStatic, bool);
	FOnSetResultStatic OnSetResultStatic;

	UFUNCTION()
	void Execute(bool RetVal1)
	{
		SILENT_INFO_MSGHN("Got return value for OnClientEntityCreated");
		if (bExecuteAnyway || (FutureContext && FutureContext->IsValidLowLevel()))
			OnSetResultStatic.ExecuteIfBound(RetVal1);
		OnSetResult.Broadcast(RetVal1);
	}

	ThisClass& MakeContext(UObject* context)
	{
		checkf(this, TEXT("Invalid mailbox call awaiting"));
		SetContext(context);
		return *this;
	}

	ThisClass& operator<<(TFunction<void(bool)> lambda)
	{
		OnSetResultStatic.BindLambda(lambda);
		return *this;
	}

	ThisClass& operator>>(TFunction<void(bool)> lambda)
	{
		bExecuteAnyway = true;
		OnSetResultStatic.BindLambda(lambda);
		return *this;
	}

};

UCLASS()
class HALONET_API UBaseAppExtended : public UMailbox
{
	GENERATED_BODY()
public:
	
    RPC_EXEC(OnClientEntityCreated)

    UFUNCTION(CustomThunk, Category = "undefined")
    UBaseAppExtended_OnClientEntityCreated_Future* OnClientEntityCreated(int32 entity_id) 
	REMOTE_CALLER_RETVAL(UBaseAppExtended_OnClientEntityCreated_Future*, OnClientEntityCreated, int32, entity_id);
};

