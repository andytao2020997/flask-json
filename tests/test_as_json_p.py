"""
This module provides tests for @as_json_p() decorator.
"""
from .common import *
from werkzeug.exceptions import BadRequest
from flask import Response, json
from flask_json import json_response, _json_p_handler, as_json_p


class TestAsJsonP(CommonTest):
    def setup(self):
        super(TestAsJsonP, self).setup()
        # Disable pretty print to have smaller result string
        self.app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
        # Force status field to test if it will be added to JSONP response.
        # It must drop status field.
        self.app.config['JSON_ADD_STATUS'] = True

        # Initial config for the @as_json_p
        self.app.config['JSON_JSONP_STRING_QUOTES'] = True
        self.app.config['JSON_JSONP_OPTIONAL'] = True
        self.app.config['JSON_JSONP_QUERY_CALLBACKS'] = ['callback', 'jsonp']

    # Helper method to make a request.
    def req(self, *args, **kwargs):
        return self.app.test_request_context(*args, **kwargs)

    # Test: required callback in the URL query.
    # It must fail since callback name is not provided.
    @raises(BadRequest)
    def test_handler_missing_callback_required(self):
        with self.req('/?param=1'):
            _json_p_handler('x', callbacks=['callback', 'foo'], optional=False)

    # Test: optional callback in the URL query.
    # It must return regular response if callback name is not provided.
    def test_handler_missing_callback_optional(self):
        with self.req('/?param=1'):
            rv = _json_p_handler({'x': 1},
                                 callbacks=['callback', 'foo'], optional=True)
            assert_is_instance(rv, Response)
            assert_equals(rv.json, {'x': 1, 'status': 200})

    # Test: if we pass a text then it must return it as is.
    def test_handler_text_no_quotes(self):
        with self.req('/?callback=foo'):
            r = _json_p_handler(str('hello'),
                                callbacks=['callback'], optional=False,
                                add_quotes=False)
            assert_equals(r.get_data(as_text=True), 'foo(hello);')
            assert_equals(r.status_code, 200)
            assert_equals(r.headers['Content-Type'], 'application/javascript')
            # For py 2.x we also test unicode string.
            if sys.version_info[0] == 2:
                r = _json_p_handler(unicode('hello'),
                                    callbacks=['callback'], optional=False,
                                    add_quotes=False)
                assert_equals(r.get_data(as_text=True), 'foo(hello);')

    # Test: if we pass a text then it must return quoted string.
    def test_handler_text_quotes(self):
        with self.req('/?callback=foo'):
            r = _json_p_handler(str('hello'), optional=False, add_quotes=True)
            assert_equals(r.get_data(as_text=True), 'foo("hello");')
            assert_equals(r.status_code, 200)
            assert_equals(r.headers['Content-Type'], 'application/javascript')
            # For py 2.x we also test unicode string.
            if sys.version_info[0] == 2:
                r = _json_p_handler(unicode('hello'),
                                    callbacks=['callback'], optional=False,
                                    add_quotes=True)
                assert_equals(r.get_data(as_text=True), 'foo("hello");')

    # Test: text with quotes.
    def test_handler_text_quotes2(self):
        with self.req('/?callback=foo'):
            r = _json_p_handler(str('hello "Sam"'), add_quotes=True)
            assert_equals(r.get_data(as_text=True), r'foo("hello \"Sam\"");')
            assert_equals(r.status_code, 200)
            assert_equals(r.headers['Content-Type'], 'application/javascript')

    # Test: same as above but used configuration instead of kwarg,
    # it adds quotes by default.
    def test_handler_text_default(self):
        with self.req('/?callback=foo'):
            r = _json_p_handler(str('hello'))
            assert_equals(r.get_data(as_text=True), 'foo("hello");')
            assert_equals(r.status_code, 200)
            assert_equals(r.headers['Content-Type'], 'application/javascript')
            # For py 2.x we also test unicode string.
            if sys.version_info[0] == 2:
                r = _json_p_handler(unicode('hello'), callbacks=['callback'],
                                    optional=False)
                assert_equals(r.get_data(as_text=True), 'foo("hello");')

    # Test: pass json response.
    def test_handler_json(self):
        with self.req('/?callback=foo'):
            r = json_response(val=100, add_status_=False)
            val = _json_p_handler(r, callbacks=['callback'], optional=False)

            assert_equals(val.get_data(as_text=True), 'foo({"val": 100});')
            assert_equals(val.status_code, 200)
            assert_equals(val.headers['Content-Type'], 'application/javascript')

    # Test: simple usage, no callback; it must proceed like @as_json.
    def test_simple_no_jsonp(self):
        @as_json_p
        def view():
            return dict(val=1, name='Sam')

        with self.req('/'):
            r = view()
            assert_equals(r.status_code, 200)
            assert_equals(r.headers['Content-Type'], 'application/json')
            assert_dict_equal(r.json, {'val': 1, 'name': 'Sam', 'status': 200})

    # Test: simple usage, with callback.
    def test_simple(self):
        @as_json_p
        def view():
            return dict(val=1, name='Sam')

        with self.req('/?callback=foo'):
            r = view()
            assert_equals(r.status_code, 200)
            assert_equals(r.headers['Content-Type'], 'application/javascript')
            # Build test value.
            param = json.jsonify(val=1, name='Sam').get_data(as_text=True)
            text = 'foo(%s);' % param
            assert_equals(r.get_data(as_text=True), text)

    # Test: simple usage, with alternate callback.
    # By default callback name may be 'callback' or 'jsonp'.
    def test_simple2(self):
        @as_json_p
        def view():
            return dict(val=1, name='Sam')

        with self.req('/?jsonp=foo'):
            r = view()
            assert_equals(r.status_code, 200)
            assert_equals(r.headers['Content-Type'], 'application/javascript')

            param = json.jsonify(val=1, name='Sam').get_data(as_text=True)
            text = 'foo(%s);' % param
            assert_equals(r.get_data(as_text=True), text)

    # Test: @as_json_p with parameters, with missing callback.
    # Here we force @as_json_p to use custom callback names
    # and make it required.
    @raises(BadRequest)
    def test_complex_required_missing(self):
        @as_json_p(callbacks=['boo'], optional=False)
        def view():
            return dict(val=1, name='Sam')

        with self.req('/?callback=foo'):
            view()

    # Test: @as_json_p with parameters.
    # Here we force @as_json_p to use custom callback names
    # and make it required.
    def test_complex_required(self):
        @as_json_p(callbacks=['boo'], optional=False)
        def view():
            return dict(val=1, name='Sam')

        with self.req('/?boo=foo'):
            r = view()
            assert_equals(r.status_code, 200)
            assert_equals(r.headers['Content-Type'], 'application/javascript')

            param = json.jsonify(val=1, name='Sam').get_data(as_text=True)
            text = 'foo(%s);' % param
            assert_equals(r.get_data(as_text=True), text)
