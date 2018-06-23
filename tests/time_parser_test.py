import pytest

from job_combine.utils.time_parser import *


def assert_time_str(a, b, sep=':'):
    for x, y in zip(a.split(sep), b.split(sep)):
        assert int(x) == int(y)


def test_parse_str1():
    result = str_to_timedelta('1-2-3', '%H-%M-%S')
    assert result == timedelta(hours=1, minutes=2, seconds=3)


def test_parse_str2():
    result = str_to_timedelta('1:2', '%D:%S')
    assert result == timedelta(days=1, seconds=2)


def test_parse_str3():
    result = str_to_timedelta('0:62', '%M:%S')
    assert result == timedelta(minutes=1, seconds=2)


def test_parse_str_multiple():
    result = str_to_timedelta('1:2', '%M:%S', '%H:%M')
    assert result == timedelta(minutes=1, seconds=2)


def test_parse_str_no_match1():
    with pytest.raises(ValueError):
        str_to_timedelta('1-2-3', '%H:%M:%S')


def test_parse_str_no_match2():
    with pytest.raises(ValueError):
        str_to_timedelta('1-2-3', '%H-%M')


def test_parse_str_no_format():
    with pytest.raises(ValueError):
        str_to_timedelta('1-2-3')


def test_parse_str_match_second():
    result = str_to_timedelta('1:2', '%H:%M:%S', '%H:%M')
    assert result == timedelta(hours=1, minutes=2)


def test_format_td1():
    result = str_from_timedelta(timedelta(hours=3, minutes=2, seconds=1), '%H:%M:%S')
    assert_time_str(result, '3:2:1')


def test_format_td2():
    result = str_from_timedelta(timedelta(hours=3, minutes=2, seconds=1), '%M:%S')
    assert_time_str(result, '182:1')


def test_format_td_approx():
    result = str_from_timedelta(timedelta(hours=3, minutes=2, seconds=1), '%H:%M')
    assert_time_str(result, '3:2')


def test_format_td_gap():
    result = str_from_timedelta(timedelta(hours=3, minutes=2, seconds=1), '%H:%S')
    assert_time_str(result, '3:121')
