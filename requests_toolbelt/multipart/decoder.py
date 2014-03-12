# -*- coding: utf-8 -*-
"""

requests_toolbelt.multipart.decoder
===================================

This holds all the implementation details of the MultipartDecoder

"""

from .encoder import encode_with
from requests.structures import CaseInsensitiveDict


def _split_on_find(content, bound):
    point = content.find(bound)
    return content[:point], content[point + len(bound):]


class ImproperBodyPartContentException(Exception):
    def __init__(self, *args):
        super(ImproperBodyPartContentException, self).__init__(*args)


class BodyPart(object):
    """

    The ``BodyPart`` object is a ``Response``-like interface to an individual
    subpart of a multipart response. It is expected that these will
    generally be created by objects of the ``MultipartDecoder`` class.

    Like ``Response``, there is a ``CaseInsensitiveDict`` object named header,
    ``content`` to access bytes, ``text`` to access unicode, and ``encoding``
    to access the unicode codec.

    """

    def __init__(self, content, encoding):
        headers = {}
        # Split into header section (if any) and the content
        if b'\r\n\r\n' in content:
            first, self.content = _split_on_find(content, b'\r\n\r\n')
            if first != b'':
                for line in first.split(b'\r\n'):
                    if b': ' in line:
                        h_key, h_value = _split_on_find(line, b': ')
                        headers[h_key] = h_value
        elif b'\r\n' == content[:2]:
            self.content = content[2:]
        else:
            raise ImproperBodyPartContentException(
                'content neither contains CR-LF-CR-LF, nor starts with CR-LF'
            )
        self.headers = CaseInsensitiveDict(headers)
        self.encoding = encoding

    def __eq__(self, other):
        try:
            ans = self.content == other.content
        except AttributeError:
            ans = self.content == other
        return ans

    @property
    def text(self):
        return self.content.decode(self.encoding)


class NonMultipartContentTypeException(Exception):
    def __init__(self, *args):
        super(NonMultipartContentTypeException, self).__init__(*args)


class MultipartDecoder(object):
    """

    The ``MultipartDecoder`` object parses the multipart payload of
    a bytestring into a tuple of ``Response``-like ``BodyPart`` objects.

    The basic usage is::

        import requests
        from requests_toolbelt import MultipartDecoder

        response = request.get(url)
        decoder = MultipartDecoder.from_response(response)
        for part in decoder.parts:
            print(part.header['content-type'])

    """
    def __init__(self, content, content_type, encoding='utf-8'):
        #: Original content
        self.content = content
        #: Original Content-Type header
        self.content_type = content_type
        #: Response body encoding
        self.encoding = encoding
        #: Parsed parts of the multipart response body
        self.parts = tuple()
        self._find_boundary()
        self._parse_body()

    def _find_boundary(self):
        ct_info = tuple(x.strip() for x in self.content_type.split(';'))
        mimetype = ct_info[0]
        if mimetype.split('/')[0] != 'multipart':
            raise NonMultipartContentTypeException(
                "Unexpected mimetype in content-type: '{0}'".format(mimetype)
            )
        for item in ct_info[1:]:
            attr, value = _split_on_find(
                item,
                '='
            )
            if attr.lower() == 'boundary':
                self.boundary = encode_with(value.strip('"'), self.encoding)

    @classmethod
    def _fix_last_part(cls, part, end_marker):
        if end_marker in part:
            return part[:part.find(end_marker)]
        else:
            return part

    def _parse_body(self):
        self.parts = tuple(
            [
                BodyPart(
                    MultipartDecoder._fix_last_part(
                        x[:-2], b''.join((b'\r\n--', self.boundary, b'--'))
                    ),
                    self.encoding
                )
                for x in self.content.split(
                    b''.join((b'--', self.boundary, b'\r\n'))
                )
                if x != b'' and x != b'\r\n'
            ]
        )

    @classmethod
    def from_response(cls, response, encoding='utf-8'):
        content = response.content
        content_type = response.headers.get('content-type', None)
        return cls(content, content_type, encoding)
