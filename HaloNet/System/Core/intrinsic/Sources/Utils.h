#include <stdio.h>


typedef int int32;

void print_mem_as_chars(void* ptr, int32 size)
{
	char* copied = new char[size + 1];
	copied[size] = '\0';
	memcpy(copied, ptr, size);
	for (int32 i = 0; i < size; i++)
		if (copied[i] == 0)
			copied[i] = '?';
	printf("%s", copied);
	printf("\n");
	delete[] copied;
}


void print_mem_as_ints(void* ptr, int32 size)
{
	char* copied = new char[size + 1];
	copied[size] = '\0';
	memcpy(copied, ptr, size);
	for (int32 i = 0; i < size; i++)
	{
		printf("%u ", copied[i]);
	}
	printf("\n");
	delete[] copied;
}