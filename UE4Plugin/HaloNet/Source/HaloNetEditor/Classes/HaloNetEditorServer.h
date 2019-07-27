#pragma once
 
#include "Engine.h"
#include "ModuleManager.h"
#include "TCPServer.h"
#include "UnrealEd.h"

 
class FHaloNetEditorServer
{
public:
	FHaloNetEditorServer();
	~FHaloNetEditorServer();
 
	void OnNewClient(TSharedPtr<FAddressPair> pair);
	void OnDataReceived(FHaloNetServiceClient* client, TArray<uint8> data);

	TSharedPtr<FHaloNetTCPServer> HNEditorServer;
	TSharedPtr<FHaloNetServiceClient> HNEditorClient;
};