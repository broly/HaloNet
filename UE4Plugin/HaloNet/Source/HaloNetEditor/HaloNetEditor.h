#pragma once
 
#include "Engine.h"
#include "ModuleManager.h"
#include "TCPServer.h"
#include "UnrealEd.h"

DECLARE_LOG_CATEGORY_EXTERN(HaloNetEditor, All, All);
 
class FHaloNetEditorModule: public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

	TSharedPtr<class FHaloNetEditorServer> HNEditorServer;
};