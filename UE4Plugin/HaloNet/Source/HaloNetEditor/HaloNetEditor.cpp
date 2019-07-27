#include "HaloNetEditor.h"

IMPLEMENT_GAME_MODULE(FHaloNetEditorModule, HaloNetEditor);

DEFINE_LOG_CATEGORY(HaloNetEditor)
 
#define LOCTEXT_NAMESPACE "HaloNetEditor"
 
void FHaloNetEditorModule::StartupModule()
{
	UE_LOG(HaloNetEditor, Warning, TEXT("HaloNetEditor: Log Started"));

	HNEditorServer = MakeShareable(new FHaloNetEditorServer());
}
 
void FHaloNetEditorModule::ShutdownModule()
{
	UE_LOG(HaloNetEditor, Warning, TEXT("HaloNetEditor: Log Ended"));
}

#undef LOCTEXT_NAMESPACE
