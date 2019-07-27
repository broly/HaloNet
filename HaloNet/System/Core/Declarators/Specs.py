from Core.Specifiers import declspec, END_SPECIFIERS

# Methods specifiers
Exposed:                        declspec("Метод/Сущность имеет доступ для вызовов с клиента UE4") = 0
CaptureConnection:              declspec("Первым параметром этого метода будет коннекшин вызова") = 1
BlueprintCallable:              declspec("Метод может быть вызван из BP") = 2
BlueprintNativeEvent:           declspec("Метод наследуется в С++ и в BP") = 3
BlueprintImplementableEvent:    declspec("Метод наследуется в BP") = 4
Exec:                           declspec("Метод/Сущность имеет доступ с косноли клиента UE4") = 5
Native:                         declspec("Метод вызывается без использования виртуальной машины UE4") = 6
Latent:                         declspec("Результат этого метода можно ожидать в Blueprint") = 7
SystemInternal:                 declspec("Метод уже реализован уровнем выше и не генерируется в интерфейсе") = 8
CaptureAccessToken:             declspec("Добавить параметр токена доступа") = 9
WithTimeout:                    declspec("Добавить таймаут метдоу (указать дополнительно)") = 10
DeferredReturn:                 declspec("Возвращаемое значение будет отправлено позже, чем выполнится функция (для клиента C++)") = 11


# Types specifiers
Blueprintable:                  declspec("Спецификатор для USTRUCT") = 20
BlueprintType:                  declspec("Спецификатор для USTRUCT") = 21
Private:                        declspec("Приватный тип") = 22
Local:                          declspec("Локальная структура") = 23

# Enum field specifiers
Hidden:                         declspec("Скрытое поле перечисления") = 30

# Properties specifiers
Persistent:                     declspec("Свойство персистентно (сохраняется в БД)") = 40
Transactional:                  declspec("Свойство транзакционно (переменную можно менять только в транзакциях)") = 41
Replicated:                     declspec("Свойство реплицируемо (реплицируется на клиент)") = 42
PartialRep_EXPERIMENTAL:        declspec("Частично-реплицируемое свойство. Экспериментальный. "
                                         "Может работать не стабильно. Сейчас используется ТОЛЬКО ДЛЯ МАП!") = 43


AvailableEverywhere:            declspec("Хранилище доступно на клиенте") = 50

Multicast:                      declspec("Класс с мультикастовым клиентским мейлбоксом") = 60

DisplayThis:                    declspec("Спецификатор для мониторинга переменной (не следует использовать в метаданных Property)") = 70


__Async:                        declspec("Асинхронный метод") = 17

END_SPECIFIERS()