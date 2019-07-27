namespace UnrealBuildTool.Rules
{
	public class HaloNet : ModuleRules
	{
		//public HaloNet (TargetInfo Target) 4.15
		public HaloNet(ReadOnlyTargetRules Target) : base(Target)
		{
			PublicIncludePaths.AddRange(new string[] { "HaloNet/Public" });
			PrivateIncludePaths.AddRange(new string[] { "HaloNet/Private" });
			PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "Sockets", "Networking", "Json", "JsonUtilities" });
			PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });
			DynamicallyLoadedModuleNames.AddRange(new string[] { /* ... add any modules that your module loads dynamically here ... */ });
		}
	}
}