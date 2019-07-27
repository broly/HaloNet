#include "memory"

using namespace std;

void pack_bytes(const char* Bytes, int BytesNum, shared_ptr<char>& OutPackedBytes, int& OutSize)
{
	char* data = new char[4 + BytesNum];
	memcpy(data, &BytesNum, 4);
	memcpy(data + 4, Bytes, BytesNum);

	OutSize = BytesNum + 4;
	OutPackedBytes = shared_ptr<char>(data, default_delete<char>());
}

void unpack_bytes(const char* InPackedBytes, int InSize, shared_ptr<char>& OutBytes, int& OutBytesNum)
{
    char* data = new char[InSize - 4];
    memcpy(&OutBytesNum, InPackedBytes, 4);
    memcpy(data, InPackedBytes + 4, InSize - 4);
    OutBytes = shared_ptr<char>(data, default_delete<char>());
}