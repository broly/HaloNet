#include "HaloNet.h"
#include "Mailbox.h"
#include "HaloNetLibrary.h"
#include "Serialization.h"
#include "JsonRaw.h"


FBinarySerialization& FBinarySerialization::operator<<(int32 other)
{
	TArray<uint8> res = FBinarySerializer::FromInt(other);
	AddData(res);
	return *this;
}

FBinarySerialization& FBinarySerialization::operator<<(FString other)
{
	TArray<uint8> res = FBinarySerializer::FromString(other);
	AddData(res);
	return *this;
}

FBinarySerialization& FBinarySerialization::operator<<(TArray<uint8> other)
{
	AddData(other);
	return *this;
}

FBinarySerialization& FBinarySerialization::operator<<(const FBinarySerialization& other)
{
	AddData(other.GetArchived());
	return *this;
}


FBinarySerializationProxy FBinarySerialization::Proxy()
{
	return FBinarySerializationProxy(this);
}

TArray<uint8> FBinarySerializer::FromString(const FString& value)
{
	auto char_data = StringCast<ANSICHAR>(*value);
	
	TArray<uint8> binary_data;

	const int32 length = value.Len();
	binary_data.SetNum(4 + length);
	
	uint8* data_ptr = reinterpret_cast<uint8*>(binary_data.GetData());
	FMemory::Memcpy(data_ptr, &length, 4);
	FMemory::Memcpy(data_ptr + 4, char_data.Get(), length);

	return binary_data;
}

TArray<uint8> FBinarySerializer::_PropertyValue2BinaryArray(const UProperty* Prop, const void* ValuePtr)
{
	bool IsArray = false;
	if (Prop->ArrayDim > 1)
		IsArray = true;

	TArray<uint8> Values;
	Values.Empty();

	for (int32 i = 0; i < Prop->ArrayDim; ++i)
	{
		const void* ElementValueAddress = reinterpret_cast<const uint8*>(ValuePtr) + (Prop->ElementSize * i);

		if (const UArrayProperty* const ArrayProp = Cast<const UArrayProperty>(Prop))
		{
			FBinarySerialization data_list;

			FScriptArrayHelper ScriptArrayHelper(ArrayProp, ElementValueAddress);
			const int32 ElementCount = ScriptArrayHelper.Num();
			data_list << ElementCount;

			for (int32 j = 0; j < ElementCount; ++j)
			{
				TArray<uint8> res = _PropertyValue2BinaryArray(ArrayProp->Inner, ScriptArrayHelper.GetRawPtr(j));
				data_list.AddData(res);
			}

			Values = data_list.GetArchived();
		}
		else if (const UMapProperty* const MapProp = Cast<const UMapProperty>(Prop))
		{
			FBinarySerialization bs;
			FScriptMapHelper ScriptMapHelper(MapProp, ElementValueAddress);
			const int32 ElementCount = ScriptMapHelper.Num();
			bs << ElementCount;
			for (int32 j = 0; j < ElementCount; ++j)
			{
				if (!ScriptMapHelper.IsValidIndex(j))
					continue;
			
				const uint8* MapPairPtr = ScriptMapHelper.GetPairPtr(j);
			
				TArray<uint8> key = _PropertyValue2BinaryArray(MapProp->KeyProp, MapPairPtr + MapProp->MapLayout.KeyOffset);
				bs << key;
			}
			for (int32 j = 0; j < ElementCount; ++j)
			{
				if (!ScriptMapHelper.IsValidIndex(j))
					continue;

				const uint8* MapPairPtr = ScriptMapHelper.GetPairPtr(j);

				TArray<uint8> value = _PropertyValue2BinaryArray(MapProp->ValueProp, MapPairPtr + MapProp->MapLayout.ValueOffset);
				bs << value;
			}
			
			
			Values = bs.GetArchived();
		}
		else if (const UClassProperty* ClassProp = Cast<const UClassProperty>(Prop))
		{
			UObject* value = ClassProp->GetPropertyValue(ElementValueAddress);
			Values = FromString(value->GetName());
		}
		else if (const UStructProperty* const StructProp = Cast<const UStructProperty>(Prop))
		{
			TArray<uint8> res = _Struct2Binary(ElementValueAddress, StructProp->Struct);
			Values = res;
		}
		else if (const USetProperty* const SetProp = Cast<const USetProperty>(Prop))
		{
			FBinarySerialization data_list;

			FScriptSetHelper ScriptSetHelper(SetProp, ElementValueAddress);
			const int32 ElementCount = ScriptSetHelper.Num();
			data_list << ElementCount;

			for (int32 j = 0; j < ElementCount; ++j)
			{
				TArray<uint8> res = _PropertyValue2BinaryArray(SetProp->ElementProp, ScriptSetHelper.GetElementPtr(j));
				data_list.AddData(res);
			}

			Values = data_list.GetArchived();
		}
		else if (const UBoolProperty* const BoolProp = Cast<const UBoolProperty>(Prop))
		{
			bool value = BoolProp->GetPropertyValue(ElementValueAddress);
			Values = FromInt<uint8>(value == true);
			
		}
		// SIGNED INTS
		else if (const UEnumProperty* const EnumProp = Cast<const UEnumProperty>(Prop))
		{
			UEnum* enum_field = EnumProp->GetEnum();
			UNumericProperty* underlying = EnumProp->GetUnderlyingProperty();
			
			int64 value = underlying->GetSignedIntPropertyValue(ElementValueAddress);
			FName field_name = enum_field->GetNameByValue(value);

			FBinarySerialization sr;
			sr << field_name.ToString();
			Values = sr.GetArchived();
		}
		else if (const UNumericProperty* const NumericProp = Cast<const UNumericProperty>(Prop))
		{
			if (NumericProp->IsEnum())
			{
				int64 value = NumericProp->GetSignedIntPropertyValue(ElementValueAddress);
				UEnum* enum_field = NumericProp->GetIntPropertyEnum();
				FName field_name = enum_field->GetNameByValue(value);

				FBinarySerialization sr;
				sr << StringToBytes(field_name.ToString());
				Values = sr.GetArchived();
			}
			else if (const UInt8Property* const Int8Prop = Cast<const UInt8Property>(Prop))
			{
				TArray<uint8> res = FromInt<int8>(Int8Prop->GetSignedIntPropertyValue(ElementValueAddress));
				Values = res;
			}
			else if (const UInt16Property* const Int16Prop = Cast<const UInt16Property>(Prop))
			{
				TArray<uint8> res = FromInt<int16>(Int16Prop->GetSignedIntPropertyValue(ElementValueAddress));
				Values = res;
			}
			else if (const UIntProperty* const Int32Prop = Cast<const UIntProperty>(Prop))
			{
				TArray<uint8> res = FromInt<int32>(Int32Prop->GetSignedIntPropertyValue(ElementValueAddress));
				Values = res;
			}
			else if (const UInt64Property* const Int64Prop = Cast<const UInt64Property>(Prop))
			{
				TArray<uint8> res = FromInt<int64>(Int64Prop->GetSignedIntPropertyValue(ElementValueAddress));
				Values = res;
			}
			// UNSIGNED INTS
			else if (const UByteProperty* const UInt8Prop = Cast<const UByteProperty>(Prop))
			{
				TArray<uint8> res = FromInt<uint8>(UInt8Prop->GetUnsignedIntPropertyValue(ElementValueAddress));
				Values = res;
			}
			else if (const UUInt16Property* const UInt16Prop = Cast<const UUInt16Property>(Prop))
			{
				TArray<uint8> res = FromInt<uint16>(UInt16Prop->GetUnsignedIntPropertyValue(ElementValueAddress));
				Values = res;
			}
			else if (const UUInt32Property* const UInt32Prop = Cast<const UUInt32Property>(Prop))
			{
				TArray<uint8> res = FromInt<uint32>(UInt32Prop->GetUnsignedIntPropertyValue(ElementValueAddress));
				Values = res;
			}
			else if (const UUInt64Property* const UInt64Prop = Cast<const UUInt64Property>(Prop))
			{
				TArray<uint8> res = FromInt<uint64>(UInt64Prop->GetUnsignedIntPropertyValue(ElementValueAddress));
				Values = res;
			}
			else if (const UDoubleProperty* const UDoubleProp = Cast<const UDoubleProperty>(Prop))
			{
				TArray<uint8> res = FromInt<double>(UDoubleProp->GetFloatingPointPropertyValue(ElementValueAddress));
				Values = res;
			}
			else if (const UFloatProperty* const UFloatProp = Cast<const UFloatProperty>(Prop))
			{
				TArray<uint8> res = FromInt<float>(UFloatProp->GetFloatingPointPropertyValue(ElementValueAddress));
				Values = res;
			}
		}
		else if (const UObjectPropertyBase* const ObjectProp = Cast<const UObjectPropertyBase>(Prop))
		{
			if (ObjectProp->PropertyClass->IsChildOf(UMailbox::StaticClass()))
			{
				checkf(false, TEXT("Client mailbox serialization not supported yet"));
			}
			//ERROR_MSG("SOMETHING WENT WRONG IN SERIALIZER!");
			// note: need to detect loops
			//const UObject* InnerObject = ObjectProp->GetObjectPropertyValue(ElementValueAddress);
			//if (InnerObject)
			//{
			//	TArray<uint8> res = _PropertyValue2BinaryArray(InnerObject);
			//	Values.Add(res);
			//}
		}
		else if (const UStrProperty* const StrProp = Cast<const UStrProperty>(Prop))
		{
			FString value = StrProp->GetPropertyValue(ElementValueAddress);
			Values = FromString(value);
		}
		else if (const UNameProperty* const NameProp = Cast<const UNameProperty>(Prop))
		{
			FName value = NameProp->GetPropertyValue(ElementValueAddress);
			Values = FromString(value.ToString());
		}
		else if (const UTextProperty* const TextProp = Cast<const UTextProperty>(Prop))
		{
			check(0);
		}
		else
		{
			FString TextString = TEXT("");
			Prop->ExportText_Direct(TextString, ElementValueAddress, ElementValueAddress, nullptr, PPF_Delimited);
			if (TextString == "")
				TextString = "\"\"";
			//Values.Add(TextString);
			Values = FromString(TextString);
		}
	}

	return Values;
	//FString Result = FString::Join(Values, TEXT(", "));
	//
	//if (IsArray)
	//	return FString::Printf(TEXT("[%s]"), *Result);
	//return Result;
}


TArray<uint8> FBinarySerializer::_Struct2Binary(const void* StructData, UStruct* StructStructure)
{
	if (StructStructure->GetName() == GetStructNameHN<FBytes>())
	{
		UArrayProperty* ArrayProp = FindField<UArrayProperty>(StructStructure, "Data");

		if (ArrayProp->GetName() == TEXT("Data"))
		{

			const FScriptArray& script_value = ArrayProp->GetPropertyValue_InContainer(StructData);
			FScriptArray& v = const_cast<FScriptArray&>(script_value);
			TArray<uint8>* value = reinterpret_cast<TArray<uint8>*>( &v );

			int32 array_count = value->Num();
			TArray<uint8> out_value;
			out_value.SetNum(4 + value->Num());
			FMemory::Memcpy(out_value.GetData(),     &array_count,     4);
			FMemory::Memcpy(out_value.GetData() + 4, value->GetData(), array_count);

			return out_value;
		}

	}

	FBinarySerialization data_list;

	if (StructStructure->GetName() == TEXT("Timespan") || StructStructure->GetName() == TEXT("DateTime"))
	{
		TArray<uint8> res = FromInt<int64>(*(int64*)StructData);
		return res;
	}
	else
	{
		for (TFieldIterator<const UProperty> PropIt(StructStructure, EFieldIteratorFlags::IncludeSuper, EFieldIteratorFlags::ExcludeDeprecated, EFieldIteratorFlags::IncludeInterfaces); PropIt; ++PropIt)
		{
			TArray<uint8> data = _PropertyValue2BinaryArray(*PropIt, PropIt->ContainerPtrToValuePtr<void>(StructData));
			data_list.AddData(data);
		}
	}

	return data_list.GetArchived();
}

void FBinarySerializer::_BinaryArray2PropertyValue(UProperty* Prop, void* ValuePtr, TArray<uint8> BinaryArray, UHaloNetLibrary* networking_instance)
{

	void* ElementValueAddress = reinterpret_cast<uint8*>(ValuePtr);
	Prop->InitializeValue(ValuePtr);

	if (UArrayProperty* ArrayProp = Cast<UArrayProperty>(Prop))
	{
		{
			
			FScriptArrayHelper ScriptArrayHelper(ArrayProp, ElementValueAddress);

		
			auto bs = FBinarySerialization(BinaryArray);
			auto srp = bs.Proxy();

			int32 count;
			if (srp >> count)
			{
				// auto Array = data_list.GetDatas();
				ScriptArrayHelper.EmptyValues(count);

				for (int32 j = 0; j < count; ++j)
				{
					int32 index = ScriptArrayHelper.AddValue();
					TArray<uint8> Value;
					srp >> Value;
					_BinaryArray2PropertyValue(ArrayProp->Inner, ScriptArrayHelper.GetRawPtr(index), Value, networking_instance);
				}
			}
		}

	}
	else if (UMapProperty* MapProp = Cast<UMapProperty>(Prop))
	{
		FScriptMapHelper ScriptMapHelper(MapProp, ElementValueAddress);
		auto dproxy = FBinarySerializationProxy(BinaryArray);

		int32 count;
		dproxy >> count;

		TArray<TArray<uint8>> keys;
		TArray<TArray<uint8>> values;
		for (int32 i = 0; i < count; i++)
		{
			TArray<uint8> bytes;
			dproxy >> bytes;
			keys.Add(bytes);
		}
		for (int32 i = 0; i < count; i++)
		{
			TArray<uint8> bytes;
			dproxy >> bytes;
			values.Add(bytes);
		}
		for (int32 j = 0; j < count; ++j)
		{
			int32 index = ScriptMapHelper.AddDefaultValue_Invalid_NeedsRehash();
			ScriptMapHelper.Rehash();
		}
		ScriptMapHelper.Rehash();

		int32 k = 0;

		const int32 ElementCount = ScriptMapHelper.Num();
		for (int32 j = 0; j < ElementCount; ++j)
		{
			if (!ScriptMapHelper.IsValidIndex(j))
				continue;
		
			uint8* MapPairPtr = ScriptMapHelper.GetPairPtr(j);
		
			_BinaryArray2PropertyValue(MapProp->KeyProp, MapPairPtr + MapProp->MapLayout.KeyOffset, keys[k], networking_instance);
			_BinaryArray2PropertyValue(MapProp->ValueProp, MapPairPtr + MapProp->MapLayout.ValueOffset, values[k], networking_instance);
			k++;
		
		}
		ScriptMapHelper.Rehash();
	}
	else if (USetProperty* SetProp = Cast<USetProperty>(Prop))
	{
		FScriptSetHelper ScriptSetHelper(SetProp, ElementValueAddress);

		auto bs = FBinarySerialization(BinaryArray);
		auto srp = bs.Proxy();

		int32 count;
		srp >> count;

		ScriptSetHelper.EmptyElements(count);

		for (int32 j = 0; j < count; ++j)
		{
			int32 index = ScriptSetHelper.AddDefaultValue_Invalid_NeedsRehash();
			ScriptSetHelper.Rehash();
			TArray<uint8> Value;
			srp >> Value;
			_BinaryArray2PropertyValue(SetProp->ElementProp, ScriptSetHelper.GetElementPtr(index), Value, networking_instance);
		}
		ScriptSetHelper.Rehash();

		// FScriptSetHelper ScriptSetHelper(SetProp, ElementValueAddress);
		// 
		// auto data_list = FBinarySerialization(BinaryArray);
		// 
		// auto Set = data_list.GetDatas();
		// int32 ElementsCount = Set.Num();
		// 
		// ScriptSetHelper.EmptyElements(ElementsCount);
		// 
		// for (int32 j = 0; j < ElementsCount; ++j)
		// {
		// 	int32 index = ScriptSetHelper.AddDefaultValue_Invalid_NeedsRehash();
		// 	ScriptSetHelper.Rehash();
		// }
		// int32 k = 0;
		// for (int32 j = 0; j < ElementsCount; ++j)
		// {
		// 	if (!ScriptSetHelper.IsValidIndex(j))
		// 		continue;
		// 
		// 	uint8* ElemPtr = ScriptSetHelper.GetElementPtr(j);
		// 
		// 	_BinaryArray2PropertyValue(SetProp->ElementProp, ElemPtr, Set[j], networking_instance);
		// 	k++;
		// 
		// }
		// ScriptSetHelper.Rehash();

	}
	else if (UStructProperty* StructProp = Cast<UStructProperty>(Prop))
	{
		_BinaryArrayToStruct(ElementValueAddress, StructProp->Struct, BinaryArray, networking_instance);
	}
	//else if (UAssetClassProperty* AssetClassProp = Cast<UAssetClassProperty>(Prop)) 4.15
	else if (USoftClassProperty* AssetClassProp = Cast<USoftClassProperty>(Prop))
	{
		FStringAssetReference AssetToLoad;
		FString asset_path = ToStringValue(BinaryArray);
		if (asset_path.StartsWith(TEXT("Blueprint'")) && asset_path.EndsWith(TEXT("'")))
			asset_path = asset_path.RightChop(10)
								   .LeftChop(1) + TEXT("_C");
		else if (asset_path.StartsWith(TEXT("Class'")) && asset_path.EndsWith(TEXT("'")))
			asset_path = asset_path.RightChop(6)
								   .LeftChop(1) + TEXT("_C");
		AssetToLoad.SetPath(asset_path);
		//FAssetPtr ptr(AssetToLoad); 4.15
		FSoftObjectPtr ptr(AssetToLoad); //4.18
		
		AssetClassProp->SetPropertyValue(ValuePtr, ptr);
	}
	else if (UClassProperty* ClassProp = Cast<UClassProperty>(Prop))
	{

		FString asset_path = ToStringValue(BinaryArray);

		if (!asset_path.IsEmpty())

		{

			if (asset_path.StartsWith(TEXT("Blueprint'")) && asset_path.EndsWith(TEXT("'")))
				asset_path = asset_path.RightChop(10)
				.LeftChop(1) + TEXT("_C");
			else if (asset_path.StartsWith(TEXT("Class'")) && asset_path.EndsWith(TEXT("'")))
				asset_path = asset_path.RightChop(6)
				.LeftChop(1) + TEXT("_C");

			UClass* cls = LoadClass<UObject>(networking_instance, *asset_path);

			if (!ensure(cls != nullptr || asset_path == TEXT("")))
				ERROR_MSGHN("Failed to load asset %s", *asset_path);

			ClassProp->SetPropertyValue(ValuePtr, cls);
		}
	}
	else if (UObjectPropertyBase* ObjectProp = Cast<UObjectPropertyBase>(Prop))
	{
		if (ObjectProp->PropertyClass->IsChildOf(UMailbox::StaticClass()))
		{
			auto sr = FBinarySerialization(BinaryArray);
			auto srp = sr.Proxy();
			FString ip; 
			int32 port;
			int32 id;
			FString context;
			FString class_name;

			srp >> ip;
			srp >> port;
			srp >> id;
			srp >> context;
			srp >> class_name;

			if ensure (networking_instance)
			{
				if (ip == TEXT("0.0.0.0") && port == 0)
				{
					ObjectProp->SetObjectPropertyValue(ValuePtr, nullptr);
				}
				else 
				{
					auto endpoint = IPPort2Endpoint(ip, port);
					UMailbox* new_mbox = networking_instance->CreateMailbox(endpoint, id, ObjectProp->PropertyClass);
					ObjectProp->SetObjectPropertyValue(ValuePtr, new_mbox);
				}
			}
		} else if (ObjectProp->PropertyClass->IsChildOf(UJsonRaw::StaticClass()))
		{
			ObjectProp->SetObjectPropertyValue(ValuePtr, UJsonRaw::Deserialized(BinaryArray));
		}
		//ERROR_MSG("SOMETHING WENT WRONG IN SERIALIZER!");
		// note: need to detect loops
		//UObject* InnerObject = ObjectProp->GetObjectPropertyValue(ElementValueAddress);
		//if (InnerObject)
		//{
		//	_JsonToObject(InnerObject, JsonValuePtr->AsObject());
		//}
	}
	else
	{
		if (const UEnumProperty* EnumProp = Cast<UEnumProperty>(Prop))
		{
			UEnum* enum_field = EnumProp->GetEnum();
			UNumericProperty* underlying = EnumProp->GetUnderlyingProperty();
			auto srp = FBinarySerializationProxy(BinaryArray);
			FString name;
			srp >> name;
			uint64 value = enum_field->GetValueByName(*name);
			underlying->SetIntPropertyValue(ValuePtr, value);
		}
		else if (const UNumericProperty* NumProp = Cast<UNumericProperty>(Prop))
		{
			// SIGNED INTS
			if (NumProp->IsEnum())
			{
				auto srp = FBinarySerializationProxy(BinaryArray);
				FString name;
				srp >> name;
				UEnum* enum_field = NumProp->GetIntPropertyEnum();
				uint64 value = enum_field->GetValueByName(*name);
				NumProp->SetIntPropertyValue(ValuePtr, value);
			}
			else if (const UInt8Property* Int8Prop = Cast<UInt8Property>(NumProp))
			{
				void* ptr = ValuePtr;
				int8 value = ToNumericValue<int8>(BinaryArray);
				Int8Prop->SetIntPropertyValue(ptr, static_cast<int64>(value));
			}
			else if (const UInt16Property* Int16Prop = Cast<UInt16Property>(NumProp))
			{
				void* ptr = ValuePtr;
				int16 value = ToNumericValue<int16>(BinaryArray);
				Int16Prop->SetIntPropertyValue(ptr, static_cast<int64>(value));
			}
			else if (const UIntProperty* Int32Prop = Cast<UIntProperty>(NumProp))
			{
				void* ptr = ValuePtr;
				int32 value = ToNumericValue<int32>(BinaryArray);
				Int32Prop->SetIntPropertyValue(ptr, static_cast<int64>(value));
			}
			else if (const UInt64Property* Int64Prop = Cast<UInt64Property>(NumProp))
			{
				void* ptr = ValuePtr;
				int64 value = ToNumericValue<int64>(BinaryArray);
				Int64Prop->SetIntPropertyValue(ptr, static_cast<int64>(value));
			}
			// UNSIGNED INTS
			else if (const UByteProperty* UInt8Prop = Cast<UByteProperty>(NumProp))
			{
				void* ptr = ValuePtr;
				uint8 value = ToNumericValue<uint8>(BinaryArray);
				UInt8Prop->SetIntPropertyValue(ptr, static_cast<uint64>(value));
			}
			else if (const UUInt16Property* UInt16Prop = Cast<UUInt16Property>(NumProp))
			{
				void* ptr = ValuePtr;
				uint16 value = ToNumericValue<uint16>(BinaryArray);
				UInt16Prop->SetIntPropertyValue(ptr, static_cast<uint64>(value));
			}
			else if (const UUInt32Property* UInt32Prop = Cast<UUInt32Property>(NumProp))
			{
				void* ptr = ValuePtr;
				uint32 value = ToNumericValue<int32>(BinaryArray);
				UInt32Prop->SetIntPropertyValue(ptr, static_cast<uint64>(value));
			}
			else if (const UUInt64Property* UInt64Prop = Cast<UUInt64Property>(NumProp))
			{
				void* ptr = ValuePtr;
				uint64 value = ToNumericValue<int64>(BinaryArray);
				UInt64Prop->SetIntPropertyValue(ptr, static_cast<uint64>(value));
			}
			// FLOATING POINT
			else if (const UFloatProperty* FloatProp = Cast<UFloatProperty>(NumProp))
			{
				void* ptr = ValuePtr;
				float value = ToNumericValue<float>(BinaryArray);
				FloatProp->SetFloatingPointPropertyValue(ptr, static_cast<double>(value));
			}
			else if (const UDoubleProperty* DoubleProp = Cast<UDoubleProperty>(NumProp))
			{
				void* ptr = ValuePtr;
				double value = ToNumericValue<double>(BinaryArray);
				DoubleProp->SetFloatingPointPropertyValue(ptr, static_cast<double>(value));
			}
		}

		else if (const UBoolProperty* BoolProp = Cast<UBoolProperty>(Prop))
		{
			bool value = ToNumericValue<uint8>(BinaryArray) != 0;
			BoolProp->SetPropertyValue(ValuePtr, value);
		}
		else
		{

			if (const UStrProperty* StrProp = Cast<UStrProperty>(Prop))
			{
				FString TextString = ToStringValue(BinaryArray);
				FString value = TextString;
				StrProp->SetPropertyValue(ValuePtr, value);
			}
			else if (const UTextProperty* TextProp = Cast<UTextProperty>(Prop))
			{
				FText value = DeserializeText(BinaryArray);
				TextProp->SetPropertyValue(ValuePtr, value);
			}
			else if (const UNameProperty* NameProp = Cast<UNameProperty>(Prop))
			{
				FString TextString = ToStringValue(BinaryArray);
				FName value = FName(*TextString);
				NameProp->SetPropertyValue(ValuePtr, value);
			}
		}
	}
}

void FBinarySerializer::_BinaryArrayToStruct(void* StructData, UStruct* Struct, TArray<uint8> BinaryArray, UHaloNetLibrary* networking_instance)
{
	// if (Struct->GetName() == TEXT("Bytes"))
	if (Struct->GetName() == GetStructNameHN<FBytes>())
	{
		TArray<uint8> data;
		
		int32 diff = BinaryArray.Num() - 4;
		if (!ensureAlways(diff > 0))
			return;

		data.AddZeroed(diff);
		FMemory::Memcpy(data.GetData(), BinaryArray.GetData() + 4, diff);
		auto array_prop = FindFieldChecked<UArrayProperty>(Struct, TEXT("Data"));

		// _BinaryArray2PropertyValue(array_prop, array_prop->ContainerPtrToValuePtr<void>(StructData), data, networking_instance);

		FScriptArrayHelper ScriptArrayHelper(array_prop, array_prop->ContainerPtrToValuePtr<void>(StructData));
		
		int32 count = data.Num();

		ScriptArrayHelper.EmptyValues(count);

		for (int32 j = 0; j < count; ++j)
		{
			int32 index = ScriptArrayHelper.AddValue();
			uint8 Value = data[j];
			if (auto byte_prop = Cast<UByteProperty>(array_prop->Inner))
			{
				byte_prop->SetPropertyValue(ScriptArrayHelper.GetRawPtr(index), Value);
			}
		}
		return;
	}

	if (Struct->GetName() == TEXT("Timespan") || Struct->GetName() == TEXT("DateTime"))
	{
		int64 ticks = ToNumericValue<int64>(BinaryArray);
		// FMemory::Memcpy(StructData, &ticks, sizeof int64);
		*((int64*)StructData) = ticks;
		return;
	}

	auto data_list = FBinarySerialization(BinaryArray);
	if (data_list.IsValid())
	{
		int32 data_list_count = data_list.Num();
		int32 data_index = 0;

		for (TFieldIterator<UProperty> PropIt(Struct, EFieldIteratorFlags::IncludeSuper, EFieldIteratorFlags::ExcludeDeprecated, EFieldIteratorFlags::IncludeInterfaces); PropIt; ++PropIt)
		{
			ensure(data_index <= data_list_count);
			if (data_list.Num() > 0)
			{
				TArray<uint8> data = data_list[data_index];
				_BinaryArray2PropertyValue(*PropIt, PropIt->ContainerPtrToValuePtr<void>(StructData), data, networking_instance);
				data_index++;
			}
		}
	}
}

FText FBinarySerializer::DeserializeText(TArray<uint8> data)
{
	auto srp = FBinarySerializationProxy(data);
	FString text;
	FString key;
	FString nspace;
	int32 format_values_count;
	FFormatOrderedArguments format_values;
	srp >> text;
	srp >> key;
	srp >> nspace;
	srp >> format_values_count;

	for (int32 i = 0; i < format_values_count; i++)
	{
		int32 value_type;
		srp >> value_type;
		FText deserialized_entry;
		FString str;
		TArray<uint8> bytes;
		switch (value_type)
		{
		case int32(ETextFormatValueType::Simple):
			srp >> str;
			deserialized_entry = FText::FromString(str);
			break;
		case int32(ETextFormatValueType::Text):
			srp >> bytes;
			deserialized_entry = DeserializeText(bytes);
			break;
		default:
			ERROR_MSGHN("Serialization error");
		}
		format_values.Add(deserialized_entry);
	}

	FText out_text = FInternationalization::ForUseOnlyByLocMacroAndGraphNodeTextLiterals_CreateText(*text, *nspace, *key);

	return FText::Format(out_text, format_values);
}


FString FBinarySerializer::ToStringValue(TArray<uint8> binary_array)
{
	if ensure(binary_array.Num() >= 4)
	{
		uint8* data_ptr = reinterpret_cast<uint8*>(binary_array.GetData());

		int32 length;
		FMemory::Memcpy(&length, data_ptr, 4);

		if ensure(length >= 0 && length <= binary_array.Num() - 4)
		{
			char* raw_str = new char[length + 1];
			FMemory::Memcpy(raw_str, data_ptr + 4, length);
			raw_str[length] = '\0';

			return FString(UTF8_TO_TCHAR(raw_str));
		}
	}
	return TEXT("");
}

TArray<uint8> FBinarySerializer::StringToBytes(FString string_value)
{
	TArray<uint8> result;

	result.Append(FromInt<int32>(string_value.Len()));
	result.Append(FromString(string_value));

	return result;
}
