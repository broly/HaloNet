import platform
import sys

from Core.Common.Colors import ColorPatternMapping

color_patterns_enabled = True


if platform.system() == "Windows":
    from ctypes import windll

    STD_OUTPUT_HANDLE = -11

    stdout_handle = windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    SetConsoleTextAttribute = windll.kernel32.SetConsoleTextAttribute

    def set_console_color(color):
        sys.stdout.flush()
        SetConsoleTextAttribute(stdout_handle, color)
        if color_patterns_enabled:
            print(ColorPatternMapping[color], end='')

    def set_default_console_color(color):
        sys.stdout.flush()
        SetConsoleTextAttribute(stdout_handle, color)
        if color_patterns_enabled:
            print(ColorPatternMapping[color])
        else:
            print()


else:
    def set_console_color(color):
        if color_patterns_enabled:
            print(ColorPatternMapping[color], end='')

    def set_default_console_color(color):
        if color_patterns_enabled:
            print(ColorPatternMapping[color])

