// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "HaloNet.h"
#include "JsonRaw.generated.h"


UCLASS()
class UJsonRaw : public UObject
{
	GENERATED_BODY()
	
public:
	
	TArray<uint8> Serialized();
	static UJsonRaw* Deserialized(TArray<uint8> serialized_value);

	void SetJsonObject(TSharedPtr<FJsonObject> InJsonObject);

	UFUNCTION(BlueprintPure, Category = "JSON", meta = (CompactNodeTitle = "GET"))
	FString GetStringField(FString field_name) const;

	UFUNCTION(BlueprintPure, Category = "JSON", meta = (CompactNodeTitle = "GET"))
	int32 GetIntegerField(FString field_name) const;

	UFUNCTION(BlueprintPure, Category = "JSON", meta = (CompactNodeTitle = "GET"))
	float GetFloatField(FString field_name) const;

	UFUNCTION(BlueprintPure, Category = "JSON", meta = (CompactNodeTitle = "Contains"))
	bool Contains(FString field_name) const;

	UFUNCTION(BlueprintPure, Category = "JSON", meta = (CompactNodeTitle = "Contains String"))
	bool ContainsStringField(FString field_name) const;

	UFUNCTION(BlueprintPure, Category = "JSON", meta = (CompactNodeTitle = "Contains Number", Keywords = "Int,Float,Number"))
	bool ContainsNumberField(FString field_name) const;

	TSharedPtr<FJsonObject> JsonObject;
};