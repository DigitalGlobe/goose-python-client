#
# stac.py
#
# DigitalGlobe STAC Python client.
#

import getpass
import json
import requests
import urllib.parse

from dgcatalog.exceptions import StacException


class Stac:
    default_stac_url = 'https://discover.digitalglobe.com/v2/stac'

    default_auth_url = 'https://geobigdata.io/auth/v1/oauth/token'

    def __init__(self, url=None, token=None, username=None, password=None, verbose=False):
        """
        Initialize connection to a STAC catalog.

        Credentials must be provided by specifying either a token or a username.
        These parameters are mutually exclusive.  If token is specified then username and
        password must be None.  If username is specified then token must be None.
        If username is specified but password is None then you are prompted to enter a
        password using getpass.

        :param url:
        :param token:
        :param username:
        :param password:
        :param verbose: If True then set logging level to INFO.
        """

        if token and (username or password):
            raise StacException('If token is specified then username and password must be None.')
        if not token and not username and not password:
            raise StacException('Provide either a token or a username.')
        if username and not password:
            password = getpass.getpass('Password: ')
        if username:
            token = Stac.get_token(self, self.default_auth_url, username, password)
        self._token = token

        if url:
            self.url = url
        else:
            self.url = self.default_stac_url
        self.verbose = verbose

    def _message(self, message):
        if self.verbose:
            print(message)

    def get_token(self, auth_url, username, password):
        """
        Generate a token from the GBDX authorization service.

        :param auth_url: URL to authorization service, generally "https://geobigdata.io/auth/v1/oauth/token"
        :param username: GBDX username.
        :param password: GBDX password.
        :return: GBDX token.
        :raises StacException: if user is unauthorized, or any other kind of error generating token.
        """
        params = {
            'grant_type': 'password',
            'username': username,
            'password': password
        }
        self._message('Requesting token from {}'.format(auth_url))
        response = requests.post(auth_url, data=params)
        try:
            body = response.text
        except Exception as exp:
            raise StacException(
                'Error requesting GBDX token.  Response from GBDX authorization service is not JSON.') from exp
        token = body.get('access_token')
        if token:
            return token
        error = body.get('Error')
        if error:
            raise StacException('Error requesting GBDX token: {}'.format(error))
        raise StacException('Error requesting GBDX token.  Unexpected response from service: {}'.format(body))

    def insert_catalog(self, catalog):
        """
        Create a new catalog in the database.

        :param catalog: Catalog object as dict.
        :return: None
        :raises StacException: If new catalog cannot be added to database.
        """
        url = Stac._url_append_path(self.url, 'catalog')
        self._message('POST: {}'.format(url))
        # Raise exception if error returned, otherwise return None.
        self._post(url, json=catalog)

    def get_catalog(self, catalog_id=None):
        """
        Get a catalog or catalogs.  If catalog_id is not None then return just that catalog,
        otherwise return a list of all catalogs.

        :param catalog_id:
        :raises StacException: if no catalog with catalog_id exists
        :return: Dictionary of deserialized JSON.  List of dictionaries, each dictionary a catalog.
        """
        url = Stac._url_append_path(self.url, 'catalog')
        if catalog_id:
            url = Stac._url_append_path(url, catalog_id)
        self._message('GET: {}'.format(url))
        return self._get(url)

    def update_catalog(self, catalog):
        """
        Update a catalog.

        :param catalog: Catalog object as dict.
        :return: None
        :raises StacException: If catalog cannot be updated.
        """
        catalog_id = catalog.get('id')
        if not catalog_id or not isinstance(catalog_id, str):
            raise StacException('Catalog object does not have a valid "id" property.')
        url = Stac._url_append_path(self.url, 'catalog/{}'.format(catalog_id))
        self._message('PUT: {}'.format(url))
        # Raise exception if error returned, otherwise return None.
        return self._put(url, json=catalog)

    def insert_item(self, item, catalog_id):
        """
        Insert a new STAC item into a STAC catalog.

        :param item: Item object as dict.
        :param catalog_id:  Catalog to insert items into.
        :return:
        """
        pass

    def insert_items(self, items, catalog_id):
        """
        Insert new STAC items into a STAC catalog.

        :param items: Sequence of Item objects as dict's.
        :param catalog_id:  Catalog to insert items into.
        :return:
        """

    def get_item(self, item_id):
        """
        Return a single STAC item given its ID.
        :param item_id: STAC item ID
        :return: Dict of STAC item.
        """
        pass

    def update_item(self, item):
        """
        Update an existing STAC item.
        :param item:
        :return:
        """
        pass

    def search(self, catalog_id=None, bbox=None, geometry=None, start_datetime=None, end_datetime=None,
               spatial_operation=None, item_ids=None, properties_filter=None, order_by=None,
               limit=None, page=None):
        pass

    def _create_http_headers(self):
        """
        Return dictionary of HTTP headers to send with our web service requests.
        """
        return {
            'Authorization: Bearer {}'.format(self._token)
        }

    def _get(self, url, **kwargs):
        """
        Perform an HTTP GET on the goose API and return the result.

        :param url: URL to call
        :param kwargs: Keyword arguments supported by requests.get.
        :return: Dict or None.
        """
        return self._handle_response(requests.get(url, **kwargs, headers=self._create_http_headers()))

    def _post(self, url, **kwargs):
        """
        Perform an HTTP POST on the goose API and return the result.

        :param url: URL to call
        :param kwargs: Keyword arguments supported by requests.post.
        :return: Dict or None.
        """
        return self._handle_response(requests.post(url, **kwargs, headers=self._create_http_headers()))

    def _put(self, url, **kwargs):
        """
        Perform an HTTP PUT on the goose API and return the result.

        :param url: URL to call
        :param kwargs: Keyword arguments supported by requests.put.
        :return: Dict or None.
        """
        return self._handle_response(requests.put(url, **kwargs, headers=self._create_http_headers()))

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
