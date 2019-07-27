// Fill out your copyright notice in the Description page of Project Settings.

#include "HaloNet.h"
#include "TCPClient.h"
#include "Runtime/Sockets/Public/SocketSubsystem.h"
// #include "SagaLogs.h"
#include "Base64.h"
#include "Utils.h"
#include "TCPServer.h"

int32 FHaloNetTCPServer::ThreadCounter = 0;

FHaloNetTCPServer::FHaloNetTCPServer(FIPv4Endpoint InEndpoint)
{
	RemoteEndpoint = InEndpoint;
	Thread = FRunnableThread::Create(this, *FString::Printf(TEXT("FHaloNetTCPServer_%i"), ThreadCounter++), 0, TPri_BelowNormal);
	TickerHandle = FTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateRaw(this, &FHaloNetTCPServer::Tick), 0);
	AcceptedSockets = MakeShareable(new TQueue<TSharedPtr<FAddressPair>, EQueueMode::Mpsc>());
}

FHaloNetTCPServer::~FHaloNetTCPServer()
{
	FTicker::GetCoreTicker().RemoveTicker(TickerHandle);
	ListenSocket->Close();
	delete Thread;
}

FSocket* FHaloNetTCPServer::CreateTCPConnectionListener(const FString& SocketName, const int32 ReceiveBufferSize) const
{
	FSocket* listen_socket = FTcpSocketBuilder(*SocketName)
		.AsReusable()
		.BoundToEndpoint(RemoteEndpoint)
		.Listening(8);

	//Set Buffer Size
	int32 NewSize = 0;
	ensure(listen_socket);
	listen_socket->SetReceiveBufferSize(ReceiveBufferSize, NewSize);

	//Done!
	return listen_socket;
}

void FHaloNetTCPServer::TCPConnectionListener()
{
	//~~~~~~~~~~~~~
	if (!ListenSocket) 
		return;
	//~~~~~~~~~~~~~

	//Remote address
	bool Pending;

	// handle incoming connections
	if (ListenSocket->HasPendingConnection(Pending) && Pending)
	{
		TSharedRef<FInternetAddr> RemoteAddress = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateInternetAddr();

		//New Connection receive!
		FSocket* ConnectionSocket = ListenSocket->Accept(*RemoteAddress, TEXT("HaloNet UE4 Dedicated Server connection"));

		if (ConnectionSocket != nullptr)
		{
			FIPv4Endpoint RemoteAddressForConnection = FIPv4Endpoint(RemoteAddress);
			TSharedPtr<FAddressPair> addr_pair = MakeShareable(new FAddressPair());
			addr_pair->endpoint = RemoteAddressForConnection;
			addr_pair->socket = ConnectionSocket;
			// TSharedPtr<FHaloNetServiceClient> connection = MakeShareable(new FHaloNetServiceClient(RemoteAddressForConnection, TEXT("Connected client"), ConnectionSocket));
			AcceptedSockets->Enqueue(addr_pair);
			// AcceptedClientsArray.Add(connection);
		}
	}
}

uint32 FHaloNetTCPServer::Run()
{
	ListenSocket = CreateTCPConnectionListener(TEXT("HaloNetDedicatedServer"));

	if (!ListenSocket)
	{
		UE_LOG(TestLog, Error, TEXT("Unable to create thread, socket is null"));
	}

	while (Stopper.GetValue() == 0)
	{
		TCPConnectionListener();
		FPlatformProcess::Sleep(0.001);
	}

	return true;
}

void FHaloNetTCPServer::Stop()
{
	Stopper.Increment();
}


bool FHaloNetTCPServer::Tick(float InDeltaTime)
{
	TSharedPtr<FAddressPair> pair;
	while (AcceptedSockets->Dequeue(pair))
		OnSocketAccepted.ExecuteIfBound(pair);
	return true;
}
