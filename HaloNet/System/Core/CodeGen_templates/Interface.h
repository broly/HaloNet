#pragma once

#include "{{PROJECT_NAME}}.h"
#include "Mailbox.h"
#include "Classes/Future.h"
#include "HaloNet/Generated/HaloNetDataTypes.h"
#include "MethodInfo.h"
#include "Entity.h"
#include "{{ENTITY_NAME}}{{CONTEXT_NAME}}Interface.generated.h"
{% for fwd_type in FORWARDED_TYPES %}
class {{fwd_type}};
{%- endfor %}
UINTERFACE()
class {{PROJECT_API}}_API U{{ENTITY_NAME}}Interface
    : public UInterface
{
    GENERATED_UINTERFACE_BODY()
};

class {{PROJECT_API}}_API I{{ENTITY_NAME}}Interface
    : public IInterface
{
    GENERATED_IINTERFACE_BODY()

public:
    /// Generated methods
    {% for method_name, method_info in METHODS.items() %}
    {% if not method_info['SystemInternal'] -%}
    {% if method_info['is_async'] and method_info['DeferredReturn'] -%}
        {% set add_param = ["class U" + ENTITY_NAME + "_" + method_name + "_Waiter* __waiter__ = nullptr"] %}
    {% else -%}
        {% set add_param = [] %}
    {% endif %}
    {%- if method_info['Docstring'] %}
    /** {% for DSTRING in method_info['Docstring'] %}
     * {{DSTRING}} {% endfor %}
     */ {% endif %}
    UFUNCTION({% if method_info['BlueprintNativeEvent'] %}BlueprintNativeEvent{% endif %}{% if method_info['BlueprintImplementableEvent'] %}BlueprintImplementableEvent{% endif %})
    {% if not method_info['BlueprintNativeEvent'] and not method_info['BlueprintImplementableEvent'] %}virtual {% endif %}{% if not method_info['DeferredReturn'] and method_info['delegate_retvals']|count > 0 %}{{method_info['delegate_retvals'][0]}}{% else %}void{% endif %} {{method_name}}({{", ".join(method_info['signature_params_list'] + add_param)}}){% if not method_info['BlueprintNativeEvent'] and not method_info['BlueprintImplementableEvent'] %} = 0 {% endif %};
    {% endif -%}
    {% endfor %}

    static TMap<int32, FClientMethodMetadata> GetDefaultMethodsList();

};