// Fill out your copyright notice in the Description page of Project Settings.

#include "HaloNet.h"
#include "TCPClient.h"
#include "Runtime/Sockets/Public/SocketSubsystem.h"
// #include "SagaLogs.h"
#include "Base64.h"
#include "Utils.h"

int32 FHaloNetServiceClient::ThreadCounter = 0;
TArray<uint8> FHaloNetServiceClient::HELLO_PACKAGE =			{ 0xFF, 'h', 'e', 'l', 'l', 'o', 0xFF, 'p' };
TArray<uint8> FHaloNetServiceClient::HELLO_RESPONSE_PACKAGE =	{ 0x7F, 'h', 'e', 'l', 'l', 'o', 0x7F, 'p' };

#define MAX_READ_SIZE (256 * 1024)


FHaloNetServiceClient::FHaloNetServiceClient(FString in_ip, uint16 in_port, FString in_name)
{
	INFO_MSGHN("NewClient... %s, %s, %i", *in_name, *in_ip, in_port);
	bErrorReceived = false;
	Thread = FRunnableThread::Create(this, *FString::Printf(TEXT("FHaloNetServiceClient_%i"), ThreadCounter++), 0, TPri_BelowNormal);
	ConnectionSocket = nullptr;
	RemoteAddress = IPPort2Endpoint(in_ip, in_port);
	ListenName = in_name;
	IncomingMessagesQueue = MakeShareable(new TQueue<TArray<uint8>, EQueueMode::Mpsc>());
	OutcomingMessagesQueue = MakeShareable(new TQueue<TArray<uint8>, EQueueMode::Mpsc>());
	TickerHandle = FTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateRaw(this, &FHaloNetServiceClient::Tick), 0);
	ReadingBufferTemp.Init(0, MAX_READ_SIZE);
}

FHaloNetServiceClient::FHaloNetServiceClient(FIPv4Endpoint remote_endpoint, FString in_name)
{
	INFO_MSGHN("NewClient... %s, %s", *in_name, *remote_endpoint.ToString());
	bErrorReceived = false;
	Thread = FRunnableThread::Create(this, *FString::Printf(TEXT("FHaloNetServiceClient_%i"), ThreadCounter++), 0, TPri_BelowNormal);
	ConnectionSocket = nullptr;
	RemoteAddress = remote_endpoint;
	ListenName = in_name;
	IncomingMessagesQueue = MakeShareable(new TQueue<TArray<uint8>, EQueueMode::Mpsc>());
	OutcomingMessagesQueue = MakeShareable(new TQueue<TArray<uint8>, EQueueMode::Mpsc>());
	TickerHandle = FTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateRaw(this, &FHaloNetServiceClient::Tick), 0);
	ReadingBufferTemp.Init(0, MAX_READ_SIZE);
}

FHaloNetServiceClient::FHaloNetServiceClient(FIPv4Endpoint remote_endpoint, FString in_name, FSocket* ExistingSocket)
{
	INFO_MSGHN("NewClient existing... %s %s", *in_name, *remote_endpoint.ToString());
	bErrorReceived = false;
	ConnectionSocket = ExistingSocket;
	Thread = FRunnableThread::Create(this, *FString::Printf(TEXT("FHaloNetServiceClient_%i"), ThreadCounter++), 0, TPri_BelowNormal);
	RemoteAddress = remote_endpoint;
	ListenName = in_name;
	IncomingMessagesQueue = MakeShareable(new TQueue<TArray<uint8>, EQueueMode::Mpsc>());
	OutcomingMessagesQueue = MakeShareable(new TQueue<TArray<uint8>, EQueueMode::Mpsc>());
	TickerHandle = FTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateRaw(this, &FHaloNetServiceClient::Tick), 0);
	ReadingBufferTemp.Init(0, MAX_READ_SIZE);
}

FHaloNetServiceClient::~FHaloNetServiceClient()
{
	FTicker::GetCoreTicker().RemoveTicker(TickerHandle);
	if (ConnectionSocket)
		ConnectionSocket->Close();
	delete Thread;
	Thread = nullptr;
}

bool FHaloNetServiceClient::Init()
{
	return true;
}

uint32 FHaloNetServiceClient::Run()
{
	FPlatformProcess::Sleep(0.03);
	SetupSocket(ConnectionSocket);
	FPlatformProcess::Sleep(0.03);


	while (StopTaskCounter.GetValue() == 0)
	{
		TCPConnectionListener();
		FPlatformProcess::Sleep(0.001);
	}
	return 0;
}

void FHaloNetServiceClient::Stop()
{
	StopTaskCounter.Increment();
}

void FHaloNetServiceClient::ForceSendData()
{
	Tick(0.f);
}


bool FHaloNetServiceClient::Tick(float InDeltaTime)
{
	TArray<uint8> out_msg;


	TArray<uint8> OutData;
	if ensure(OutcomingMessagesQueue.IsValid())
		if (ConnectionSocket && OutcomingMessagesQueue->Dequeue(OutData))
		{
			Write(ConnectionSocket, OutData);
		}
	
	while (IncomingMessagesQueue->Dequeue(out_msg))
	{
		//INFO_MSGHN("Msg %s", *Bytes2String(out_msg));
		OnDataReceived.ExecuteIfBound(this, out_msg);
	}

	
	if (bErrorReceived)
	{
		OnErrorReceived.Broadcast(this, {});
		bErrorReceived = false;
	}

	return true;
}

bool FHaloNetServiceClient::Send(const TArray<uint8> data) const
{
	OutcomingMessagesQueue->Enqueue(data);
	// Write(ConnectionSocket, data);
	return bErrorReceived;
}

bool FHaloNetServiceClient::IsConnected() const
{
	return !bErrorReceived; // ConnectionSocket->GetConnectionState() == ESocketConnectionState::SCS_Connected;
}

float FHaloNetServiceClient::Now()
{
	FDateTime nowTime = FDateTime::Now();
	FTimespan time = FTimespan(nowTime.GetDay(), nowTime.GetHour(), nowTime.GetMinute(), nowTime.GetSecond(), nowTime.GetMillisecond());
	return (time.GetTotalMilliseconds() / 1000.0f);
}


bool FHaloNetServiceClient::SetupSocket(FSocket* ExistingSocket)
{

	ConnectionSocket = ExistingSocket ? ExistingSocket : CreateTCPConnection();

	if (!ConnectionSocket)
	{
		// PRINT("StartTCPReceiver>> Listen socket could not be created! ~> %s %d", *RemoteAddress.Address.ToString(), RemoteAddress.Port);
		return false;
	}

	// GetWorld()->GetTimerManager().SetTimer(TCPConnectionHandle, this, &ATestSocket::TCPConnectionListener, 0.01, true);

	LastHandshakeTime = AwaitingPackageTime = Now();

	return true;
}



FSocket* FHaloNetServiceClient::CreateTCPConnection(const int32 ReceiveBufferSize) const
{
	FSocket* Socket = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream, ListenName, false);
	TSharedRef<FInternetAddr> addr = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateInternetAddr();
	addr->SetIp(RemoteAddress.Address.Value);
	addr->SetPort(RemoteAddress.Port);
	ensure(Socket->SetRecvErr(true));
	bool connected = Socket->Connect(*addr);
	PRINTHN("is connected %i", connected);
	return Socket;
}

void FHaloNetServiceClient::TCPConnectionListener()
{
	if (ConnectionSocket != nullptr)
	{
		TArray<TArray<uint8>> ReceivedData = Read(ConnectionSocket);
		for (auto& rec_data : ReceivedData)
		{
			if (rec_data.Num())
			{
				LastHandshakeTime = Now();
				if ensure(IncomingMessagesQueue.IsValid())
					IncomingMessagesQueue->Enqueue(rec_data);
			}
		}
				
		if (ConnectionSocket->GetConnectionState() == ESocketConnectionState::SCS_ConnectionError)
		{
			bErrorReceived = true;

		}

	}


}

FString FHaloNetServiceClient::StringFromBinaryArray(TArray<uint8> BinaryArray) const
{
	BinaryArray.Add(0);
	return FString(ANSI_TO_TCHAR(reinterpret_cast<const char*>(BinaryArray.GetData())));
}

TArray<TArray<uint8>> FHaloNetServiceClient::Read(FSocket* socket)
{
	SCOPE_CYCLE_COUNTER(STAT_Sockets)

	TArray<TArray<uint8>> ReceivedData = {};

	/*
	int32 last_error = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->GetLastErrorCode();

	if (last_error)
	{
		PRINTHN("%i", ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->TranslateErrorCode(last_error));
	}

	bool has_any_data = false;

	while (!has_any_data)
	{
		int32 bytes_read = 0;

		if (StopTaskCounter.GetValue() > 0)
			return {};

		uint32 tmp;
		if (!socket->HasPendingData(tmp))
			continue;

		const bool result = socket->Recv(ReadingBufferTemp.GetData(), MAX_READ_SIZE, bytes_read);
		
		if (!result)
		{
			bErrorReceived = true;
			return {};
		}

		ReadingBuffer.SetNum(ReadingBuffer.Num() + bytes_read);
		FMemory::Memcpy(ReadingBuffer.GetData(), ReadingBufferTemp.GetData(), bytes_read);

		if (ReadingBuffer.Num() > 8)
		{
			uint64 msg_size;
			FMemory::Memcpy(&msg_size, ReadingBuffer.GetData(), 8);
			if (ReadingBuffer.Num() >= msg_size + 8)
			{
				TArray<uint8> message;
				message.Init(0, msg_size);
				FMemory::Memcpy(message.GetData(), ReadingBuffer.GetData() + 8, msg_size);
				int32 old_size = ReadingBuffer.Num();
				int32 new_size = old_size - (msg_size + 8);

				FMemory::Memcpy(ReadingBuffer.GetData(), ReadingBuffer.GetData() + 8 + msg_size, new_size);
				ReadingBuffer.SetNum(new_size);

				PRINTHN("Received data: %s", *Bytes2String(message));
				ReceivedData.Add(message);
				has_any_data = true;
			}
		} else
		{
			PRINTHN("omg");
		}

		if (has_any_data)
			return ReceivedData;

		FPlatformProcess::Sleep(0.2);
	}
	*/
	
	uint32 Size;
	while (socket->HasPendingData(Size) && StopTaskCounter.GetValue() == 0)
	{
		if (Size < 8)
		{
			//FPlatformProcess::Sleep(0.2f);
			continue;
		}

		uint64 msg_size;
		int32 __bytes_read = 0;
		socket->Recv((uint8*)&msg_size, 8, __bytes_read);

		if (__bytes_read < 8)
		{
			//FPlatformProcess::Sleep(0.2f);
			continue;
		}

		TArray<uint8> rec_data_entry;
		rec_data_entry.Init(0, msg_size);
		int32 total_bytes_read = 0;
		int32 __bytes_read2 = 0;

		while (total_bytes_read < msg_size && StopTaskCounter.GetValue() == 0)
		{
			//FPlatformProcess::Sleep(0.2f);
			if (socket->HasPendingData(Size))
			{
				socket->Recv(rec_data_entry.GetData() + total_bytes_read, msg_size - total_bytes_read, __bytes_read2);
				total_bytes_read += __bytes_read2;
			}
		}
		ReceivedData.Add(rec_data_entry);
	}
	return ReceivedData;
}

void FHaloNetServiceClient::Write(FSocket* socket, TArray<uint8> in_data) const
{
	if (!ensure(socket))
		return;
	int32 sent;
	uint64 send_bytes = in_data.Num();
	socket->Send((uint8*)&send_bytes, 8, sent);
	socket->Send(in_data.GetData(), in_data.Num(), sent);
	
}

#if ENABLE_DEBUG_SOCKET
void FHaloNetServiceClient::DumpData(void* ptr, uint64 count)
{
	FString filename = FString::Printf(TEXT("%s/HaloNet/DumpSockets.dat"), *FPaths::ProjectSavedDir());

	TArray<uint8> data;
	data.Init(0, count);
	FMemory::Memcpy(data.GetData(), ptr, count);

	if (!FFileHelper::SaveArrayToFile(data, *filename, &IFileManager::Get(), FILEWRITE_Append))
		ERROR_MSGHN("Failed to save data");
}
#endif