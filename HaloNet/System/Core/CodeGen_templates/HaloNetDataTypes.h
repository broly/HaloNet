#pragma once

#include "{{PROJECT_NAME}}.h"
#include "HaloNet/HNDependencies.h"

#include "Classes/Serialization.h"
#include "HaloNetDataTypes.generated.h"

{% for TYPENAME, TYPEDATA in TYPES.items() -%}
{%- if TYPEDATA['Kind'] == "Enum" and not TYPEDATA['IsLocal'] %}
{%- if TYPEDATA['Docstring'] %}
/** {% for DSTRING in TYPEDATA['Docstring'] %}
 * {{DSTRING}} {% endfor %}
 */ {% endif %}
UENUM({{ ", ".join(TYPEDATA["Specs"])}})
enum class {{TYPENAME}} : uint8
{
    {% for FIELDNAME, FIELDDATA in TYPEDATA["Members"].items() -%}
    {{FIELDNAME}}{% if FIELDDATA['Value'] %} = {{FIELDDATA['Value']}}{% endif %}{% if FIELDDATA["UMETA"] %} UMETA({{", ".join(FIELDDATA["UMETA"])}}){% endif %},
    {% endfor %}
};
{% endif %}
{%- endfor %}

{% for TYPENAME, TYPEDATA in TYPES.items() %}
{%- if TYPEDATA['Kind'] == "Struct" and not TYPEDATA['IsLocal'] %}
{%- if TYPEDATA['Docstring'] %}
/** {% for DSTRING in TYPEDATA['Docstring'] %}
 * {{DSTRING}} {% endfor %}
 */ {% endif %}
USTRUCT({{ ", ".join(TYPEDATA["Specs"])}})
struct {{TYPENAME}}
{
    GENERATED_USTRUCT_BODY()

public:
    {{TYPENAME}}()
        {%- for D in TYPEDATA['SetupDefaults'] %}
        {{D}}{% endfor %}
    {};

    {{TYPENAME}}({{", ".join(TYPEDATA['InputParams'])}})
        {%- for F in TYPEDATA['SetupParams'] %}
        {{F}}{% endfor %}
    {};

    {% for FIELDNAME, FIELDTYPE in TYPEDATA["Fields"].items() %}
    UPROPERTY({% if TYPEDATA['BlueprintType'] or TYPEDATA['Blueprintable'] %}BlueprintReadWrite, Category = "HN struct properties"{% endif %})
    {{FIELDTYPE['Name']}} {{FIELDNAME}};
    {% endfor -%}
    {%- if TYPEDATA["GeneratedCode"] %} {{TYPEDATA["GeneratedCode"]}} {% endif %}
};
{% endif -%}
{% endfor -%}