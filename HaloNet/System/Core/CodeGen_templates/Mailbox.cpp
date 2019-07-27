#include "{{ENTITY_NAME}}{{CONTEXT_NAME}}Mailbox.h"
#include "{{PROJECT_NAME}}.h"
{% for fwd_include in FORWARDED_INCLUDES %}
#include "HaloNet/Generated/Entities/{{fwd_include[0]}}/{{fwd_include[1]}}Mailbox.h"
{%- endfor %}

{% for method_name, method_info in METHODS.items() %} {% if method_info['is_async'] %}
void U{{ENTITY_FULLNAME}}_{{method_name}}_Future::Execute({{ ", ".join(method_info["returns_list"])}})
{
    SILENT_INFO_MSGHN("Got return value for {{method_name}}");
    if (bExecuteAnyway || (FutureContext && FutureContext->IsValidLowLevel()))
        OnSetResultStatic.ExecuteIfBound({{ ", ".join(method_info["ret_names"])}});
    OnSetResult.Broadcast({{ ", ".join(method_info["ret_names"])}});
}
{% endif %} {% endfor %}


U{{ENTITY_FULLNAME}}Mailbox::U{{ENTITY_FULLNAME}}Mailbox(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    {% for method_name, method_info in METHODS.items() -%}
    MethodsIndices.Add(TEXT("{{method_name}}"), {{method_info['ID']}});
    {% endfor %}
}

{% for method_name, method_info in METHODS.items() %}
{% if method_info['is_async'] %}U{{ENTITY_FULLNAME}}_{{method_name}}_Future*{% else %}void{% endif %} U{{ENTITY_FULLNAME}}Mailbox::{{method_name}}({{", ".join(method_info['params_list'])}}) {% if method_info['is_async'] %}REMOTE_CALLER_RETVAL(U{{ENTITY_FULLNAME}}_{{method_name}}_Future*, {{method_name}}{{"".join(method_info['params_commas'])}}){% else %}REMOTE_CALLER({{method_name}}{{"".join(method_info['params_commas'])}}){% endif %};
{% endfor %}

{% if LATENT_SUPPORTED %}
// Latent functions section
{% for method_name, method_info in METHODS.items() %}{% if method_info['Latent'] %}
void U{{ENTITY_FULLNAME}}Mailbox::internal_{{method_name}}(UObject* WorldContextObject, U{{ENTITY_FULLNAME}}Mailbox* Target, {{", ".join(method_info['params_list'])}}, U{{ENTITY_FULLNAME}}Mailbox::FOnLatentSetResult_{{method_name}} OnDone, FLatentActionInfo LatentInfo)
{
    if (UWorld* World = GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::LogAndReturnNull))
	{
		FLatentActionManager& LatentManager = World->GetLatentActionManager();
		if (LatentManager.FindExistingAction<FLatentAsyncFunctionAction>(LatentInfo.CallbackTarget, LatentInfo.UUID) == nullptr)
		{
			FLatentAsyncFunctionAction* NewAction = new FLatentAsyncFunctionAction(LatentInfo);
			LatentManager.AddNewAction(LatentInfo.CallbackTarget, LatentInfo.UUID, NewAction);
			if (auto future = Target->{{method_name}}({{ ", ".join(method_info['params_names']) }}))
			{
				future->MakeContext(WorldContextObject) << [=, &LatentInfo]({{ ", ".join(method_info['returns_list']) }})
				{
					OnDone.ExecuteIfBound({{ ", ".join(method_info['ret_names']) }});
					NewAction->Done();
				};
			}
		}
	}
}
{%- endif %}{% endfor %}
// end of latent functions section
{% endif %}