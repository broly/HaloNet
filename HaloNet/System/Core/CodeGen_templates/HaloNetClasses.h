#pragma once

#include "{{PROJECT_NAME}}.h"
{% for incl in INCLUDES %}
#include "{{incl}}"
{%- endfor %}

#include "HaloNetCommon.h"