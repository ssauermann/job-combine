"""
Bidirectional converters from str to timedelta

Supported format specifiers are:
    %D for days
    %H for hours
    %M for minutes
    %S for seconds
"""
import re
import sys
from datetime import timedelta


def str_to_timedelta(time_str, *formats):
    """
    Converts a string representation to a time delta
    :param time_str: Time string
    :param formats: Time formats (first matching will be used)
    :return: Time delta
    """

    for f in formats:
        pattern = f.replace('%D', '(?P<d>[0-9]+)')
        pattern = pattern.replace('%H', '(?P<h>[0-9]+)')
        pattern = pattern.replace('%M', '(?P<m>[0-9]+)')
        pattern = pattern.replace('%S', '(?P<s>[0-9]+)')
        match = re.match(r'^' + pattern + r'$', time_str)

        if match is None:
            continue

        def get_group(grp):
            try:
                return match.group(grp)
            except IndexError:
                return 0

        days = int(get_group('d'))
        hours = int(get_group('h'))
        minutes = int(get_group('m'))
        seconds = int(get_group('s'))

        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    raise ValueError('`%s` is not a supported time format: %s' % (time_str, ', '.join(formats)))


def str_from_timedelta(time_delta, time_format):
    """
    Converts a time delta to a string representation
    :param time_delta: Time delta
    :param time_format: Time format
    :return: Time string
    """

    remaining_time = time_delta
    days = hours = minutes = 0

    if '%D' in time_format:
        days = remaining_time.days
        remaining_time -= timedelta(days=days)

    if '%H' in time_format:
        hours = int(total_seconds(remaining_time) / (60 * 60))
        remaining_time -= timedelta(hours=hours)

    if '%M' in time_format:
        minutes = int(total_seconds(remaining_time) / 60)
        remaining_time -= timedelta(minutes=minutes)

    seconds = total_seconds(remaining_time)

    formatted = time_format.replace('%D', '%02d' % days)
    formatted = formatted.replace('%H', '%02d' % hours)
    formatted = formatted.replace('%M', '%02d' % minutes)
    formatted = formatted.replace('%S', '%02d' % seconds)

    return formatted


if sys.version_info >= (2, 7):
    def total_seconds(td):
        return td.total_seconds()
else:
    def total_seconds(td):
        return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 1e6) / 1e6
