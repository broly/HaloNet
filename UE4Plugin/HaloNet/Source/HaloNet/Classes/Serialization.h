#pragma once

#include "HaloNet.h"
#include "Utils.h"
#include "JsonRaw.h"
#include "Algo/Accumulate.h"
#include "Serialization.generated.h"

class FBinarySerializer;

enum class ETextFormatValueType
{
	Simple = 0,
	Text = 1,
};

/**
 * Особая интерпретация байтового типа
 * В виду того, что у UE4 нет универсального байтового типа, 
 * мы используем массив байтов в качестве контейнера обернув его этой структурой 
 * (необходимо для передачи нетипизированной сериализованной информации)
 */
USTRUCT(BlueprintType)
struct FBytes
{
	GENERATED_USTRUCT_BODY()

public:
	FBytes()
		: Data({})
	{}

	FBytes(const TArray<uint8>& InData)
		: Data(InData)
	{}

	UPROPERTY()
	TArray<uint8> Data;
};

/**
 * Класс статических методов для сериализации\десериализации объектов для Divinity
 */
UCLASS()
class HALONET_API UE4ServiceSerializer : public UObject
{
	GENERATED_BODY()

public:
	

};

static const int32 COUNT_SIZE = 4;

namespace SharedPointerInternals
{
	/** Deletes an object via the standard delete operator */
	template <typename Type>
	struct FreeDeleter
	{
		FORCEINLINE void operator()(Type* Object) const
		{
			FMemory::Free(Object);
		}
	};
}


/**
 * Класс бинарного списка данных
 * Для склеивания\дробления бинарных данных
 * BinarySerialization
 */
class HALONET_API FBinarySerialization
{
public:

	FBinarySerialization()
		: bHasValidData(true)
	{}

	FBinarySerialization(uint8* InOther, int32 InSize)
	{
		bHasValidData = true;
		FromOther(InOther, InSize);
	}

	FBinarySerialization(TSharedPtr<uint8> InOther, int32 InSize)
	{
		bHasValidData = true;
		FromOther(InOther.Get(), InSize);
	}


	FBinarySerialization(TArray<uint8> InOther)
	{
		bHasValidData = true;
		FromOther(InOther.GetData(), InOther.Num());
	}

	~FBinarySerialization()
	{
		for (auto data : Datas)
			FMemory::Free(data);
	}

	void FromOther(TArray<uint8> InOther)
	{
		bHasValidData = true;
		FromOther(InOther.GetData(), InOther.Num());
	}


	void FromOther(uint8* InOther, int32 InSize)
	{
		bHasValidData = true;

		uint8* ptr = InOther;

		int32 data_count = 0;
		FMemory::Memcpy(&data_count, ptr, COUNT_SIZE);

		if (data_count >= 0)
		{
			int32 current_data_offset = 0;
			for (int32 index = 0; index < data_count; index++)
			{
				int32 count = 0;
				const int32 current_count_offset = COUNT_SIZE + (index * COUNT_SIZE);
				if (current_count_offset > InSize)
				{
					bHasValidData = false;
					break;
				}
				FMemory::Memcpy(&count, ptr + current_count_offset, COUNT_SIZE);
				DataCounts.Add(count);
				const int32 current_data_offset_full = COUNT_SIZE + (data_count * COUNT_SIZE) + current_data_offset;
				if (current_data_offset > InSize)
				{
					bHasValidData = false;
					break;
				}
				uint8* data = (uint8*)FMemory::Malloc(count);
				FMemory::Memcpy(data, ptr + current_data_offset_full, count);
				Datas.Add(data);
				current_data_offset += count;

			}
		}
		else
		{
			bHasValidData = false;
		}
	}

	void Add(const uint8* InData, int32 InCount)
	{
		uint8* copied = (uint8*)FMemory::Malloc(InCount);
		FMemory::Memcpy(copied, InData, InCount);
		Datas.Add(copied);
		DataCounts.Add(InCount);
	}

	FORCEINLINE void AddData(TArray<uint8> InData)
	{
		Add(InData.GetData(), InData.Num());
	}

	int32 Size() const
	{
		return Datas.Num();
	}

	void GetArchive(TSharedPtr<uint8>& OutArchive, int32& OutArchiveSize) const
	{
		const int32 data_count = DataCounts.Num();
		const int32 data_counts_size = COUNT_SIZE * DataCounts.Num();
		const int32 total_memory = COUNT_SIZE + data_counts_size + TotalSize();
		uint8* ptr = (uint8*)FMemory::Malloc(total_memory);

		// memset(ptr, 0, total_memory);
		FMemory::Memcpy(ptr, &data_count, COUNT_SIZE);
		FMemory::Memcpy(ptr + COUNT_SIZE, DataCounts.GetData(), COUNT_SIZE * DataCounts.Num());

		int32 current_data_offset = 0;
		for (int32 index = 0; index < Datas.Num(); index++)
		{
			FMemory::Memcpy(ptr + COUNT_SIZE + data_counts_size + current_data_offset, Datas[index], DataCounts[index]);
			current_data_offset += DataCounts[index];
		}

		const TSharedPtr<uint8> out(ptr, SharedPointerInternals::FreeDeleter<uint8>());
		OutArchive = out;
		OutArchiveSize = total_memory;
	}

	FORCEINLINE TArray<uint8> GetArchived() const
	{
		TArray<uint8> archive;
		TSharedPtr<uint8> arc_ptr;
		int32 size;
		GetArchive(arc_ptr, size);

		archive.Init(0, size);
		FMemory::Memcpy(archive.GetData(), arc_ptr.Get(), size);

		return archive;
	}

	void GetData(TArray<uint8*>& OutData, TArray<int32>& OutCounts) const
	{
		OutData = Datas;
		OutCounts = DataCounts;
	}

	TArray<uint8> GetByIndex(int32 index) const
	{
		TArray<uint8> ReturnValue;
		if (index < Size())
		{
			int32 count = DataCounts[index];
			ReturnValue.Init(0, count);
			FMemory::Memcpy(ReturnValue.GetData(), Datas[index], count);
		} 
		else checkf(false, TEXT("Access out of bounds"));
		return ReturnValue;
	}


	FORCEINLINE TArray<uint8> operator[](int32 index) const
	{
		return GetByIndex(index);
	}

	int32 TotalSize() const
	{
		return Algo::Accumulate(DataCounts, 0);
	}

	FORCEINLINE int32 Num() const
	{
		return Size();
	}

	bool IsValid() const
	{
		return bHasValidData;
	}
	
	FBinarySerialization& operator<<(int32 other);
	FBinarySerialization& operator<<(FString other);
	FBinarySerialization& operator<<(TArray<uint8> other);
	FBinarySerialization& operator<<(const FBinarySerialization& other);


	class FBinarySerializationProxy Proxy();

	
private:
	TArray<int32> DataCounts;
	TArray<uint8*> Datas;

	bool bHasValidData;
};



class HALONET_API FBinarySerializer
{
public:  /// Секция сериализующих функций 
	
	/**
	 * Преобразует численный тип в массив байтов
	 *
	 * @param value: переменная численного типа
	 * @return: массив байтов
	 */
	template<typename T>
	static TArray<uint8> FromInt(T value)
	{
		TArray<uint8> binary_data;

		const uint8* ptr = reinterpret_cast<const uint8*>(&value);
		for (int32 i = 0; i < sizeof(T); i++)
			binary_data.Add(ptr[i]);


		return binary_data;
	}

	/**
	 * Преобразует строчный тип в массив байтов
	 *
	 * @param value: переменная строчного типа
	 * @return: массив байтов
	 */
	static TArray<uint8> FromString(const FString& value);

	/**
	 * Преобразует структурный тип в массив байтов
	 *
	 * @param Value: переменная структурного типа
	 * @return: массив байтов
	 */
	template<typename T>
	static TArray<uint8> FromStruct(T Value)
	{
		UScriptStruct* st = Value.StaticStruct();
		TArray<uint8> result = _Struct2Binary(&Value, st);
		return result;
	}

public:  /// Секция десериализующих функций 
	
	/**
	 * Преобразует массив байтов в численный тип
	 * 
	 * @param binary_array массив байтов
	 * @return: численный тип
	 */
	template<typename T>
	static FORCENOINLINE T ToNumericValue(TArray<uint8> binary_array)
	{
		if (sizeof(T) <= binary_array.Num())
		{
			T* result = reinterpret_cast<T*>(binary_array.GetData());
			return *result;
		}
		return 0;
	}
	
	/**
	 * Преобразует массив байтов в строчный тип
	 * 
	 * @param binary_array массив байтов
	 * @return: строчный тип
	 */
	static FString ToStringValue(TArray<uint8> binary_array);

	static TArray<uint8> StringToBytes(FString string_value);

	/**
	 *
	 * @param divinity:
	 * @param binary_array:
	 */
	template<typename T>
	static TArray<uint8> FromMailbox(T* mailbox)
	{
		FString ip = "0.0.0.0";
		int32 port = 0;
		int32 id = 0;
		if (mailbox != nullptr)
		{
			auto conn = mailbox->GetConnection();
			if (conn != nullptr)
			{
				FIPv4Endpoint endpoint = conn->GetRemoteEndpoint();
				ip = endpoint.Address.ToString();
				port = endpoint.Port;
				id = mailbox->GetRemoteEntityID();
			}
		}
		auto data_list = FBinarySerialization();
		data_list.AddData( FBinarySerializer::FromString(ip) );
		data_list.AddData( FBinarySerializer::FromInt<int32>(port) );
		data_list.AddData( FBinarySerializer::FromInt<int32>(id) );
		return data_list.GetArchived();
	}

	/**
	 * Преобразует массив байтов в структурный тип
	 * 
	 * @param Value массив байтов
	 * @return: структурный тип
	 */
	template<typename T>
	static T ToStruct(T Struct, TArray<uint8> Value)
	{
		UScriptStruct* st = T::StaticStruct();
		_BinaryArrayToStruct(&Struct, st, Value);
		return Struct;
	}


	/// ADVANCED INNER SECTION

public:  /// Секция вспомогательных сериализующих и десериализующих функций
	/**
	 * Рефлексивное преобразование значения свойства в бинарные данные
	 * 
	 * @param Prop: указатель на данные свойства
	 * @param ValuePtr: указатель на фактические данные
	 * @return: массив байтов
	 */
	static TArray<uint8> _PropertyValue2BinaryArray(const UProperty* Prop, const void* ValuePtr);
	
	/**
	 * Рефлексивное преобразование структуры в бинарные данные
	 * 
	 * @param StructData: указатель на фактические данные
	 * @param StructStructure: указатель на данные структуры
	 * @return: массив байтов
	 */
	static TArray<uint8> _Struct2Binary(const void* StructData, UStruct* StructStructure);

	/**
	 * Рефлексивное преобразование бинарных данных в значение свойства
	 * 
	 * @param Prop: указатель данные свойства
	 * @param ValuePtr: указатель на фактические данные
	 * @param BinaryArray: массив байтов
	 */
	static void _BinaryArray2PropertyValue(UProperty* Prop, void* ValuePtr, TArray<uint8> BinaryArray, class UHaloNetLibrary* networking_instance);
	
	/**
	 * Рефлексивное преобразование структуры в бинарные данные
	 * 
	 * @param StructData: указатель на фактические данные
	 * @param Struct: указатель данные свойства
	 * @param BinaryArray: массив байтов
	 */
	static void _BinaryArrayToStruct(void* StructData, UStruct* Struct, TArray<uint8> BinaryArray, class UHaloNetLibrary* networking_instance);

public:  /// Секция сериализации\десериализации данных для структур

	template <typename T>
	static FORCEINLINE TArray<uint8> SerializeStruct(T Struct)
	{
		//static_assert(IsTypeUSTRUCT(T), "Excepting USTRUCT, but unknown type got");

		UStruct* st = Struct.StaticStruct();
		return _Struct2Binary(&Struct, st);
	}

	template <typename T>
	static FORCEINLINE T DeserializeStruct(T& Struct, TArray<uint8> data)
	{
		//static_assert(IsTypeUSTRUCT(T), "Excepting USTRUCT, but unknown type got");

		UScriptStruct* st = Struct.StaticStruct();
		_BinaryArrayToStruct(&Struct, st, data);
		return Struct;
	}

	static FText DeserializeText(TArray<uint8> data);
};




class FBinarySerializationProxy
{
public:
	FBinarySerializationProxy(FBinarySerialization* binary_serialization)
	{

		ArchivePtr = binary_serialization;
		index = 0;
		bTemp = false;
	}

	FBinarySerializationProxy(TArray<uint8>& data)
	{
		ArchivePtr = new FBinarySerialization(data);
		bTemp = true;
		index = 0;
	}

	~FBinarySerializationProxy()
	{
		if (bTemp)
			delete ArchivePtr;
	}

	bool HasAnyData() const
	{
		if (ArchivePtr)
			return ArchivePtr->Size() > index;
		return false;
	}

	explicit operator bool() const
	{
		return HasAnyData();
	}

	TArray<uint8> GetNext()
	{
		if (ArchivePtr)
			if (ArchivePtr->Size() > index)
			{
				return (*ArchivePtr)[index++];
			}
		return {};
	}

	/**
	 * Достать 4ёх байтное число из Proxy
	 * @param other: полученные данные
	 * @return успех операции
	 */
	FBinarySerializationProxy& operator>>(int32& other)
	{
		const bool success = HasAnyData();
		if (success)
		{
			TArray<uint8> data = GetNext();
			other = FBinarySerializer::ToNumericValue<int32>(data);
		}
		return *this;
	}
	
	/**
	 * Достать строку из Proxy
	 * @param other: полученные данные
	 * @return успех операции
	 */
	FBinarySerializationProxy& operator>>(FString& other)
	{
		const bool success = HasAnyData();
		if (success)
		{
			TArray<uint8> data = GetNext();
			other = FBinarySerializer::ToStringValue(data);
		}
		return *this;
	}
	
	/**
	 * Достать массив байтов из Proxy
	 * @param other: полученные данные
	 * @return успех операции
	 */
	FBinarySerializationProxy& operator>>(TArray<uint8>& other)
	{
		const bool success = HasAnyData();
		if (success)
			other = GetNext();
		return *this;
	}
	
	/**
	 * Достать другие сериализованные данные из Proxy
	 * @param other: полученные данные
	 * @return успех операции
	 */
	FBinarySerializationProxy& operator>>(FBinarySerialization& other)
	{
		const bool success = HasAnyData();
		if (success)
			other = FBinarySerialization(GetNext());
		return *this;
	}

private:

	int32 index;
	FBinarySerialization* ArchivePtr;

	bool bTemp;
	// TArray<TArray<uint8>> Data;
};
