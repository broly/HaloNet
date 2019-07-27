#pragma once

#include "{{PROJECT_NAME}}.h"
#include "Mailbox.h"
#include "HaloNet/Generated/HaloNetDataTypes.h"
#include "Classes/Future.h"
#include "{{ENTITY_NAME}}{{CONTEXT_NAME}}Mailbox.generated.h"
{% for fwd_type in FORWARDED_TYPES %}
class {{fwd_type}};
{%- endfor %}
{% for method_name, method_info in METHODS.items() %} {% if method_info['is_async'] %}
UCLASS()
class U{{ENTITY_FULLNAME}}_{{method_name}}_Future : public UFuture
{
    GENERATED_BODY()

public:
    DECLARE_DYNAMIC_MULTICAST_DELEGATE{{method_info["delegate_postfix"]}}(FOnSetResult{% if (method_info["dynamic_delegate_retvals_decl"].__len__()) != 0 %}, {% endif %}{{ ", ".join(method_info["dynamic_delegate_retvals_decl"])}});
    UPROPERTY(BlueprintAssignable, BlueprintReadWrite, Category = "Future")
    FOnSetResult OnSetResult;

    DECLARE_DELEGATE{{method_info["delegate_postfix"]}}(FOnSetResultStatic{% if (method_info["dynamic_delegate_retvals"].__len__()) != 0 %}, {% endif %}{{ ", ".join(method_info["delegate_retvals"])}});
    FOnSetResultStatic OnSetResultStatic;

    UFUNCTION()
    void Execute({{ ", ".join(method_info["returns_list"])}});

    ThisClass& MakeContext(UObject* context)
    {
        checkf(this, TEXT("Invalid mailbox call awaiting"));
        SetContext(context);
        return *this;
    }

    ThisClass& operator<<(TFunction<void({{ ", ".join(method_info["delegate_retvals"])}})> lambda)
    {
        OnSetResultStatic.BindLambda(lambda);
        return *this;
    }

    ThisClass& operator>>(TFunction<void({{ ", ".join(method_info["delegate_retvals"])}})> lambda)
    {
        bExecuteAnyway = true;
        OnSetResultStatic.BindLambda(lambda);
        return *this;
    }

};


{% endif %} {% endfor %}

UCLASS()
class {{PROJECT_API}}_API U{{ENTITY_FULLNAME}}Mailbox
    : public UMailbox
{
    GENERATED_BODY()

public:

    U{{ENTITY_FULLNAME}}Mailbox(const FObjectInitializer& ObjectInitializer);

    /// Generated methods
    {% for method_name, method_info in METHODS.items() %}
    RPC_EXEC({{method_name}})
    {%- if method_info['Docstring'] %}
    /** {% for DSTRING in method_info['Docstring'] %}
     * {{DSTRING}} {% endfor %}
     */ {% endif %}
    UFUNCTION(CustomThunk{% if method_info['BlueprintCallable'] %}, BlueprintCallable{% endif %}{% if method_info['Exec'] %}, Exec{% endif %}, Category = "{{method_info['Category']}}")
    {% if method_info['is_async'] %}U{{ENTITY_FULLNAME}}_{{method_name}}_Future*{% else %}void{% endif %} {{method_name}}({{", ".join(method_info['params_list_with_defaults'])}});
    {% endfor %}

    {% if LATENT_SUPPORTED %}
    // Latent functions section
    {% for method_name, method_info in METHODS.items() %} {% if method_info['Latent'] %}
    DECLARE_DYNAMIC_DELEGATE{{method_info["delegate_postfix"]}}(FOnLatentSetResult_{{method_name}}{% if (method_info["dynamic_delegate_retvals_decl"].__len__()) != 0 %}, {% endif %}{{ ", ".join(method_info["dynamic_delegate_retvals_decl"])}});

	UFUNCTION(BlueprintCallable, meta = (Latent, LatentInfo = "LatentInfo", WorldContext = "WorldContextObject", BlueprintInternalUseOnly = "true"), Category = "Utilities")
	static void internal_{{method_name}}(UObject* WorldContextObject, U{{ENTITY_FULLNAME}}Mailbox* Target, {{", ".join(method_info['params_list'])}}, FOnLatentSetResult_{{method_name}} OnDone, FLatentActionInfo LatentInfo);
    {%- endif %} {% endfor %}
    // end of latent functions section
    {% endif %}
};