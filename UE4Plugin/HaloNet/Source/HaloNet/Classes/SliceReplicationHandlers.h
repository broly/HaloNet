#pragma once

#include "HaloNet.h"
#include "Sockets.h"
#include "Classes/Serialization.h"
#include "Networking.h"


enum class ESliceReplicationKind
{
	Full,
	Clear,
	EditEntry,
	Add,
	RemoveEntry,
	Extend,
};

enum class ESliceReplicationDataType
{
	Map,
	Array
};

template<ESliceReplicationDataType rep_dt>
struct FSliceReplicationHandler {};

HALONET_API inline FString WatchMem(uint8* ptr, int32 count)
{
	TArray<uint8> mem_array;
	mem_array.Init(0, count);
	FMemory::Memcpy(mem_array.GetData(), ptr, count);
	return Bytes2String(mem_array);
}

template<>
struct FSliceReplicationHandler<ESliceReplicationDataType::Map>
{
	static bool Handle(UObject* InEntity, UProperty* InProperty, FBinarySerializationProxy& serialization_proxy, UHaloNetLibrary* HN)
	{
		UMapProperty* prop = Cast<UMapProperty>(InProperty);

		if (!prop)
			return false;

		int32 rep_kind;

		while (serialization_proxy >> rep_kind)
		{
			switch (ESliceReplicationKind(rep_kind))
			{
				case ESliceReplicationKind::Add:
				case ESliceReplicationKind::EditEntry:
				{
					PRINTHN("SliceRep: Edit entry of %s", *InProperty->GetName());
					TArray<uint8> serialzied_key_value;
					serialization_proxy >> serialzied_key_value;

					TArray<uint8> key;
					TArray<uint8> value;
					auto kv_srp = FBinarySerializationProxy(serialzied_key_value);
					kv_srp >> key;
					kv_srp >> value;

					const int32 size = prop->KeyProp->GetSize();
					const int32 value_size = prop->ValueProp->GetSize();
					uint8* ptr = (uint8*)FMemory::Malloc(size);
					uint8* old_value_ptr = (uint8*)FMemory::Malloc(value_size);
					prop->KeyProp->InitializeValue(ptr);
					prop->ValueProp->InitializeValue(old_value_ptr);
					FBinarySerializer::_BinaryArray2PropertyValue(prop->KeyProp, ptr, key, HN);
					FScriptMapHelper_InContainer helper(prop, InEntity);
					bool bNotFound = true;
					uint8* value_ptr = nullptr;

					for (int32 i = 0; i < helper.Num(); i++)
					{
						if (FMemory::Memcmp(helper.GetKeyPtr(i), ptr, size) == 0)
						{
							value_ptr = helper.GetValuePtr(i);
							prop->ValueProp->CopySingleValue(old_value_ptr, value_ptr);
							FBinarySerializer::_BinaryArray2PropertyValue(prop->ValueProp, value_ptr, value, HN);
							helper.Rehash();
							bNotFound = false;
							break;
						}
					}
					if (bNotFound)
					{
						const int32 index = helper.AddDefaultValue_Invalid_NeedsRehash();
						uint8* cur_key_ptr = helper.GetKeyPtr(index);
						value_ptr = helper.GetValuePtr(index);
						prop->KeyProp->InitializeValue(cur_key_ptr);
						prop->ValueProp->InitializeValue(value_ptr);
						prop->KeyProp->CopySingleValue(cur_key_ptr, ptr);
						FBinarySerializer::_BinaryArray2PropertyValue(prop->ValueProp, value_ptr, value, HN);
						helper.Rehash();
					}

					bool has_old_value = !bNotFound;
					UFunction* rep_func = InEntity->FindFunction(*FString::Printf(TEXT("OnBaseSliceRep_%s_Add"), *InProperty->GetName()));
					if (rep_func)
					{
						int32 ksize;
						if (auto as_struct = Cast<UStructProperty>(prop->ValueProp))
							ksize = as_struct->Struct->GetCppStructOps()->GetAlignment();  // for sturcts data must be aligned with 8 bytes
						else
							ksize = prop->KeyProp->GetMinAlignment();
						int32 vsize = prop->ValueProp->GetSize();


						uint8* params = (uint8*)FMemory::Malloc(ksize + vsize + ksize + vsize);
						prop->KeyProp->InitializeValue(params);
						prop->ValueProp->InitializeValue(params + ksize);
						GetDefault<UBoolProperty>()->InitializeValue(params + ksize + vsize);
						prop->ValueProp->InitializeValue(params + ksize + vsize + ksize);

						FMemory::Memcpy(params, ptr, ksize);
						FMemory::Memcpy(params + ksize, value_ptr, vsize);
						FMemory::Memcpy(params + ksize + vsize, &has_old_value, ksize);
						FMemory::Memcpy(params + ksize + vsize + ksize, old_value_ptr, vsize);
						InEntity->ProcessEvent(rep_func, params);
						FMemory::Free(params);
					}


					FMemory::Free(ptr);
					FMemory::Free(old_value_ptr);

					break;
				}
				case ESliceReplicationKind::Clear:
				{
					PRINTHN("SliceRep: Clear the %s", *InProperty->GetName());
					prop->ClearValue_InContainer(InEntity);
					break;
				}
				case ESliceReplicationKind::RemoveEntry:
				{
					PRINTHN("SliceRep: Remove from %s", *InProperty->GetName());
					TArray<uint8> serialzied_key;
					serialization_proxy >> serialzied_key;

					TArray<uint8> key;
					TArray<uint8> value;
					auto kv_srp = FBinarySerializationProxy(serialzied_key);
					kv_srp >> key;

					const int32 size = prop->KeyProp->GetSize();
					const int32 value_size = prop->ValueProp->GetSize();
					uint8* ptr = (uint8*)FMemory::Malloc(size);
					uint8* old_value_ptr = (uint8*)FMemory::Malloc(value_size);
					prop->KeyProp->InitializeValue(ptr);
					prop->ValueProp->InitializeValue(old_value_ptr);
					FBinarySerializer::_BinaryArray2PropertyValue(prop->KeyProp, ptr, key, HN);
					FScriptMapHelper_InContainer helper(prop, InEntity);
					bool bNotFound = true;
					for (int32 i = 0; i < helper.Num(); i++)
					{
						if (FMemory::Memcmp(helper.GetKeyPtr(i), ptr, size) == 0)
						{
							FMemory::Memcpy(old_value_ptr, helper.GetValuePtr(i), value_size);
							helper.RemoveAt(i);
							bNotFound = false;
							break;
						}
					}
					if (bNotFound)
					{
						WARN_MSGHN("Unable to remove key from map %s: %s", *InProperty->GetName(), *Bytes2String(key));
						return false;
					}

					UFunction* rep_func = InEntity->FindFunction(*FString::Printf(TEXT("OnBaseSliceRep_%s_Remove"), *InProperty->GetName()));
					if (rep_func)
					{
						const int32 min_key_alignment = prop->KeyProp->GetMinAlignment();
						const int32 min_value_alignment = prop->ValueProp->GetMinAlignment();
						const int32 min_alignment = FMath::Max(min_key_alignment, min_value_alignment);

						uint8* params = (uint8*)FMemory::Malloc(min_alignment + value_size);

						prop->KeyProp->InitializeValue(params);
						prop->ValueProp->InitializeValue(params + min_alignment);

						prop->KeyProp->CopySingleValue(params, ptr);
						prop->ValueProp->CopySingleValue(params + min_alignment, old_value_ptr);

						InEntity->ProcessEvent(rep_func, params);
						FMemory::Free(params);
					}

					FMemory::Free(ptr);

					break;	
				}
				case ESliceReplicationKind::Extend:
				{
					ERROR_MSGHN("Extend replication for map not supported");
					return false;
				}
				case ESliceReplicationKind::Full:
				{
					PRINTHN("SliceRep: Full rep %s", *InProperty->GetName());
					TArray<uint8> serialzied_full;
					serialization_proxy >> serialzied_full;

					TArray<uint8> full;

					auto kv_srp = FBinarySerializationProxy(serialzied_full);
					kv_srp >> full;

					void* value_ptr = prop->ContainerPtrToValuePtr<void>(InEntity);
					FBinarySerializer::_BinaryArray2PropertyValue(prop, value_ptr, full, HN);

					UFunction* rep_func = InEntity->FindFunction(*FString::Printf(TEXT("OnBaseRep_%s"), *InProperty->GetName()));
					if (rep_func)
						InEntity->ProcessEvent(rep_func, nullptr);

					break;
				}

				default:
					return false;
			}
		}

		return true;
	}
};

template<>
struct FSliceReplicationHandler<ESliceReplicationDataType::Array>
{
	static bool Handle(UObject* InEntity, UProperty* InProperty, FBinarySerializationProxy& serialization_proxy, UHaloNetLibrary* HN)
	{
		int32 rep_kind;

		while (serialization_proxy >> rep_kind)
		{

		}

		return true;
	}
};

