# -*- coding: utf-8 -*-
"""
This module provides tests for Flask-JSON encoding feature.
"""
from .common import *
from datetime import datetime, date, time, tzinfo, timedelta
from flask_json import json_response


class TestEncode(CommonTest):
    # Test: encode lazy string.
    def test_lazystring(self):
        # Skip this test if speaklater is not installed.
        try:
            from speaklater import make_lazy_string, _LazyString
        except ImportError:
            return

        # test_nospeaklater() overrides this import so we have to revert it
        # otherwise the test may fail because flask_json._LazyString
        # will be None
        flask_json._LazyString = _LazyString

        r = json_response(text=make_lazy_string(lambda: u'Привет'))
        assert_equals(r.status_code, 200)
        assert_equals(r.json['text'], u'Привет')

    # Test: encode iterable types: set, generators, iterators.
    # All of the must be converted to array of values.
    def test_iterable(self):
        # set
        r = json_response(lst=set([1, 2, 3]))
        assert_equals(r.json['lst'], [1, 2, 3])

        # generator
        r = json_response(lst=(x for x in [3, 2, 42]))
        assert_equals(r.json['lst'], [3, 2, 42])

        # iterator
        r = json_response(lst=iter([1, 2, 3]))
        assert_equals(r.json['lst'], [1, 2, 3])

    # Test: encode stuff if speaklater is not installed.
    # Here we just check if JSONEncoderEx.default() runs without errors.
    def test_nospeaklater(self):
        # Let's pretend we have no speaklater imported to test behaviour
        # without speaklater even if it installed.
        flask_json._LazyString = None

        r = json_response(text=time())
        assert_equals(r.status_code, 200)
        assert_equals(r.json['text'], '00:00:00')

    # Helper function to build response with time values.
    # Used by test_datetime_*().
    @staticmethod
    def get_time_values():
        class GMT1(tzinfo):
            def utcoffset(self, dt):
                return timedelta(hours=1)

            def dst(self, dt):
                return timedelta(0)

        dtm = datetime(2014, 5, 12, 17, 24, 10, tzinfo=GMT1())
        return json_response(tm1=time(12, 34, 56), tm2=time(1, 2, 3, 175),
                             dt=date(2015, 12, 7), dtm=dtm)

    # Test: encode datetime, date and time values with default format.
    # By default ISO format is used.
    def test_datetime_default_format(self):
        r = TestEncode.get_time_values()
        assert_equals(r.status_code, 200)
        assert_equals(r.json['tm1'], '12:34:56')
        assert_equals(r.json['tm2'], '01:02:03.000175')
        assert_equals(r.json['dt'], '2015-12-07')
        assert_equals(r.json['dtm'], '2014-05-12T17:24:10+01:00')

    # Test: encode datetime, date and time values with custom format.
    def test_datetime_custom_format(self):
        self.app.config['JSON_TIME_FORMAT'] = '%M:%S:%H'
        self.app.config['JSON_DATE_FORMAT'] = '%Y.%m.%d'
        self.app.config['JSON_DATETIME_FORMAT'] = '%Y/%m/%d %H-%M-%S'

        r = TestEncode.get_time_values()
        assert_equals(r.status_code, 200)
        assert_equals(r.json['tm1'], '34:56:12')
        assert_equals(r.json['tm2'], '02:03:01')
        assert_equals(r.json['dt'], '2015.12.07')
        assert_equals(r.json['dtm'], '2014/05/12 17-24-10')

    # Test: encode custom type;
    # Check if __json__() is not used by default.
    # Here json encoder raises 'TypeError: is not JSON serializable'.
    @raises(TypeError)
    def test_custom_obj_default_json(self):
        class MyJsonItem(object):
            def __json__(self):
                return '<__json__>'

        json_response(item=MyJsonItem())

    # Test: encode custom type;
    # Check if for_json() is not used by default.
    # Here json encoder raises 'TypeError: is not JSON serializable'.
    @raises(TypeError)
    def test_custom_obj_default_for_json(self):
        class MyJsonItem(object):
            def for_json(self):
                return '<for_json>'

        json_response(item=MyJsonItem())

    # Test: encode custom type with __json__().
    def test_custom_obj_json(self):
        class MyJsonItem(object):
            def __json__(self):
                return '<__json__>'

        # To use __json__() and for_json() we have to set this config.
        self.app.config['JSON_USE_ENCODE_METHODS'] = True
        r = json_response(item=MyJsonItem())
        assert_equals(r.json['item'], '<__json__>')

    # Test: encode custom type with for_json().
    def test_custom_obj_for_json(self):
        class MyJsonItem(object):
            def for_json(self):
                return '<for_json>'

        self.app.config['JSON_USE_ENCODE_METHODS'] = True
        r = json_response(item=MyJsonItem())
        assert_equals(r.json['item'], '<for_json>')

    # Test: if __json__() gets called before for_json().
    def test_custom_obj_priority(self):
        class MyJsonItem(object):
            def __json__(self):
                return '<__json__>'
            def for_json(self):
                return '<for_json>'

        self.app.config['JSON_USE_ENCODE_METHODS'] = True
        r = json_response(item=MyJsonItem())
        assert_equals(r.json['item'], '<__json__>')

    # Test: encoder with custom encoding function.
    def test_hook(self):
        class Fake(object):
            data = 0

        # Encode custom type with encoding hook.
        # This way is additional to __json__() and for_json().
        @self.ext.encoder
        def my_encoder(o):
            if isinstance(o, Fake):
                return 'fake-%d' % o.data

        fake = Fake()
        fake.data = 42
        r = json_response(fake=fake, tm=time(12, 34, 56), txt='txt')
        assert_equals(r.status_code, 200)
        assert_equals(r.json['fake'], 'fake-42')
        assert_equals(r.json['tm'], '12:34:56')
        assert_equals(r.json['txt'], 'txt')

    # Test: if JSONEncoderEx calls original default() method for unknown types.
    # In such situation exception will be raised (not serializable).
    @raises(TypeError)
    def test_encoder_invalid(self):
        json_response(fake=object())
