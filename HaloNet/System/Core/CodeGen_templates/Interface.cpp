#include "{{ENTITY_NAME}}{{CONTEXT_NAME}}Interface.h"
#include "{{PROJECT_NAME}}.h"
#include "{{ENTITY_NAME}}{{CONTEXT_NAME}}Entity.h"
{% for fwd_include in FORWARDED_INCLUDES %}
#include "HaloNet/Generated/Entities/{{fwd_include[0]}}/{{fwd_include[1]}}Mailbox.h"
{%- endfor %}

U{{ENTITY_NAME}}Interface::U{{ENTITY_NAME}}Interface(const FObjectInitializer& ObjectInitializer)
{

}

TMap<int32, FClientMethodMetadata> I{{ENTITY_NAME}}Interface::GetDefaultMethodsList()
{
    TMap<int32, FClientMethodMetadata> ret_val;
    {% for method_name, method_info in METHODS.items() -%}
	ret_val.Add({{method_info['ID']}},
	    FClientMethodMetadata({{method_info['ID']}},
	                          "{{method_name}}",
	                          {% if method_info['is_async'] %}true{% else %}false{% endif %},
	                          {% if method_info['is_async'] %}U{{ENTITY_NAME}}_{{method_name}}_Waiter::StaticClass(){% else %}nullptr{% endif %},
	                          {% if method_info['DeferredReturn'] %}true{% else %}false{% endif %},
	                          {% if method_info['SystemInternal'] %}true{% else %}false{% endif %}
	    ));
    {% endfor %}
	return ret_val;
}