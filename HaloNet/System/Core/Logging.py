
import os
import sys
import logging
from logging.handlers import RotatingFileHandler

import raven

from Core.Common.Colors import Color
from Core.Common.Helpers import _debugbreak
from Core.Common.Platform import set_console_color, set_default_console_color
from Core.ConfigSystem.Bases import ConfigGlobals
from Core.Globals import Globals

__all__ = 'Log', 'INFO_MSG', 'PRINT', 'ERROR_MSG', 'WARN_MSG', 'CRITICAL_MSG'

from time import time
from datetime import datetime

ENABLE_TIMESTAMP = True

sentry_client = None
if ConfigGlobals.Sentry:
    sentry_client = raven.Client(ConfigGlobals.Sentry, auto_log_stacks=True)


def capture_log(msg=None, tags=None):
    if sentry_client:
        tags = tags or {}
        _, exception, _ = sys.exc_info()
        tags['exception'] = exception
        tags['msg'] = msg
        with sentry_client.context:
            sentry_client.context.merge({
                'tags': tags,
            })
            try:
                if exception:
                    sentry_client.captureException()
                else:
                    sentry_client.captureMessage(msg)
            finally:
                sentry_client.context.clear()


def get_tab_length():
    if ConfigGlobals.OutputEntryStyle == OutputStyle.FullPythonStyle:
        return 100
    elif ConfigGlobals.OutputEntryStyle == OutputStyle.CPPStyle:
        return 50
    elif ConfigGlobals.OutputEntryStyle == OutputStyle.ShortInformative:
        return 40
    elif ConfigGlobals.OutputEntryStyle == OutputStyle.Absent:
        return 0


# print_function = print
# logging.basicConfig(filename=Configuration().get_globals().get("logging_filename", ".log"), filemode='a', level=logging.INFO)
# print_function = logging.info

class NullFormater():
    def format(self, record):
        return record

logging_filename = ConfigGlobals.LoggingFilename
file_handler = None
if logging_filename:
    logging_filename = f'{logging_filename}_{os.getpid()}.log'
    file_handler = RotatingFileHandler(logging_filename, maxBytes=10*1024*1024, backupCount=9, encoding='utf-8')
    file_handler.formatter = NullFormater()


def dump_to_logfile(arg, *args, **kwargs):
    if file_handler:
        file_handler.handle(arg)


class Log:
    """ Объявление новой категории лога

    @param log_name: название категории
    @param context: контекст лога (None если нет четкого контекста)
    @param color_pattern: цветовой паттерн для выделения цветом в логе
    @param action: дополнительное действие при логе
    @param specific_source: специфичный источник сообщения
    @param enabled: активирован ли вывод для этой категории?
    @param debug_break: приостанавливать ли выполнение при выводе сообщения в эту категорию?
    @return: новый логгер
    """

    def __init__(self, log_name, context, color, action=None, specific_source=None, enabled=True, debug_break=False, log_category=logging.INFO, warning_id=None):
        self.log_name = log_name
        self.context = context
        self.color = color
        self.action = action
        self.specific_source = specific_source
        self.enabled = enabled
        self.debug_break = debug_break
        self.log_category = log_category
        self.once_buffer = set()

    def __call__(self, message, *args, once=None, depth=0, warning_id=None, category=None, stack_level=0, captured=False, tags=None, **kwargs):
        suppressed_warnings = ConfigGlobals.SuppressedWarnings
        if self.enabled \
                and not Globals.no_logging \
                and self.log_name not in Globals.disabled_log_categories \
                and once not in self.once_buffer\
                and warning_id not in suppressed_warnings:
            color = self.color if Globals.colored_output else ""
            end_color = '\033[0m' if Globals.colored_output else ""

            path = get_output_entry_string(depth) if not self.specific_source else\
                output_offset_msg(self.specific_source)
            context_str = output_offset_msg_2(self.context) + output_offset_msg("") if self.context is not None else \
                output_offset_msg_2(Globals.service_name) + path

            timestamp = ""
            if ENABLE_TIMESTAMP:
                timestamp = datetime.fromtimestamp(time()).strftime('%Y-%m-%d %H:%M:%S') + " "

            set_console_color(color)
            print('%s%s%s: ' % (timestamp, context_str, self.log_name), message, *args, end='')
            set_default_console_color(Color.Standard)

            dump_to_logfile('%s %s %s##%s: %s' % (timestamp, self.context if self.context else (Globals.service_name if Globals.service_name else None), path, self.log_name, message))

            if not captured and self.log_category >= logging.ERROR:
                try:
                    msg = str(message) + ((" " + repr(args)) if args else "")
                    capture_log(msg=msg, tags=tags)
                except Exception as e:
                    from traceback import print_exc
                    if sentry_client:
                        sentry_client.captureException()
                    print_exc()
            if self.action is not None:
                self.action()
            if self.debug_break:
                _debugbreak()  # FIXME: Put breakpoint here

        if once:
            self.once_buffer.add(once)


# Список логгеров
PRINT =             Log("PRINT",               None, Color.White,                         log_category=logging.INFO,  enabled=True)  # Обычный вывод на экран
LOCK_LOG =          Log("LOCK INFO",           None, Color.White,                         log_category=logging.INFO,  enabled=True)
WARN_MSG =          Log("WARNING",             None, Color.Yellow,                        log_category=logging.WARN,  enabled=True)  # Предупреждение
DEPR_MSG =          Log("DEPRECATION WARNING", None, Color.Yellow,                        log_category=logging.WARN,  enabled=True)  # Предупреждение о возражении
ERROR_MSG =         Log("ERROR",               None, Color.LightRed,   debug_break=True,  log_category=logging.ERROR, enabled=True)  # Ошибка
SILENT_ERROR_MSG =  Log("ERROR",               None, Color.LightRed,   debug_break=False, log_category=logging.ERROR, enabled=True)  # Тихая ошибка
INFO_MSG =          Log("INFO",                None, Color.LightBlue,                     log_category=logging.INFO,  enabled=True)  # Информация
EMPHASIS =          Log("EMPHASIS",            None, Color.LightGreen, debug_break=True)                                             # Особое внимание
CRITICAL_MSG =      Log("CRITICAL",            None, Color.LightRed,   debug_break=True,  log_category=logging.FATAL, enabled=True)  # Критическое сообщение
ASSERT_MSG =        Log("ASSERTION FAILED",    None, Color.LightRed,   debug_break=True,  log_category=logging.FATAL, enabled=True)  # Сообщение об ассершине

# GEN_INFO = Log("GENERATING", 'Generator', '\033[34m')                                # Информация из генератора
# GEN_HINT = Log("HINT", 'Generator', '\x1b[1;37m')                                    # Подсказка из генератора

from Core.ConfigSystem.Bases import ConfigGlobals, OutputStyle


def get_output_entry_string(depth=0):
    method_space = sys._getframe(2 + depth)
    if ConfigGlobals.OutputEntryStyle == OutputStyle.FullPythonStyle:
        msg = 'File "%s", line %s, in %s' % (method_space.f_code.co_filename, method_space.f_lineno, method_space.f_code.co_name)
        char_count = len(msg)
        return msg + " " * (get_tab_length() - char_count) + "\t"
    elif ConfigGlobals.OutputEntryStyle == OutputStyle.Absent:
        return ""
    elif ConfigGlobals.OutputEntryStyle == OutputStyle.CPPStyle:
        if 'self' in method_space.f_locals:
            the_class_name = method_space.f_locals["self"].__class__.__name__
        else:
            the_class_name = "<unknown>"
        the_method_name = method_space.f_code.co_name
        msg = the_class_name + "::" + the_method_name
        char_count = len(msg)
        return msg + " " * (get_tab_length() - char_count) + "\t"
    elif ConfigGlobals.OutputEntryStyle == OutputStyle.ShortInformative:
        the_method_name = method_space.f_code.co_name
        fname = method_space.f_code.co_filename.replace("\\", "/")
        msg = fname[fname.rfind("/") + 1:] + ":" + str(method_space.f_lineno) + " " + the_method_name
        msg = msg[:40] + ('...' if len(msg) > 40 else '')
        char_count = len(msg)
        return msg + " " * (get_tab_length() - char_count) + "\t"


def output_offset_msg(msg):
    char_count = len(msg)
    return msg + " " * (get_tab_length() - char_count) + "\t"


def output_offset_msg_2(msg):
    char_count = len(msg)
    return msg + " " * (15 - char_count) + "\t"

def decay_log_line(log_line):
    pass