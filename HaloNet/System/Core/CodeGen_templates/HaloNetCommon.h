#pragma once

#include "{{PROJECT_NAME}}.h"
#include "MethodInfo.h"
#include "HaloNetDataTypes.h"
#include "HaloNetLibrary.h"
#include "HaloNetCommon.generated.h"

USTRUCT(BlueprintType)
struct FBaseAppStorages
{
    GENERATED_BODY()

public:
    {% for storage_name, storage_type_name, is_available, storage_keys in STORAGES %}{% if is_available %}
    UPROPERTY(BlueprintReadOnly, Category = "HN Storages")
    TArray<{{storage_type_name}}> {{storage_name}};
    {% endif %}{% endfor %}
};


UCLASS()
class UBaseAppStoragesAPI : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    {% for storage_name, storage_type_name, is_available, storage_keys in STORAGES %}{% if is_available %}
    {% for sk, st in storage_keys.items() %}
    /** Returns the storage entry by key {{sk}} from {{storage_type_name}} */
    UFUNCTION(BlueprintPure, Category = "Generated Storages API", meta = (DisplayName = "{{storage_name}}.GetBy({{sk}})"))
    static {{storage_type_name}} {{storage_name}}_GetBy_{{sk}}(const TArray<{{storage_type_name}}>& storage, {{st.__name__}} {{sk}}, bool& found)
    {
        const {{storage_type_name}}* found_data = storage.FindByPredicate([{{sk}}](const {{storage_type_name}}& entry)
	    {
		    return {{sk}} == entry.{{sk}};
	    });
		found = found_data != nullptr;
		return found ? *found_data : {{storage_type_name}}();
    }
    {% endfor %}
    {% endif %}{% endfor %}
};

{#
template<char const* name, typename TStorageEntry, typename TKey>
struct TStorageGetter
{
};

{% for storage_name, storage_type_name, is_available, storage_keys in STORAGES %}{% if is_available %}
{% for sk, st in storage_keys.items() %}
char {{storage_name}}_{{sk}}[] = "{{sk}}";
template<>
struct TStorageGetter<{{storage_name}}_{{sk}}, {{storage_type_name}}, {{st.__name__}}>
{
    static {{storage_type_name}}* Get(TArray<{{storage_type_name}}> InArray, {{st.__name__}} key)
    {
        for (int32 index = 0; index < InArray.Num(); index++)
        {
            if (InArray[index].{{sk}} == key)
            {
                return &InArray[index];
            }
        }
        return nullptr;
    }
};
{% endfor %}
{% endif %}{% endfor %}
#}



class {{PROJECT_API}}_API FHaloNetCommon : public IHaloNetCommon
{
public:
    virtual TMap<FString, FString>& GetClientEntitiesMapping() override;

	virtual TSet<FName>& GetExecCapableClasses() override;

	virtual const FString& GetGeneratorSignature() const override;

	virtual TArray<FStorageInfo> GetStorageStructTypes() override;


    FHaloNetCommon();
public:

    TSharedPtr<TMap<FString, FString>> ClientEntitiesMapping;
    TSharedPtr<TSet<FName>> ExecCapableClasses;


	FString GeneratorSignature;

    void Initialize();

    bool IsInitialized() const;

    bool bIsInitialized;
};

class {{PROJECT_API}}_API FHaloNetCommonInitializer
{
public:
    FHaloNetCommonInitializer()
    {
        IHaloNetCommon::SetInstance(MakeShareable(new FHaloNetCommon()));
    }

    static TSharedRef<FHaloNetCommonInitializer> Instance;
};