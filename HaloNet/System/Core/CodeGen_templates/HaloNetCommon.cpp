#include "HaloNetCommon.h"
#include "{{PROJECT_NAME}}.h"


TMap<FString, FString>& FHaloNetCommon::GetClientEntitiesMapping()
{
    return *ClientEntitiesMapping;
}

TSet<FName>& FHaloNetCommon::GetExecCapableClasses()
{
	return *ExecCapableClasses;
}

bool FHaloNetCommon::IsInitialized() const
{
    return bIsInitialized;
}

FHaloNetCommon::FHaloNetCommon()
    : bIsInitialized(false)
{
    Initialize();
}

const FString& FHaloNetCommon::GetGeneratorSignature() const
{
	return GeneratorSignature;
}

void FHaloNetCommon::Initialize()
{
    ClientEntitiesMapping = MakeShareable(new TMap<FString, FString>());
    ExecCapableClasses = MakeShareable(new TSet<FName>());
    {% for class_name, using_class in CLIENT_CLASSES_MAPPING.items() %}
    ClientEntitiesMapping->Add(TEXT("{{class_name}}"), TEXT("{{using_class}}"));
    {%- endfor %}

    {% for class_name in EXEC_CAPABLE_CLASSES %}
    ExecCapableClasses->Add("{{class_name}}Mailbox");
    {%- endfor %}
    GeneratorSignature = TEXT("{{GENERATOR_SIGNATURE}}");
    bIsInitialized = true;
}

TArray<FStorageInfo> FHaloNetCommon::GetStorageStructTypes()
{
	TArray<FStorageInfo> storage_structs;
	{% for storage_name, storage_type_name, is_available, storage_keys in STORAGES %}{% if is_available %}storage_structs.Add(FStorageInfo(TEXT("{{storage_name}}"), {{storage_type_name}}::StaticStruct()));
	{% endif %}{% endfor %}
	return storage_structs;
}

TSharedRef<FHaloNetCommonInitializer> FHaloNetCommonInitializer::Instance = MakeShareable(new FHaloNetCommonInitializer());