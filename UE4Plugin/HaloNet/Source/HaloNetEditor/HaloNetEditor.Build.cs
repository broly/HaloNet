namespace UnrealBuildTool.Rules
{
	public class HaloNetEditor : ModuleRules
	{
		//public HaloNetEditor (TargetInfo Target) 4.15
		public HaloNetEditor(ReadOnlyTargetRules Target) : base(Target)
		{
			PublicIncludePaths.AddRange(new string[] { "HaloNetEditor/Public" });
			PrivateIncludePaths.AddRange(new string[] { "HaloNetEditor/Private" });
			PublicDependencyModuleNames.AddRange(new string[] {
			    "Core",
			    "CoreUObject",
			    "Engine",
			    "InputCore",
			    "UMG",
			    "Slate",
			    "SlateCore",
			    "HTTP",
			    "RHI",
                "UnrealEd",
			    "HaloNet",
			    "KismetCompiler",
			    "BlueprintGraph",
			    "Kismet",
			    "EditorStyle",
			    "HaloNetEditor",
                "GraphEditor"
            });
			PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });
			DynamicallyLoadedModuleNames.AddRange(new string[] { /* ... add any modules that your module loads dynamically here ... */ });
		}
	}
}