#pragma once

#include "HaloNet.h"
#include "Engine.h"
#include "Sockets.h"
#include "Networking.h"
#include "TCPClient.h"
#include "Utils.h"
#include "Future.generated.h"

class UHaloNetLibrary;

UCLASS(BlueprintType)
class HALONET_API UWaiter : public UObject
{
	GENERATED_BODY()

public:
	/** 
	 * ��������� ID �������
	 * @see FutureID
	 */
	void SetID(int32 InID);

	/** 
	 * ���������� ID ������� 
	 * @see FutureID
	 */
	int32 GetID() const;

	void SetMethodIndex(int32 InMethodIndex);

	void SetEntityID(int32 InEntityID);;

	void SetHaloNet(UHaloNetLibrary* InHaloNet);

	void SetOwnerObject(UObject* InOwnerObject);

	void SetConnection(FHaloNetServiceClient* Conn);

	void ProcessExecuteReturn(UFunction* func, FFrame& Stack);

	void SendSerializedData(TArray<uint8> bytes);

	FHaloNetServiceClient* GetConnection() const;


protected:
	/** ������������� ��������, ������������ ������� ������ ��� ������������� � ����������� */
	UPROPERTY()
	int32 WaiterID;

	UPROPERTY()
	int32 EntityID;

	UPROPERTY()
	int32 MethodIndex;

	UPROPERTY()
	UHaloNetLibrary* HaloNet;

	UPROPERTY()
	UObject* OwnerObject; 

	FHaloNetServiceClient* RemoteConnection;
};

/**
 * �������
 * 
 * �������� ����������� ������ ��������� ������
 * ����� �������� ����� ����� ��������, ������� ��������� ���� ��������
 * 
 * �� ����������� �������� ���� �����. �� ��������� ��� ����������� � ��������� ����
 */
UCLASS(BlueprintType)
class HALONET_API UFuture : public UObject
{
	GENERATED_BODY()

public:
	UFuture(const FObjectInitializer& ObjectInitializer);

	/** 
	 * ��������� ID ��������
	 * @see FutureID
	 */
	void SetID(int32 InID);

	/** 
	 * ���������� ID �������� 
	 * @see FutureID
	 */
	int32 GetID() const;

	/** 
	 * ������������� ��������� ���������� ��������� ������. 
	 * ��������� ������� 
	 * @param return_values ������������ �������� ��������� ������ � ���� ��������� �������
	 */
	void SetResult(const TArray<uint8>& return_values);

	/**
	 * ������������� ��������
	 * @see FutureContext
	 */
	void SetContext(UObject* context);

	void Fail(const FString& error);

	void operator>(TFunction<void(const FString&)> func)
	{
		OnErrorReceivedStatic.BindLambda(func);
	}

	void OnErrorReceivedFunc(FHaloNetServiceClient* client, TArray<uint8> data)
	{
		if (bIsDone)
			Fail(TEXT("Disconnected"));
	}



protected:
	/** ������������� ��������, ������������ ������� ������ ��� ������������� � ����������� */
	UPROPERTY()
	int32 FutureID;

	/** ������� ������������� �������� */
	UPROPERTY()
	bool bIsDone;

	/** ���� � ���������������� ���������� ������ �������� (���� ���� �������� ����������) */
	UPROPERTY()
	bool bExecuteAnyway;
	
	/** �������� �������� ��������, ��������� ��� ������������. ���� ���� �������� ����������, ������, ������� ���� ���������, ������� �� ����� */
	UPROPERTY()
	UObject* FutureContext;
	
	DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnErrorReceived, const FString&, error_message);
    UPROPERTY(BlueprintAssignable, BlueprintReadWrite, Category = "Future")
    FOnErrorReceived OnErrorReceived;

    DECLARE_DELEGATE_OneParam(FOnErrorReceivedStatic, const FString&);
    FOnErrorReceivedStatic OnErrorReceivedStatic;
};

UCLASS(BlueprintType)
class HALONET_API UEmptyWaiter : public UWaiter
{
    GENERATED_BODY()

public:
    RET_EXEC(ExecuteReturn);
    /**
     * Returns the values for remote service
     */
    UFUNCTION(CustomThunk)
    void ExecuteReturn()
	REMOTE_RETURNER();

    /**
     * Helper definition for result sending
     */
    struct FResult
    {
        FResult() {}
		FResult(ENoneWaiterResult) {}
        
    };

    ThisClass& __derefer() { return *this; };

	void operator=(FResult result) { ExecuteReturn(); }

};
