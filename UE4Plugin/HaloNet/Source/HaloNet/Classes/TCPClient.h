// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "HaloNet.h"
#include "GameFramework/Actor.h"
#include "Networking.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
//#include "Messaging.h"

#define HANDSHAKE_CHECKING_ENABLED 0
#define HANDSHAKE_CHECKING_TIME 5.f
#define HANDSHAKE_CHECKING_TIME_ERROR 10.f

#define ENABLE_DEBUG_SOCKET 0

DECLARE_STATS_GROUP(TEXT("HaloNet"), STATGROUP_HaloNet, STATCAT_Advanced);
DECLARE_CYCLE_STAT(TEXT("HaloNet ~ Sockets"), STAT_Sockets, STATGROUP_HaloNet);

struct FAddressPair
{
	FIPv4Endpoint endpoint;
	FSocket* socket;
};



class HALONET_API FHaloNetServiceClient
	: public FRunnable
{
public:
	FHaloNetServiceClient(FString in_ip, uint16 in_port, FString in_name);
	FHaloNetServiceClient(FIPv4Endpoint remote_endpoint, FString in_name);
	FHaloNetServiceClient(FIPv4Endpoint remote_endpoint, FString in_name, FSocket* ExistingSocket);
	~FHaloNetServiceClient();

public:  // Thread info

	/** This thread */
	FRunnableThread* Thread;

	/** Stop flag */
	FThreadSafeCounter StopTaskCounter;

	/** Error received */
	FThreadSafeBool bErrorReceived;

	// Begin FRunnable interface.
	virtual bool Init() override;
	virtual uint32 Run() override;
	virtual void Stop() override;
	// End FRunnable interface

	/// FIX IT IF USING HTML5
	virtual FSingleThreadRunnable* GetSingleThreadInterface() override { return nullptr; }

	void ForceSendData();

public:  // Sockets info

	FSocket* ConnectionSocket;
	FIPv4Endpoint RemoteAddress;
	FString ListenName;

	TArray<uint8> ReadingBuffer;
	TArray<uint8> ReadingBufferTemp;
	
	/**
	 * Setups listener...
	 */
	bool SetupSocket(FSocket* ExistingSocket = nullptr);

	/**
	 * Creates listener...
	 */
	FSocket* CreateTCPConnection(const int32 receive_buffer_size = 2 * 1024 * 1024) const;

	/**
	 * Connection events...
	 */
	void TCPConnectionListener(); 	//can thread this eventually

	FString StringFromBinaryArray(TArray<uint8> BinaryArray) const;
	
	bool Tick(float InDeltaTime);

	FDelegateHandle TickerHandle;

	DECLARE_DELEGATE_TwoParams(FOnDataReceived, FHaloNetServiceClient*, TArray<uint8>)
	FOnDataReceived OnDataReceived;

	DECLARE_MULTICAST_DELEGATE_TwoParams(FOnErrorReceived, FHaloNetServiceClient*, TArray<uint8>)
	FOnErrorReceived OnErrorReceived;

	TSharedPtr<TQueue<TArray<uint8>, EQueueMode::Mpsc>, ESPMode::ThreadSafe> IncomingMessagesQueue;
	mutable TSharedPtr<TQueue<TArray<uint8>, EQueueMode::Mpsc>, ESPMode::ThreadSafe> OutcomingMessagesQueue;


	bool Send(const TArray<uint8> data) const;

	bool IsConnected() const;

	double LastHandshakeTime;

	double AwaitingPackageTime;

	static int32 ThreadCounter;

	static TArray<uint8> HELLO_PACKAGE;
	static TArray<uint8> HELLO_RESPONSE_PACKAGE;

	static float Now();
	
	/**
	 * Reads pending data from specified socket
	 */
	TArray<TArray<uint8>> Read(FSocket* socket);

	/**
	 * Sends data to socket
	 */
	void Write(FSocket* socket, TArray<uint8> in_data) const;


#if ENABLE_DEBUG_SOCKET
	static void DumpData(void* ptr, uint64 count);
#endif
};

