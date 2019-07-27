from datetime import datetime
import math

class _timespan:
    TicksPerDay =    864_000_000_000
    TicksPerHour =    36_000_000_000
    TicksPerMicrosecond =         10
    TicksPerMillisecond =     10_000
    TicksPerMinute =     600_000_000
    TicksPerSecond =      10_000_000
    TicksPerWeek = 6_048_000_000_000

    DaysPerMonth = [0, 31, 28, 31,  30,  31,  30,  31,  31,  30,  31,  30,  31]
    DaysToMonth  = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365]

class _DateTime(datetime):
    def get_ticks(self):
        TotalDays = 0
        if self.month > 2 and self.is_leap_year(self.year):
            TotalDays += 1

        year = self.year - 1
        month = self.month - 1
        day = self.day
        hour = self.hour
        minute = self.minute
        seconds = self.second
        milliseconds = self.microsecond // 1000

        TotalDays += year * 365
        TotalDays += year // 4
        TotalDays -= year // 100
        TotalDays += year // 400
        TotalDays += _timespan.DaysToMonth[month]
        TotalDays += day - 1

        ticks = int(TotalDays * _timespan.TicksPerDay +
                    hour * _timespan.TicksPerHour +
                    minute * _timespan.TicksPerMinute +
                    seconds * _timespan.TicksPerSecond +
                    milliseconds * _timespan.TicksPerMillisecond)

        return ticks


    @staticmethod
    def is_leap_year(int year):
        if (year % 4) == 0:
            return (year % 100) != 0 or (year % 400) == 0
        return False

    @staticmethod
    def get_julian_day_by_ticks(long long ticks):
        return 1721425.5 + ticks / _timespan.TicksPerDay

    @staticmethod
    def get_date_by_ticks(long long ticks):
        l = math.floor(_DateTime.get_julian_day_by_ticks(ticks) + 0.5) + 68569
        n = 4 * l // 146097
        l = l - (146097 * n + 3) // 4
        i = 4000 * (l + 1) // 1461001
        l = l - 1461 * i // 4 + 31
        j = 80 * l // 2447
        k = l - 2447 * j // 80
        l = j // 11
        j = j + 2 - 12 * l
        i = 100 * (n - 49) + i + l

        year, month, day = int(i), int(j), int(k)

        return year, month, day

    @staticmethod
    def get_by_ticks(long long ticks):
        year, month, day = _DateTime.get_date_by_ticks(ticks)
        hour = int((ticks // _timespan.TicksPerHour) % 24)
        minute = int((ticks // _timespan.TicksPerMinute) % 60)
        second = int((ticks // _timespan.TicksPerSecond) % 60)
        millisecond = int((ticks // _timespan.TicksPerMillisecond) % 1000)
        return year, month, day, hour, minute, second, millisecond

