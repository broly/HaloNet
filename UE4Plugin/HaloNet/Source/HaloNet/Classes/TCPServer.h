// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "HaloNet.h"
#include "GameFramework/Actor.h"
#include "Networking.h"
#include "Sockets.h"
#include "TCPClient.h"
#include "SocketSubsystem.h"
//#include "Messaging.h"

constexpr int32 GTCPServerBufferSize = 2 * 1024 * 1024;


class HALONET_API FHaloNetTCPServer
	: public FRunnable
{
public:
	FHaloNetTCPServer(FIPv4Endpoint InEndpoint);
	~FHaloNetTCPServer();
	
	FSocket* CreateTCPConnectionListener(const FString& SocketName, const int32 ReceiveBufferSize = GTCPServerBufferSize) const;

	void TCPConnectionListener();

	virtual uint32 Run() override;
	virtual void Stop() override;

	bool Tick(float InDeltaTime);

	FSocket* ListenSocket;

	/** This thread */
	FRunnableThread* Thread;
	
	FIPv4Endpoint RemoteEndpoint;
	
	TSharedPtr<TQueue<TSharedPtr<FAddressPair>, EQueueMode::Mpsc>, ESPMode::ThreadSafe> AcceptedSockets;

	/** Stop flag */
	FThreadSafeCounter Stopper;

	FDelegateHandle TickerHandle;

	DECLARE_DELEGATE_OneParam(FOnSocketAccepted, TSharedPtr<FAddressPair>)
	FOnSocketAccepted OnSocketAccepted;

	TArray<TSharedPtr<FHaloNetServiceClient>> AcceptedClientsArray;

	static int32 ThreadCounter;
};

