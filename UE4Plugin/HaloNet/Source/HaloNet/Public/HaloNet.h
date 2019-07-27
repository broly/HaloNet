#pragma once

#include "Engine.h"

#include "IHaloNet.h"




#ifdef PLATFORM_WINDOWS
	#define RPC_EXECPTIONS_SUPPORTED 1
#else
	#define RPC_EXECPTIONS_SUPPORTED 0
#endif


class FHaloNet : public IHaloNet
{
	/** IModuleInterface implementation */
	virtual void StartupModule() override
	{

	}

	virtual void ShutdownModule() override
	{

	}


};

