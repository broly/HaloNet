#include "HaloNet.h"
#include "Utils.h"
#include "Mailbox.h"

double NowSeconds()
{
	FDateTime now_time = FDateTime::Now();
	FTimespan time = FTimespan(now_time.GetDay(), now_time.GetHour(), now_time.GetMinute(), now_time.GetSecond(), now_time.GetMillisecond());
	return (time.GetTotalMilliseconds() / 1000.0f);
}


FIPv4Endpoint IPPort2Endpoint(FString ip, uint16 port)
{
	FIPv4Address addr;

	TArray<FString> Tokens;

	if (ip.ParseIntoArray(Tokens, TEXT("."), false) == 4)
	{
		addr.A = FCString::Atoi(*Tokens[0]);
		addr.B = FCString::Atoi(*Tokens[1]);
		addr.C = FCString::Atoi(*Tokens[2]);
		addr.D = FCString::Atoi(*Tokens[3]);

	}

	FIPv4Endpoint endp = FIPv4Endpoint(addr, port);

	INFO_MSGHN("IPPort2Endpoint %s", *endp.ToString());

	return endp;
}
