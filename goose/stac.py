#
# stac.py
#

import json
import logging
import requests
import urllib.parse

from goose.exceptions import StacException


class Stac:
    default_url = 'https://discover.digitalglobe.com/v2/stac'

    def __init__(self, url=None):
        if url:
            self.url = url
        else:
            self.url = self.default_url

        self.catalog = Catalog(self.url)
        self.item = Item(self.url)

    @staticmethod
    def _url_append_path(url, path):
        """
        Append to a URL's path portion, leaving all other parts of the URL the same.
        :param url: A URL
        :param path: Path to append
        :return: URL with path appended
        """
        parts = urllib.parse.urlsplit(url)
        url_path = parts.path
        if not parts.path.endswith('/') and not path.startswith('/'):
            url_path += '/'
        url_path += path
        return urllib.parse.urlunsplit((parts.scheme, parts.netloc, url_path, parts.query, parts.fragment))

    @staticmethod
    def _handle_response(response):
        """
        Handle response from the STAC web service.  We expect every response to be JSON and for
        all service methods to report exceptions the same way, so this single method will handle
        all web service responses.
        :param requests.Response response:
        :raises StacException: if error returned by web service
        :return: Dictionary of deserialized JSON if response was successful
        """

        # We expect every web request to return JSON, no exceptions.  In case of bad API-Gateway
        # configuration we may get HTML in some cases, which we raise an exception for.
        content_type = response.headers.get('Content-Type')
        if content_type not in ('application/json', 'application/hal+json'):
            raise StacException(
                'Service error:  STAC server response content-type is not JSON:  {}'.format(content_type), response)
        try:
            content = json.loads(response.text)
        except Exception as exp:
            raise StacException('Service error:  STAC server response body is invalid JSON', response) from exp

        if 200 <= response.status_code < 300:
            return content

        message = content.get('message', None)
        request_id = content.get('request_id', None)

        # For errors we expect the response to have a JSON properties "message" and "request_id"
        if 400 <= response.status_code < 600:
            raise StacException(message, response, request_id)

        # Unrecognized HTTP status code
        raise StacException(
            'Service error:  Unsupported HTTP status {} returned.'.format(response.status_code), response, request_id)


class Catalog:
    def __init__(self, url):
        self.url = url

    def get(self, catalog_id=None):
        """
        Select catalogs.  If catalog_id is not None then return just that catalog,
        otherwise return a list of all catalogs.
        :param catalog_id:
        :raises StacException: if no catalog with catalog_id exists
        :return: Dictionary of deserialized JSON
        """
        url = Stac._url_append_path(self.url, 'catalog')
        if catalog_id:
            url = Stac._url_append_path(url, catalog_id)
        logging.info('Requesting URL: {}'.format(url))
        response = requests.get(url)
        return Stac._handle_response(response)


class Item:
    def __init__(self, url):
        self.url = url
