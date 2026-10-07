package com.tiger.ziwei.core

import com.nlf.calendar.Lunar
import com.nlf.calendar.Solar
import java.time.LocalDate

object TigerCalendar {
    fun normalizeBirth(input: BirthInput): BirthData {
        require(input.gender == "female" || input.gender == "male")
        require(input.calendar_type == "solar" || input.calendar_type == "lunar")
        require(input.birth_hour in 0..23 && input.birth_minute in 0..59)
        require(input.birthplace.isNotBlank())
        val solar = if (input.calendar_type == "lunar") {
            val year = requireNotNull(input.lunar_year)
            val month = requireNotNull(input.lunar_month)
            val day = requireNotNull(input.lunar_day)
            require(input.birth_year == null && input.birth_month == null && input.birth_day == null && input.is_leap_month != null)
            toSolar(LunarDateResult(year, month, day, input.is_leap_month == true))
        } else {
            require(input.lunar_year == null && input.lunar_month == null && input.lunar_day == null && input.is_leap_month == null)
            LocalDate.of(requireNotNull(input.birth_year), requireNotNull(input.birth_month), requireNotNull(input.birth_day))
        }
        return BirthData(
            name = input.name?.trim()?.ifEmpty { null }, gender = input.gender,
            birth_year = solar.year, birth_month = solar.monthValue, birth_day = solar.dayOfMonth,
            birth_hour = input.birth_hour, birth_minute = input.birth_minute,
            birthplace = input.birthplace.trim(),
        )
    }

    fun toLunar(date: LocalDate): LunarDateResult {
        val lunar = Solar.fromYmd(date.year, date.monthValue, date.dayOfMonth).lunar
        return LunarDateResult(lunar.year, kotlin.math.abs(lunar.month), lunar.day, lunar.month < 0)
    }

    fun toSolar(date: LunarDateResult): LocalDate {
        require(date.year in 1..9999 && date.month in 1..12 && date.day in 1..30)
        val month = if (date.is_leap_month) -date.month else date.month
        val solar = Lunar.fromYmd(date.year, month, date.day).solar
        val result = LocalDate.of(solar.year, solar.month, solar.day)
        require(toLunar(result) == date) { "invalid lunar date" }
        return result
    }

    fun calendar(birth: BirthData): CalendarResult = calendar(
        LocalDate.of(birth.birth_year, birth.birth_month, birth.birth_day),
        birth.birth_hour,
        birth.birth_minute,
    )

    fun calendar(date: LocalDate, hour: Int, minute: Int): CalendarResult {
        val lunar = Solar.fromYmdHms(date.year, date.monthValue, date.dayOfMonth, hour, minute, 0).lunar
        val lunarDate = LunarDateResult(lunar.year, kotlin.math.abs(lunar.month), lunar.day, lunar.month < 0)
        val day = GanzhiResult(lunar.dayGan, lunar.dayZhi)
        val hourBranchIndex = ((hour + 1) / 2) % 12
        val hourGanzhi = GanzhiResult(
            HEAVENLY_STEMS[(HEAVENLY_STEMS.indexOf(day.heavenly_stem) * 2 + hourBranchIndex) % 10],
            EARTHLY_BRANCHES[hourBranchIndex],
        )
        return CalendarResult(
            solar_date = date.toString(),
            solar_time = "%02d:%02d:00".format(java.util.Locale.ROOT, hour, minute),
            lunar_date = lunarDate,
            year_ganzhi = GanzhiResult(lunar.yearGan, lunar.yearZhi),
            month_ganzhi = GanzhiResult(lunar.monthGan, lunar.monthZhi),
            day_ganzhi = day,
            hour_ganzhi = hourGanzhi,
        )
    }

    fun lunarYearGanzhi(year: Int): GanzhiResult {
        val lunar = Lunar.fromYmd(year, 1, 1)
        return GanzhiResult(lunar.yearGan, lunar.yearZhi)
    }

    fun lunarMonthGanzhi(year: Int, month: Int): GanzhiResult {
        val yearStem = lunarYearGanzhi(year).heavenly_stem
        val firstStem = (HEAVENLY_STEMS.indexOf(yearStem) * 2 + 2) % 10
        return GanzhiResult(
            HEAVENLY_STEMS[(firstStem + month - 1) % 10],
            EARTHLY_BRANCHES[(month + 1) % 12],
        )
    }
}
