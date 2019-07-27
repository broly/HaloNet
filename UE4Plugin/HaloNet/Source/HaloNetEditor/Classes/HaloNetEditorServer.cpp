#include "HaloNetEditor.h"
#include "HaloNet/Classes/Utils.h"
#include "HaloNet/Classes/Serialization.h"
#include "HaloNetEditorServer.h"
#include "AssetEditorManager.h"
#include "SNotificationList.h"
#include "NotificationManager.h"

 
FHaloNetEditorServer::FHaloNetEditorServer()
{
	auto server_endpoint = IPPort2Endpoint(TEXT("127.0.0.1"), 6666);
	HNEditorServer = MakeShareable(new FHaloNetTCPServer(server_endpoint));
	HNEditorServer->OnSocketAccepted.BindRaw(this, &FHaloNetEditorServer::OnNewClient);
}

FHaloNetEditorServer::~FHaloNetEditorServer()
{
	
}
 
void FHaloNetEditorServer::OnNewClient(TSharedPtr<FAddressPair> pair)
{
	HNEditorClient = MakeShareable(new FHaloNetServiceClient(pair->endpoint, TEXT("Editor client"), pair->socket));
	HNEditorClient->OnDataReceived.BindRaw(this, &FHaloNetEditorServer::OnDataReceived);
}

void FHaloNetEditorServer::OnDataReceived(FHaloNetServiceClient* client, TArray<uint8> data)
{
	auto dproxy = FBinarySerializationProxy(data);

	FString command;

	
	if (ensure(dproxy >> command) && command == TEXT("open_asset"))
	{
		FString asset_path;
		if ensure (dproxy >> asset_path)
		{
			UObject* asset = LoadObject<UObject>(nullptr, *asset_path);
			if (asset)
			{
				TArray<FString> Assets = { asset_path };
				FAssetEditorManager::Get().OpenEditorsForAssets(Assets);
			}
			else
			{
				FNotificationInfo Info(FText::Format(NSLOCTEXT("HNEditor", "AssetNotFound", "Asset '{0}' not found"), FText::FromString(asset_path)));
				Info.Image = FEditorStyle::GetBrush(TEXT("MessageLog.Warning"));
				Info.FadeInDuration = 0.1f;
				Info.FadeOutDuration = 0.5f;
				Info.ExpireDuration = 1.5f;
				Info.bUseThrobber = false;
				Info.bUseSuccessFailIcons = true;
				Info.bUseLargeFont = true;
				Info.bFireAndForget = false;
				Info.bAllowThrottleWhenFrameRateIsLow = false;
				auto NotificationItem = FSlateNotificationManager::Get().AddNotification(Info);
				NotificationItem->SetCompletionState(SNotificationItem::CS_Fail);
				NotificationItem->ExpireAndFadeout();

				auto CompileFailSound = LoadObject<USoundBase>(nullptr, TEXT("/Engine/EditorSounds/Notifications/CompileFailed_Cue.CompileFailed_Cue"));
				GEditor->PlayEditorSound(CompileFailSound);
			}
		}
	}
}

