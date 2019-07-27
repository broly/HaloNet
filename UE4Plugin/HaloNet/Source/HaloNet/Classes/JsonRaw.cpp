// Fill out your copyright notice in the Description page of Project Settings.

#include "HaloNet.h"
#include "Utils.h"
#include "Serialization.h"
#include "JsonRaw.h"


TArray<uint8> UJsonRaw::Serialized()
{
	checkf(false, TEXT("Not implemented"));
	return {};
}

UJsonRaw* UJsonRaw::Deserialized(TArray<uint8> serialized_value)
{
	auto sr = FBinarySerialization(serialized_value);
	auto srp = sr.Proxy();
	FString json_string;
	srp >> json_string;

	TSharedPtr<FJsonObject> json_object = MakeShareable(new FJsonObject());
	
	TSharedRef< TJsonReader<TCHAR> > reader = TJsonReaderFactory<TCHAR>::Create(json_string);

	UJsonRaw* out_json_raw = nullptr;

	if ensure(FJsonSerializer::Deserialize(reader, json_object))
	{
		out_json_raw = NewObject<UJsonRaw>();
		out_json_raw->SetJsonObject(json_object);
	}	

	return out_json_raw;
}

void UJsonRaw::SetJsonObject(TSharedPtr<FJsonObject> InJsonObject)
{
	JsonObject = InJsonObject;
}

FString UJsonRaw::GetStringField(FString field_name) const
{
	FString result;
	JsonObject->TryGetStringField(field_name, result);
	return result;
}

int32 UJsonRaw::GetIntegerField(FString field_name) const
{
	double result;
	JsonObject->TryGetNumberField(field_name, result);
	return FMath::RoundToInt(result);
}

float UJsonRaw::GetFloatField(FString field_name) const
{
	double result;
	JsonObject->TryGetNumberField(field_name, result);
	return result;
}

bool UJsonRaw::Contains(FString field_name) const
{
	return JsonObject->HasField(field_name);
}

bool UJsonRaw::ContainsStringField(FString field_name) const
{
	return JsonObject->HasTypedField<EJson::String>(field_name);

}

bool UJsonRaw::ContainsNumberField(FString field_name) const
{
	return JsonObject->HasTypedField<EJson::Number>(field_name);
}
