"""Collection of tests for utils.dump.

The dump utility module only has two public attributes:

- dump_response
- dump_all

This module, however, tests many of the private implementation details since
those public functions just wrap them and testing the public functions will be
very complex and high-level.
"""
from requests_toolbelt._compat import HTTPHeaderDict
from requests_toolbelt.utils import dump

import mock
import pytest

HTTP_1_1 = 11
HTTP_1_0 = 10
HTTP_0_9 = 9


class TestSimplePrivateFunctions(object):

    """Excercise simple private functions in one logical place."""

    def test_coerce_to_bytes_skips_byte_strings(self):
        """Show that _coerce_to_bytes skips bytes input."""
        bytestr = b'some bytes'
        assert dump._coerce_to_bytes(bytestr) is bytestr

    def test_coerce_to_bytes_converts_text(self):
        """Show that _coerce_to_bytes handles text input."""
        bytestr = b'some bytes'
        text = bytestr.decode('utf-8')
        assert dump._coerce_to_bytes(text) == bytestr

    def test_format_header(self):
        """Prove that _format_header correctly formats bytes input."""
        header = b'Connection'
        value = b'close'
        expected = b'Connection: close\r\n'
        assert dump._format_header(header, value) == expected

    def test_format_header_handles_unicode(self):
        """Prove that _format_header correctly formats text input."""
        header = b'Connection'.decode('utf-8')
        value = b'close'.decode('utf-8')
        expected = b'Connection: close\r\n'
        assert dump._format_header(header, value) == expected

    def test_build_request_path(self):
        """Show we get the right request path for a normal request."""
        path, _ = dump._build_request_path(
            'https://example.com/foo/bar', {}
        )
        assert path == b'/foo/bar'


class RequestResponseMixin(object):

    """Mix-in for test classes needing mocked requests and responses."""

    response_spec = [
        'connection',
        'content',
        'raw',
        'request',
        'url',
    ]

    request_spec = [
        'body',
        'headers',
        'method',
        'url',
    ]

    httpresponse_spec = [
        'headers',
        'reason',
        'status',
        'version',
    ]

    adapter_spec = [
        'proxy_manager',
    ]

    @pytest.fixture(autouse=True)
    def set_up(self):
        """xUnit style autoused fixture creating mocks."""
        self.response = mock.Mock(spec=self.response_spec)
        self.request = mock.Mock(spec=self.request_spec)
        self.httpresponse = mock.Mock(spec=self.httpresponse_spec)
        self.adapter = mock.Mock(spec=self.adapter_spec)

        self.response.connection = self.adapter
        self.response.request = self.request
        self.response.raw = self.httpresponse

    def configure_response(self, content=b'', proxy_manager=None, url=None):
        """Helper function to configure a mocked response."""
        self.adapter.proxy_manager = proxy_manager or {}
        self.response.content = content
        self.response.url = url

    def configure_request(self, body=b'', headers=None, method=None,
                          url=None):
        """Helper function to configure a mocked request."""
        self.request.body = body
        self.request.headers = headers or {}
        self.request.method = method
        self.request.url = url

    def configure_httpresponse(self, headers=None, reason=b'', status=b'',
                               version=HTTP_1_1):
        """Helper function to configure a mocked urllib3 response."""
        self.httpresponse.headers = HTTPHeaderDict(headers or {})
        self.httpresponse.reason = reason
        self.httpresponse.status = status
        self.httpresponse.version = version


class TestResponsePrivateFunctions(RequestResponseMixin):

    """Excercise private functions using responses."""

    def test_get_proxy_information_sans_proxy(self):
        """Show no information is returned when not using a proxy."""
        self.configure_response()

        assert dump._get_proxy_information(self.response) is None

    def test_get_proxy_information_with_proxy_over_http(self):
        """Show only the request path is returned for HTTP requests.

        Using HTTP over a proxy doesn't alter anything except the request path
        of the request. The method doesn't change a dictionary with the
        request_path is the only thing that should be returned.
        """
        self.configure_response(
            proxy_manager={'http://': 'http://local.proxy:3939'},
        )
        self.configure_request(
            url='http://example.com',
            method='GET',
        )

        assert dump._get_proxy_information(self.response) == {
            'request_path': 'http://example.com'
        }

    def test_get_proxy_information_with_proxy_over_https(self):
        """Show that the request path and method are returned for HTTPS reqs.

        Using HTTPS over a proxy changes the method used and the request path.
        """
        self.configure_response(
            proxy_manager={'http://': 'http://local.proxy:3939'},
        )
        self.configure_request(
            url='https://example.com',
            method='GET',
        )

        assert dump._get_proxy_information(self.response) == {
            'method': 'CONNECT',
            'request_path': 'https://example.com'
        }
