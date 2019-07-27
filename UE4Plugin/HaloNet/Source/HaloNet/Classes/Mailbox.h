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
 * Мейлбокс удалённого объекта
 * 
 * Содержит информацию о удалённом объекте (IP, порт, ID) и позволяет общаться с ним посредством RPC
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
	 * Установить связь с удалённым сервисом
	 * @param client_conn коннекшин к удалённому сервису
	 */
	void SetConnection(TSharedPtr<FHaloNetServiceClient> client_conn);

	/**
	 * Установка ссылки на объект HaloNet
	 * @param halo_net инстанс UHaloNet
	 */
	void SetHaloNet(UHaloNetLibrary* halo_net);

	/**
	 * Сериализует данные о вызове метода по индексу и аргументами, затем отправляет их на сервер (утверждая вызов)
	 * @param method_index индекс метода
	 * @param future_id идентификатор фьючеры
	 * @param args сериализованные аргументы
	 */
	bool MethodCaller(int32 method_index, int32 future_id, TArray<uint8> args) const;

	/**
	 * Выполняет сериализацию аргументов вызванного метода по имени
	 * @param method_name имя метода
	 * @param Stack стек вызовов виртуальной машины UE4
	 * \RESULT_DECL - объявление аргумента результата как делается в генерации когда (@see Script.h)
	 */
	void ExecuteMethodCall(FName method_name, FFrame& Stack, RESULT_DECL);

	/**
	 * Установить идентификатор удалённой сущности
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
	/** Коннекшин мейлбокса удалённой сущности */
	TSharedPtr<FHaloNetServiceClient> ClientConnection;

	/** Идентификатор удлаённой сущности */
	UPROPERTY()
	int32 RemoteID;

	FIPv4Endpoint Endpoint;

	bool bDisconnected;

	/** Ассоциативный массив индексов методов по именам */
	UPROPERTY()
	TMap<FName, int32> MethodsIndices;

	/** Указатель на HaloNetLibrary */
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