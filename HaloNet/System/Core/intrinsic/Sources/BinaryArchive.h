
#include "vector"
#include "memory"
#include <numeric>

typedef int int32;

static const int32 COUNT_SIZE = 4;

using namespace std;


class BinaryArchive
{
public:
	BinaryArchive()
		: HasValidData(true)
	{}

	BinaryArchive(char* InOther, int32 InSize)
	{
		HasValidData = true;
		FromOther(InOther, InSize);
	}

	BinaryArchive(shared_ptr<char> InOther, int32 InSize)
	{
		HasValidData = true;
		FromOther(InOther.get(), InSize);
	}


	~BinaryArchive()
	{
		// for (auto data : Datas)
		// 	delete[] data;
	}


	void FromOther(char* InOther, int32 InSize)
	{
		HasValidData = true;

		char* ptr = InOther;

		int32 data_count = 0;
		memcpy(&data_count, ptr, COUNT_SIZE);

		if (data_count >= 0)
		{
			int32 current_data_offset = 0;
			for (int32 index = 0; index < data_count; index++)
			{
				int32 count = 0;
				const int32 current_count_offset = COUNT_SIZE + (index * COUNT_SIZE);
				if (current_count_offset > InSize)
				{
					HasValidData = false;
					break;
				}
				memcpy(&count, ptr + current_count_offset, COUNT_SIZE);
				DataCounts.push_back(count);
				const int32 current_data_offset_full = COUNT_SIZE + (data_count * COUNT_SIZE) + current_data_offset;
				if (current_data_offset > InSize)
				{
					HasValidData = false;
					break;
				}
				char* data = new char[count];
				memcpy(data, ptr + current_data_offset_full, count);
				Datas.push_back(data);
				current_data_offset += count;

			}
		}
		else
		{
			HasValidData = false;
		}
	}

	void Add(const char* InData, int32 InCount)
	{
		char* copied = new char[InCount];
		memcpy(copied, InData, InCount);
		Datas.push_back(copied);
		DataCounts.push_back(InCount);
	}

	int32 Size() const
	{
		return Datas.size();
	}

	void GetArchive(shared_ptr<char>& OutArchive, int32& OutArchiveSize)
	{
		const int32 data_count = DataCounts.size();
		const int32 data_counts_size = COUNT_SIZE * DataCounts.size();
		const int32 total_memory = COUNT_SIZE + data_counts_size + TotalSize();
		char* ptr = new char[total_memory];

		// memset(ptr, 0, total_memory);
		memcpy(ptr, &data_count, COUNT_SIZE);
		memcpy(ptr + COUNT_SIZE, DataCounts.data(), COUNT_SIZE * DataCounts.size());

		int32 current_data_offset = 0;
		for (int32 index = 0; index < Datas.size(); index++)
		{
			memcpy(ptr + COUNT_SIZE + data_counts_size + current_data_offset, Datas[index], DataCounts[index]);
			current_data_offset += DataCounts[index];
		}

		const shared_ptr<char> out(ptr, default_delete<char>());
		OutArchive = out;
		OutArchiveSize = total_memory;
	}

	void GetData(vector<char*>& OutData, vector<int32>& OutCounts) const
	{
		OutData = Datas;
		OutCounts = DataCounts;
	}

	int32 TotalSize()
	{
		return accumulate(DataCounts.begin(), DataCounts.end(), 0);
	}

	bool IsValid() const
	{
		return HasValidData;
	}

protected:
	vector<int32> DataCounts;
	vector<char*> Datas;

	bool HasValidData;
};
