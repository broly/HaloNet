// Fill out your copyright notice in the Description page of Project Settings.
#pragma once

#include "HaloNet.h"
#include "Serialization.h"
#include "TCPClient.h"
#include "Utils.h"
#include "Future.h"
#include "Mailbox.generated.h"

class UHaloNetLibrary;

/**
 * �������� ��������� �������
 * 
 * �������� ���������� � �������� ������� (IP, ����, ID) � ��������� �������� � ��� ����������� RPC
 */
UCLASS(BlueprintType, Blueprintable)
class HALONET_API UMailbox
	: public UObject
	, public FExec
{
	GENERATED_BODY()
	
public:
	UMailbox(const FObjectInitializer& ObjectInitializer);
	
	/**
	 * ���������� ����� � �������� ��������
	 * @param client_conn ��������� � ��������� �������
	 */
	void SetConnection(TSharedPtr<FHaloNetServiceClient> client_conn);

	/**
	 * ��������� ������ �� ������ HaloNet
	 * @param halo_net ������� UHaloNet
	 */
	void SetHaloNet(UHaloNetLibrary* halo_net);

	/**
	 * ����������� ������ � ������ ������ �� ������� � �����������, ����� ���������� �� �� ������ (��������� �����)
	 * @param method_index ������ ������
	 * @param future_id ������������� �������
	 * @param args ��������������� ���������
	 */
	bool MethodCaller(int32 method_index, int32 future_id, TArray<uint8> args) const;

	/**
	 * ��������� ������������ ���������� ���������� ������ �� �����
	 * @param method_name ��� ������
	 * @param Stack ���� ������� ����������� ������ UE4
	 * \RESULT_DECL - ���������� ��������� ���������� ��� �������� � ��������� ����� (@see Script.h)
	 */
	void ExecuteMethodCall(FName method_name, FFrame& Stack, RESULT_DECL);

	/**
	 * ���������� ������������� �������� ��������
	 */
	void SetRemoteID(int32 InID);

	void SetEndpoint(FIPv4Endpoint InEndpoint);

	UFUNCTION(BlueprintPure, Category = "Mailbox")
	bool IsValid() const;

	void OnErrorReceived(FHaloNetServiceClient* client, TArray<uint8> data);

	DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnDisconnected);
	UPROPERTY(BlueprintAssignable, Category = "Mailbox")
	FOnDisconnected OnDisconnected;

	void ForceSendDataToConnection();

public:
	/** ��������� ��������� �������� �������� */
	TSharedPtr<FHaloNetServiceClient> ClientConnection;

	/** ������������� �������� �������� */
	UPROPERTY()
	int32 RemoteID;

	FIPv4Endpoint Endpoint;

	bool bDisconnected;

	/** ������������� ������ �������� ������� �� ������ */
	UPROPERTY()
	TMap<FName, int32> MethodsIndices;

	/** ��������� �� HaloNetLibrary */
	UPROPERTY()
	UHaloNetLibrary* HaloNetLibrary;
};

UCLASS()
class HALONET_API UService_TellPID_Future : public UFuture
{
    GENERATED_BODY()

public:
    DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnSetResult);
    UPROPERTY(BlueprintAssignable, BlueprintReadWrite, Category = "Future")
    FOnSetResult OnSetResult;

    DECLARE_DELEGATE(FOnSetResultStatic);
    FOnSetResultStatic OnSetResultStatic;

    UFUNCTION()
    void Execute();

    ThisClass& MakeContext(UObject* context)
    {
        SetContext(context);
        return *this;
    }

    template<typename T>
    void operator<<(T&& lambda)
    {
        OnSetResultStatic.BindLambda(lambda);
    }

    template<typename T>
    void operator>>(T&& lambda)
    {
        bExecuteAnyway = true;
        OnSetResultStatic.BindLambda(lambda);
    }

};

UCLASS()
class HALONET_API UServiceMailbox
	: public UMailbox
{
	GENERATED_BODY()

public:

	UServiceMailbox(const FObjectInitializer& ObjectInitializer);

	/// Generated methods

	RPC_EXEC(TellPID)
	UFUNCTION(CustomThunk)
	UService_TellPID_Future* TellPID(int32 pid);

};

class FLatentAsyncFunctionAction : public FPendingLatentAction
{
public:
	FName ExecutionFunction;
	int32 OutputLink;
	FWeakObjectPtr CallbackTarget;
	bool bHasDone;

	FLatentAsyncFunctionAction(const FLatentActionInfo& LatentInfo)
		: ExecutionFunction(LatentInfo.ExecutionFunction)
		, OutputLink(LatentInfo.Linkage)
		, CallbackTarget(LatentInfo.CallbackTarget)
		, bHasDone(false)
	{
	}

	void Done()
	{
		bHasDone = true;
	}

	virtual void UpdateOperation(FLatentResponse& Response) override
	{
		Response.FinishAndTriggerIf(bHasDone, ExecutionFunction, OutputLink, CallbackTarget);
	}

#if WITH_EDITOR
	// Returns a human readable description of the latent operation's current state
	virtual FString GetDescription() const override
	{
		return FString::Printf(*NSLOCTEXT("LatentAsyncFunctionAction", "LatentAsyncFunction", "LatentAsyncFunction (%i)").ToString(), bHasDone);
	}
#endif
};