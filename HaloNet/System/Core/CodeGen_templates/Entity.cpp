#include "{{ENTITY_NAME}}{{CONTEXT_NAME}}Entity.h"
#include "{{PROJECT_NAME}}.h"
{% for fwd_include in FORWARDED_INCLUDES %}
#include "HaloNet/Generated/Entities/{{fwd_include[0]}}/{{fwd_include[1]}}Mailbox.h"
{%- endfor %}
#include "HaloNet/Generated/HaloNetClasses.h"

{% if ENTITY['is_actor_entity'] -%}
{% set ENTITY_CLASS_NAME = "A" + ENTITY_NAME + "_Base" %}
{%- else %}
{% set ENTITY_CLASS_NAME = "U" + ENTITY_NAME + "_Base" %}
{% endif %}

{% if GENERATE_ENTITY and not ENTITY['is_actor_entity'] %}
UWorld* U{{ENTITY_NAME}}_Base::GetWorld() const
{
    auto outer = GetOuter();

	if (outer->IsA<UPackage>())
		return GWorld;

    return outer->GetWorld();
}
{% endif %}

{% for method_name, method_info in METHODS.items() %}
{% if method_info['is_async'] %}
void U{{ENTITY_NAME}}_{{method_name}}_Waiter::ExecuteReturn({{ ", ".join(method_info["returns_list"])}}) REMOTE_RETURNER({{", ".join(method_info['dynamic_delegate_retvals'])}});

U{{ENTITY_NAME}}_{{method_name}}_Waiter::FResult::FResult({{", ".join(method_info["returns_list_result_def"])}})
{
    {% for ret_decl in method_info["returns_list_result_decl"] %}
    {{-ret_decl}};
    {% endfor %}
}
U{{ENTITY_NAME}}_{{method_name}}_Waiter::FResult::FResult(ENoneWaiterResult)
{

}
void U{{ENTITY_NAME}}_{{method_name}}_Waiter::operator=(ThisClass::FResult result)
{
	ExecuteReturn({{", ".join(method_info["returns_list_result_call"])}});
}
{% endif %}
{% endfor %}

{% if GENERATE_ENTITY %}
void {{ENTITY_CLASS_NAME}}::EntitySpawned(FHaloNetServiceClient* Connection)
{
    if ensureMsgf(HaloNet, TEXT("HaloNet is not defined"))
        base = HaloNet->CreateMailbox<{{EXPOSED_CONTEXT_NAME}}Mailbox>(Connection->RemoteAddress, GetEntityID());
    OnEntitySpawned();
};

void {{ENTITY_CLASS_NAME}}::StartEntityDestroy()
{
    OnStartEntityDestroy();
};

{% endif %}