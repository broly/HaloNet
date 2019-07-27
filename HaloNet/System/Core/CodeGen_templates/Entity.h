#pragma once

#include "{{PROJECT_NAME}}.h"
#include "Mailbox.h"
#include "Classes/Future.h"
#include "Classes/HaloNetLibrary.h"
#include "HaloNet/Generated/HaloNetDataTypes.h"
{% if GENERATE_ENTITY %}
#include "{{ENTITY_NAME}}{{CONTEXT_NAME}}Interface.h"
{% endif %}
#include "HaloNet/HNDependencies.h"
#include "{{ENTITY_NAME}}{{CONTEXT_NAME}}Entity.generated.h"
{% for fwd_type in FORWARDED_TYPES %}
class {{fwd_type}};
{%- endfor %}
{% for method_name, method_info in METHODS.items() %}
{% if method_info['is_async']  %} {# and method_info['DeferredReturn'] #}
UCLASS()
class U{{ENTITY_NAME}}_{{method_name}}_Waiter : public UWaiter
{
    GENERATED_BODY()

public:
    RET_EXEC(ExecuteReturn);
    /**
     * Returns the values for remote service
     */
    UFUNCTION(CustomThunk)
    void ExecuteReturn({{ ", ".join(method_info["returns_list"])}});

    /**
     * Helper definition for result sending
     */
    struct FResult
    {
        FResult({{", ".join(method_info["returns_list_result_def"])}});
		FResult(ENoneWaiterResult);

        {% for ret_def in method_info["returns_list"] %}
        {{-ret_def}};
        {% endfor %}
    };

    ThisClass& __derefer() { return *this; };

	void operator=(FResult result);

};
{% endif %}
{% endfor %}

{% if GENERATE_ENTITY %}

UCLASS()
{% if ENTITY['is_actor_entity'] %}class A{{ENTITY_NAME}}_Base{% else %}class U{{ENTITY_NAME}}_Base{% endif %}
    : public {{BASE_CLASS}}
    , public IEntityInterface
    , public I{{ENTITY_NAME}}Interface
{
    GENERATED_BODY()

public:
    typedef class U{{ENTITY_NAME}}{{EXPOSED_CONTEXT_NAME}}Mailbox {{EXPOSED_CONTEXT_NAME}}Mailbox;
    typedef class U{{ENTITY_NAME}}{{CONTEXT_NAME}}Mailbox {{CONTEXT_NAME}}Mailbox;

    {% if not ENTITY['is_actor_entity'] %}virtual UWorld* GetWorld() const override; {% endif %}

    // BEGIN IEntityInterface
    virtual int32 GetEntityID() override { return EntityID; }
    virtual void SetHaloNet(UHaloNetLibrary* InHN) override { HaloNet = InHN; };
	virtual void SetEntityID(int32 entity_id) override { EntityID = entity_id; }
    virtual TMap<int32, FClientMethodMetadata> GetMethodsList() override { return I{{ENTITY_NAME}}Interface::GetDefaultMethodsList(); }
    virtual void EntitySpawned(FHaloNetServiceClient* Connection) override;
    virtual void StartEntityDestroy() override;
	virtual void SetGameInstance(UGameInstance* InGameInstance) override { GameInstance = InGameInstance; };
    // END IEntityInterface

    UFUNCTION(BlueprintNativeEvent, Category = "HaloNet")
    void OnEntitySpawned();
    virtual void OnEntitySpawned_Implementation() {};

    UFUNCTION(BlueprintNativeEvent, Category = "HaloNet")
    void OnStartEntityDestroy();
    virtual void OnStartEntityDestroy_Implementation() {};

    // BEGIN I{{ENTITY_NAME}}Interface
    {%- for method_name, method_info in METHODS.items() %}
    {% if method_info['is_async'] and method_info['DeferredReturn'] -%}
        {% set add_param = ["class U" + ENTITY_NAME + "_" + method_name + "_Waiter* __waiter__ = nullptr"] %}
    {% else -%}
        {% set add_param = [] %}
    {% endif %}
    {%- if method_info['Docstring'] %}
    /** {% for DSTRING in method_info['Docstring'] %}
     * {{DSTRING}} {% endfor %}
     */ {% endif %}
    {% if method_info['BlueprintImplementableEvent'] %}
    // [{{method_name}}] ImplementableEvents has no middle overrides
    {% elif method_info['BlueprintNativeEvent'] %}
    virtual {% if not method_info['DeferredReturn'] and method_info['delegate_retvals']|count > 0 %}{{method_info['delegate_retvals'][0]}}{% else %}void{% endif %} {{method_name}}_Implementation({{", ".join(method_info['signature_params_list'] + add_param)}}) override PURE_VIRTUAL({{method_name}}, );
    {% else %}
    UFUNCTION()
    virtual {% if not method_info['DeferredReturn'] and method_info['delegate_retvals']|count > 0 %}{{method_info['delegate_retvals'][0]}}{% else %}void{% endif %} {{method_name}}({{", ".join(method_info['signature_params_list'] + add_param)}}) override PURE_VIRTUAL({{method_name}}, );
    {% endif %}
    {% endfor -%}
    // END I{{ENTITY_NAME}}Interface

    // BEGIN properties
    {%- for property_name, property_info in PROPERTIES.items() %}
    /** The {{ property_name }} (Replicated from BaseApp) */
	UPROPERTY(BlueprintReadOnly, Category = "HaloNet Properties")
	{{property_info['Type']}} {{property_name}};
	{% endfor %}// END properties

	// BEGIN replication notifiers
	{%- for property_name, property_info in PROPERTIES.items() %}
	/** Replication notifier for base {{ENTITY_NAME}} variable '{{ property_name }}' */
	UFUNCTION(BlueprintNativeEvent, Category = "HaloNet Properties")
	void OnBaseRep_{{property_name}}();
	virtual void OnBaseRep_{{property_name}}_Implementation() {};
	{% if property_info['PartialRep'] %} {% if 'TMap' in property_info['Type'] %}
	UFUNCTION(BlueprintNativeEvent, Category = "HaloNet Properties")
	void OnBaseSliceRep_{{property_name}}_Add({{property_info['Generic']['KT']}} Key, {{property_info['Generic']['KV']}} Value, bool bHasOldValue, {{property_info['Generic']['KV']}} OldValue);
	virtual void OnBaseSliceRep_{{property_name}}_Add_Implementation({{property_info['Generic']['KT']}} Key, {{property_info['Generic']['KV']}} Value, bool bHasOldValue, {{property_info['Generic']['KV']}} OldValue) {};

	UFUNCTION(BlueprintNativeEvent, Category = "HaloNet Properties")
	void OnBaseSliceRep_{{property_name}}_Remove({{property_info['Generic']['KT']}} Key, {{property_info['Generic']['KV']}} OldValue);
	virtual void OnBaseSliceRep_{{property_name}}_Remove_Implementation({{property_info['Generic']['KT']}} Key, {{property_info['Generic']['KV']}} OldValue) {};
	{% endif %} {% endif %}
	{% endfor %}// END replication notifiers
public:
    UPROPERTY()
    int32 EntityID;

    UPROPERTY(BlueprintReadOnly, Category = "HaloNet")
    U{{ENTITY_NAME}}{{EXPOSED_CONTEXT_NAME}}Mailbox* base;

    UPROPERTY(BlueprintReadOnly, Category = "HaloNet")
    UGameInstance* GameInstance;

protected:
    UHaloNetLibrary* HaloNet;
};

{% endif %}