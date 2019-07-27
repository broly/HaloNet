// Copyright 1998-2017 Epic Games, Inc. All Rights Reserved.


#pragma once

#include "HaloNetEditor.h"
#include "UObject/ObjectMacros.h"
#include "K2Node.h"
#include "EdGraphSchema_K2.h"
#include "SGraphNode.h"
#include "SGraphNodeK2Base.h"

#include "K2Node_Await.generated.h"

class FBlueprintActionDatabaseRegistrar;
class UEdGraph;

struct FAwaitNodePinSpecification
{
	
};


/**
 * K2Node "Await"
 * 
 * Receives and Mailbox, finds all async methods (that returning futures) 
 * And creates pins for each parameter of selected method (from dropdown list) with return values!
 */
UCLASS(MinimalAPI, meta = (Keywords = "await"))
class UK2Node_HN_Await : public UK2Node
{
	GENERATED_BODY()

public:
	// UEdGraphNode interface
	virtual void AllocateDefaultPins() override;
	virtual void ReallocatePinsDuringReconstruction(TArray<UEdGraphPin*>& OldPins) override;
	virtual void PinConnectionListChanged(UEdGraphPin* Pin);
	virtual FText GetTooltipText() const override;
	virtual void PinDefaultValueChanged(UEdGraphPin* Pin) override;
	virtual FText GetNodeTitle(ENodeTitleType::Type TitleType) const override;
	virtual bool IsCompatibleWithGraph(const UEdGraph* TargetGraph) const override;
	virtual FLinearColor GetNodeTitleColor() const override;
	FSlateIcon GetIconAndTint(FLinearColor& OutColor) const;
	// End of UEdGraphNode interface

	// UK2Node interface
	virtual bool IsNodePure() const override { return false; }
	virtual void ExpandNode(class FKismetCompilerContext& CompilerContext, UEdGraph* SourceGraph) override;
	virtual FName GetCornerIcon() const override;
	virtual void GetMenuActions(FBlueprintActionDatabaseRegistrar& ActionRegistrar) const override;
	virtual FText GetMenuCategory() const override;
	virtual bool NodeCausesStructuralBlueprintChange() const { return true; }
#if WITH_EDITOR
	virtual TSharedPtr<SGraphNode> CreateVisualWidget() override;
#endif
	// End of UK2Node interface

	/** Saved pins of current async method */
	TArray<UEdGraphPin*> CachedPins;

	/** Current method name for display */
	FString CachedFunctionName;

	/** Current mailbox name for display */
	FString CachedMailboxName;

	/** All method names of current mailbox */
	TArray<FName> MailboxFunctionNames;

	/** Current mailbox class */
	UClass* CurrentMailboxClass;

	/** Current selected method */
	UFunction* CurrentFunction;

	/** Current latent function by selected method */
	UFunction* CurrentLatentFunction;

	TArray<UProperty*> CurrentInProperties;
	TArray<UProperty*> CurrentOutProperties;


	/** Finds pin in current Graph (or in OldPins if specified) */
	UEdGraphPin* GetPinSpecified(FString PinName, TArray<UEdGraphPin*>* OldPins = nullptr);

	/**
	 * returns mailbox class of current pins in Graph (or OldPins)
	 */
	UClass* GetMailboxClass(TArray<UEdGraphPin*>* OldPins = nullptr);

	/**
	 * Constructs methods pins if mailbox specified
	 */
	UEdGraphPin* ConstructMethodPinByMailbox(TArray<UEdGraphPin*>* OldPins = nullptr, bool bRemovePrevious = false);

	/**
	 * Calls if Target pin changed
	 */
	void MailboxPinChanged(TArray<UEdGraphPin*>* OldPins = nullptr);

	/**
	 * Finds function by name in specified mailbox
	 */
	UFunction* GetMailboxFunction(UClass* MailboxClass, FName FunctionName);

	/**
	 * Generates pins for specified function with specified direction
	 */
	TArray<UEdGraphPin*> FindPropertiesAndGeneratePinsForAsyncFunction(UFunction* func, EEdGraphPinDirection direction, TArray<UProperty*>& OutProperties, bool bOnlyFindProperties = false);

protected:

	const class UEdGraphSchema_K2* GetK2Schema();

};

/**
 * Slate representation of current node
 * The Graph Node with drop down parameter!
 */
class SK2Node_MethodsDropdown : public SGraphNodeK2Base
{
public:
	SLATE_BEGIN_ARGS(SK2Node_MethodsDropdown);
	SLATE_END_ARGS()


	void Construct(const FArguments& InArgs, class UK2Node_HN_Await* InNode);


	virtual void CreateStandardPinWidget(UEdGraphPin* Pin) override;

	TSharedRef<SWidget> GetPickerMenu();

	void OnAssetSelectedFromPicker(const FAssetData& AssetData);

	FText GetAssetName() const;

	void CreateDetailsPickers();

	TSharedRef<SWidget> GetCurrentItemWidget(TSharedRef<STextBlock> TextContent);

	FText GetCurrentText();

	const FSlateBrush* GetCurrentIconBrush() const;

	void SetMethodName(FName InName);

private:

	FSlateColor OnGetComboForeground() const;

	FSlateColor OnGetWidgetForeground() const;

	FSlateColor OnGetWidgetBackground() const;

private:
	/** Items in dropdown list */
	TArray<FName> Names;

	/** Cached current icon */
	FSlateIcon CurrentIcon;

};