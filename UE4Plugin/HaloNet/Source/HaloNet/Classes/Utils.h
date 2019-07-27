#pragma once

#include "HaloNet.h"
#include "Engine.h"
#include "Engine/Engine.h"
#include "Sockets.h"
#include "Networking.h"
// #include "Future.generated.h"


/**
 * Возвращает общее количество миллисекунд до текущего момента
 */
HALONET_API inline double NowSeconds();

/**
 * Создаёт новый эндпоинт по IP и порту
 */
HALONET_API FIPv4Endpoint IPPort2Endpoint(FString ip, uint16 port);

/**
 * Типы пришедших сообщений
 */
enum class EConnectionMessageTypes : uint8
{
	RPC_Call,
	RPC_Future,
	RPC_Error,
	RPC_Exception,
};

enum class ENoneWaiterResult : uint8
{
	None,
};

DEFINE_LOG_CATEGORY_STATIC(TestLog, Log, Log);

/**
 * Объявляет функцию-выполнение для удалённого метода (для рефлексивной итерации, см. ExecuteMethodCall), используется в генерации кода
 */
#define RPC_EXEC(method_name) \
	DECLARE_FUNCTION(exec##method_name)\
	{\
		if (!ensureMsgf(Context->IsValidLowLevel() && !Context->IsUnreachable(), TEXT("Call to invalid mailbox (method %s)"), TEXT(#method_name))) \
			return; \
		FName func_name = GET_FUNCTION_NAME_CHECKED(ThisClass, method_name); \
		if (auto MailboxContext = Cast<UMailbox>(Context)) \
			MailboxContext->ExecuteMethodCall(func_name, Stack, RESULT_PARAM); \
		P_FINISH; \
	}

 /* Макросы для обработки множественных __VA_ARGS__ параметров. Используются для генерации кода */

#define __HN_EXPAND(x) x
#define __HN_ZIP_FOR_EACH_1(what, delimiter, ...)
#define __HN_ZIP_FOR_EACH_2(what, delimiter, x, y) what(x, y)
#define __HN_ZIP_FOR_EACH_4(what, delimiter, x, y, ...)\
  what(x, y) delimiter \
  __HN_EXPAND(__HN_ZIP_FOR_EACH_2(what, delimiter, __VA_ARGS__))
#define __HN_ZIP_FOR_EACH_6(what, delimiter, x, y, ...)\
  what(x, y) delimiter \
  __HN_EXPAND(__HN_ZIP_FOR_EACH_4(what, delimiter, __VA_ARGS__))
#define __HN_ZIP_FOR_EACH_8(what, delimiter, x, y, ...)\
  what(x, y) delimiter \
  __HN_EXPAND(__HN_ZIP_FOR_EACH_6(what, delimiter, __VA_ARGS__))
#define __HN_ZIP_FOR_EACH_10(what, delimiter, x, y, ...)\
  what(x, y) delimiter \
  __HN_EXPAND(__HN_ZIP_FOR_EACH_8(what, delimiter, __VA_ARGS__))
#define __HN_ZIP_FOR_EACH_12(what, delimiter, x, y, ...)\
  what(x, y) delimiter \
  __HN_EXPAND(__HN_ZIP_FOR_EACH_10(what, delimiter, __VA_ARGS__))
#define __HN_ZIP_FOR_EACH_14(what, delimiter, x, y, ...)\
  what(x, y) delimiter \
  __HN_EXPAND(__HN_ZIP_FOR_EACH_12(what, delimiter, __VA_ARGS__))
#define __HN_ZIP_FOR_EACH_16(what, delimiter, x, y, ...)\
  what(x, y) delimiter \
  __HN_EXPAND(__HN_ZIP_FOR_EACH_14(what, delimiter, __VA_ARGS__))
#define __HN_ZIP_FOR_EACH_18(what, delimiter, x, y, ...)\
  what(x, y) delimiter \
  __HN_EXPAND(__HN_ZIP_FOR_EACH_16(what, delimiter, __VA_ARGS__))
#define __HN_ZIP_FOR_EACH_20(what, delimiter, x, y, ...)\
  what(x, y) delimiter \
  __HN_EXPAND(__HN_ZIP_FOR_EACH_18(what, delimiter, __VA_ARGS__))
#define __HN_ZIP_FOR_EACH_22(what, delimiter, x, y, ...)\
  what(x, y) delimiter \
  __HN_EXPAND(__HN_ZIP_FOR_EACH_20(what, delimiter, __VA_ARGS__))
#define __HN_ZIP_FOR_EACH_24(what, delimiter, x, y, ...)\
  what(x, y) delimiter \
  __HN_EXPAND(__HN_ZIP_FOR_EACH_22(what, delimiter, __VA_ARGS__))
#define __HN_ZIP_FOR_EACH_26(what, delimiter, x, y, ...)\
  what(x, y) delimiter \
  __HN_EXPAND(__HN_ZIP_FOR_EACH_24(what, delimiter, __VA_ARGS__))
#define __HN_ZIP_FOR_EACH_28(what, delimiter, x, y, ...)\
  what(x, y) delimiter \
  __HN_EXPAND(__HN_ZIP_FOR_EACH_26(what, delimiter, __VA_ARGS__))
#define __HN_ZIP_FOR_EACH_30(what, delimiter, x, y, ...)\
  what(x, y) delimiter \
  __HN_EXPAND(__HN_ZIP_FOR_EACH_28(what, delimiter, __VA_ARGS__))


#define __HN_ZIP_FOR_EACH_NARG(...) __HN_ZIP_FOR_EACH_NARG_(__VA_ARGS__, __HN_ZIP_FOR_EACH_RSEQ_N())
#define __HN_ZIP_FOR_EACH_NARG_(...) __HN_EXPAND(__HN_ZIP_FOR_EACH_ARG_N(__VA_ARGS__))
#define __HN_ZIP_FOR_EACH_ARG_N(_1, _2, _3, _4, _5, _6, _7, _8, _9, _10, _11, _12, _13, _14, _15, _16, _17, _18, _19, _20, _21, _22, _23, _24, _25, _26, _27, _28, _29, _30, N, ...) N
#define __HN_ZIP_FOR_EACH_RSEQ_N() 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0
#define __HN_CONCATENATE(x,y) x##y
#define __HN_ZIP_FOR_EACH_(N, what, delimiter, ...) __HN_EXPAND(__HN_CONCATENATE(__HN_ZIP_FOR_EACH_, N)(what, delimiter, __VA_ARGS__))

#define __HN_ZIP_FOR_EACH(what, delimiter, ...) __HN_ZIP_FOR_EACH_(__HN_ZIP_FOR_EACH_NARG(__VA_ARGS__), what, delimiter, __VA_ARGS__)


/* / конец объявлений макросов для множественных параметров */

/** Объявление вызываемого параметра внутри структуры (тип и имя), используется для генерации */
#define REMOTE_CALLER_DEFINE_PARAM(param_type, param_name) param_type param_name

/** Определение вызываемого параметра вне структуры (тип и имя), используется для генерации */
#define REMOTE_CALLER_DECLARE_PARAM(param_type, param_name) parms.param_name = param_name;

/** Определение тела RPC метода (структура параметров и последующий вызов CustomThunk-функции с этими параметрами по имени) */
#define REMOTE_CALLER_RETVAL(future_type, remote_func_name, ...) \
	{\
		if (!ensureMsgf(IsValidLowLevel() && !IsUnreachable(), TEXT("Call to invalid mailbox (method %s)"), TEXT(#remote_func_name)))\
			return nullptr;\
		struct\
		{\
			__HN_ZIP_FOR_EACH(REMOTE_CALLER_DEFINE_PARAM, ;, ##__VA_ARGS__);\
			future_type future;\
		} parms;\
		__HN_ZIP_FOR_EACH(REMOTE_CALLER_DECLARE_PARAM, ;, ##__VA_ARGS__); \
		UFunction* func = FindFunction(TEXT(#remote_func_name)); \
		ProcessEvent(func, &parms); \
		return parms.future;\
	}

#define REMOTE_CALLER(remote_func_name, ...) \
	{\
		if (!ensureMsgf(IsValidLowLevel() && !IsUnreachable(), TEXT("Call to invalid mailbox (method %s)"), TEXT(#remote_func_name)))\
			return;\
		struct\
		{\
			__HN_ZIP_FOR_EACH(REMOTE_CALLER_DEFINE_PARAM, ;, ##__VA_ARGS__);\
		} parms;\
		__HN_ZIP_FOR_EACH(REMOTE_CALLER_DECLARE_PARAM, ;, ##__VA_ARGS__); \
		UFunction* func = FindFunction(TEXT(#remote_func_name)); \
		ProcessEvent(func, &parms); \
	}

/** Определение тела метода, возвращаего значение по фьючерсе (структура параметров и последующий вызов CustomThunk-функции с этими параметрами по имени) */
#define REMOTE_RETURNER(...) \
	{\
		struct\
		{\
			__HN_ZIP_FOR_EACH(REMOTE_CALLER_DEFINE_PARAM, ;, ##__VA_ARGS__);\
		} parms;\
		__HN_ZIP_FOR_EACH(REMOTE_CALLER_DECLARE_PARAM, ;, ##__VA_ARGS__); \
		UFunction* func = FindFunction(TEXT("ExecuteReturn")); \
		ProcessEvent(func, &parms); \
	}

/** Объявляет функцию-выполнение для возврата значения удалённого метода по фьючерсу (для рефлексивной итерации, см. ProcessExecuteReturn), используется в генерации кода  */
#define RET_EXEC(func_name) \
	DECLARE_FUNCTION(exec##func_name)\
	{\
		FName func_name = GET_FUNCTION_NAME_CHECKED(ThisClass, func_name); \
		if (auto WaiterContext = Cast<UWaiter>(Context)) \
		{ \
			UFunction* func = WaiterContext->FindFunction(func_name); \
			WaiterContext->ProcessExecuteReturn(func, Stack); \
		} \
		P_FINISH; \
	}

/** 
 * Декларативный синтаксис ожидания результата удалённой функции в контексте UObject. 
 * Внутри обычных объектов используйте "await_unsafe" вместо "await" 
 */
#define await ->MakeContext(this) <<

/**
 * Декларативный синтаксис ожидания ошибки удалённой функции 
 * Используйте только вместе с await\await_unsafe
 */
#define errawait > 

/** 
 * Декларативный синтаксис ожидания результата удалённой функции в контексте любого объекта. 
 * Внутри UObject'ов используйте "await" вместо "await_unsafe"
 */
#define await_unsafe ->MakeContext(nullptr) >>

/**
 *
 */
#define await_by(obj) ->MakeContext(obj) <<

/**
 * Записать значение в вейтер (эмуляция возврата значения асинхронной функции)
 */
#define giveback __waiter__->__derefer() = 



enum class ESagaLogsHN : uint8
{
	PrintLog,
	InfoLog,
	WarnLog,
	ErrorLog,
	GenericLog
};


inline bool VARARGS DebugLogFormattedHN(ESagaLogsHN LogCategory, bool silent, FColor DisplayColor, const TCHAR* const OutDeviceColor, const TCHAR* additionalMsg, const TCHAR* FormattedMsg, ...)
{
	const int32 DercriptionSize = 4096;
	TCHAR Description[DercriptionSize];
	GET_VARARGS(Description, DercriptionSize, DercriptionSize - 1, FormattedMsg, FormattedMsg);

#if !UE_BUILD_SHIPPING
	if (GEngine && !silent)
		GEngine->AddOnScreenDebugMessage(-1, 25.0f, DisplayColor, FString::Printf(TEXT("%s"), Description));
#endif

	FFileHelper::SaveStringToFile(FString(Description) + TEXT("\r\n"), TEXT("TestLog.log"), FFileHelper::EEncodingOptions::AutoDetect, &IFileManager::Get(), FILEWRITE_Append);

	FString res = FString::Printf(TEXT("%s\t\n%s"), Description, additionalMsg);
	const TCHAR* logDescr = additionalMsg != nullptr ? *res : Description;

	SET_WARN_COLOR(OutDeviceColor);
	switch (LogCategory)
	{
	case ESagaLogsHN::PrintLog:
		UE_LOG(TestLog, Log, TEXT("%s"), logDescr);
		break;
	case ESagaLogsHN::InfoLog:
		UE_LOG(TestLog, Log, TEXT("%s"), logDescr);
		break;
	case ESagaLogsHN::WarnLog:
		UE_LOG(TestLog, Log, TEXT("%s"), logDescr);
		break;
	case ESagaLogsHN::ErrorLog:
		UE_LOG(TestLog, Log, TEXT("%s"), logDescr);
		break;
	case ESagaLogsHN::GenericLog:
		UE_LOG(TestLog, Log, TEXT("%s"), logDescr);
		break;
	default:
		ensureMsgf(false, TEXT("Unknown log message!"));
	}
	CLEAR_WARN_COLOR();

	return false;
}


template<typename T>
FString GetStructNameHN()
{
	return GetNameSafe(T::StaticStruct());
}

#define GET_CALLSTACK() \
	 *FString::Printf(TEXT("File %s at %i in %s\nTraceback: %s"), ANSI_TO_TCHAR(__FILE__), __LINE__, ANSI_TO_TCHAR(__FUNCTION__), *FFrame::GetScriptCallstack())

/**
 * Output to log and screen
 */
#define PRINTHN(txt, ...) DebugLogFormattedHN(ESagaLogsHN::PrintLog, false, FColor::Yellow, COLOR_DARK_YELLOW, nullptr, TEXT(txt), ##__VA_ARGS__)

#define INFO_MSGHN(txt, ...) DebugLogFormattedHN(ESagaLogsHN::InfoLog, false, FColor::Blue, COLOR_BLUE, nullptr, TEXT(txt), ##__VA_ARGS__)

#define SILENT_INFO_MSGHN(txt, ...) DebugLogFormattedHN(ESagaLogsHN::InfoLog, true, FColor::Blue, COLOR_BLUE, nullptr, TEXT(txt), ##__VA_ARGS__)

#define WARN_MSGHN(txt, ...) DebugLogFormattedHN(ESagaLogsHN::WarnLog, false, FColor::Magenta, COLOR_PURPLE, nullptr, TEXT(txt), ##__VA_ARGS__) 

#define ERROR_MSGHN(txt, ...) DebugLogFormattedHN(ESagaLogsHN::ErrorLog, false, FColor::Red, COLOR_RED, nullptr, TEXT(txt), ##__VA_ARGS__)

/**
 * Перевод байтов в читаемую строку
 * @param bytes: байты
 * @return строка
 */
HALONET_API inline FString Bytes2String(const TArray<uint8>& bytes)
{
	FString str;
	for (int32 i = 0; i < bytes.Num(); i++)
	{
		if (bytes[i] < 16)
			str.Append(FString::Printf(TEXT("\\0x%i"), bytes[i]));
		else
			str.AppendChar(bytes[i]);
	}

	return str;
}

/** Пустой результат вейтера */
#define NoneResult ENoneWaiterResult::None

template<typename T>
using TBaseMailbox = typename T::BaseMailbox;

template<typename T>
using TUe4Mailbox = typename T::Ue4Mailbox;

template<typename T>
using TMailbox = TUe4Mailbox<T>;
