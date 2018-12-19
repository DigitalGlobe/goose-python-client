#
# stac.py
#
# DigitalGlobe STAC Python client.
#

import collections.abc
import getpass
import json
import requests
import urllib.parse
from datetime import datetime
from enum import Enum

from dgcatalog.exceptions import StacException


# This enumeration is copied from goose-database repo, goose_database/search.py.
class SpatialOperation(Enum):
    """
    Supported methods of comparing a search geometry with a STAC item geometry.
    """

    INTERSECT = 1
    "Query STAC items that intersect search geometry."

    CONTAINS = 2
    "Query STAC items contained inside search geometry."

    INTERSECT_BBOX = 3
    "Query STAC items whose bounding box intersects search geometry bounding box."

    def __str__(self):
        """
        Return value as string as expected by STAC web service search methods.
        """
        if self.value == SpatialOperation.INTERSECT.value:
            return "intersect"
        if self.value == SpatialOperation.CONTAINS.value:
            return "contains"
        if self.value == SpatialOperation.INTERSECT_BBOX.value:
            return "bbox"
        raise StacException("Unspported SpatialOperation value")


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

        When using a username/password a token will be generated by calling GBDX
        at geobigdata.io.

        A Stac object does not generate a new token once its current token has expired.
        It is the user's responsibility to create a new Stac object if a token expires
        and a new one needs to be generated.

        :param url: URL of STAC service.  If None then use default URL.
        :param token: GBDX token to use in service requests.
        :param username: Username to use in generating token.
        :param password: Password to use in generating token.
        :param verbose: If True then Stac methods print informational messages to stdout.
        """
        self.verbose = verbose
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
            body = json.loads(response.text)
        except Exception as exp:
            raise StacException(
                'Error requesting GBDX token.  Response from GBDX authorization service is not JSON.') from exp
        token = body.get('access_token')
        if token:
            self._message('Token successfully received.')
            return token
        error = body.get('Error')
        if error:
            raise StacException('Error requesting GBDX token: {}'.format(error))
        raise StacException('Error requesting GBDX token.  Unexpected response from service: {}'.format(body))

    #
    # Catalog methods
    #

    def insert_catalog(self, catalog):
        """
        Create a new catalog in the database.

        :param catalog: Catalog object as dict.
        :return: None
        :raises StacException: If new catalog cannot be added to database.
        """
        url = self._make_url('catalog')
        self._post(url, json=catalog)

    def get_catalog(self, catalog_id=None):
        """
        Get a catalog or catalogs.  If catalog_id is not None then return just that catalog,
        otherwise return a list of all catalogs.

        :param catalog_id:
        :raises StacException: if no catalog with catalog_id exists
        :return: Dictionary of deserialized JSON.  List of dictionaries, each dictionary a catalog.
        """
        url = self._make_url('catalog')
        if catalog_id:
            url = self._url_append_path(url, catalog_id)
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
        url =  self._make_url('catalog/{}'.format(catalog_id))
        # Raise exception if error returned, otherwise return None.
        return self._put(url, json=catalog)

    #
    # Item methods
    #

    def insert_item(self, item, catalog_id):
        """
        Insert a new STAC item into a STAC catalog.

        :param dict item: STAC item.
        :param str catalog_id:  Catalog to insert item into.
        :return:
        """
        url = self._make_url('catalog/{}/item'.format(catalog_id))
        return self._post(url, json=item)

    def insert_items(self, items, catalog_id):
        """
        Insert new STAC items into a STAC catalog.

        :param items: Sequence of Item objects as dict's.
        :param str catalog_id: Catalog to insert items into.
        :return:
        """
        url = self._make_url('catalog/{}/item'.format(catalog_id))
        return self._post(url, json=items)

    def get_item(self, item_id, catalog_id=None):
        """
        Return a single STAC item given its ID.

        :param str item_id: STAC item ID
        :param str catalog_id: Optional catalog containing STAC item.
        :return: Dict for STAC item if it exists, else None.
        """
        url = self._make_url('search')
        items = self._get(url, params={'id': item_id})
        if not items:
            return None
        else:
            return items[0]

    def update_item(self, item, catalog_id=None):
        """
        Update an existing STAC item.

        :param dict item: STAC item.
        :param str catalog_id: Catalog containing STAC item.
        :return:
        """
        item_id = item.get('id')
        if not item_id:
            raise StacException('Item has no "id" property.')
        url = self._make_url('catalog/{}/item/{}'.format(catalog_id, item_id))
        return self._put(url)

    def delete_item(self, item_id):
        """
        Delete a STAC item.

        :param str item_id: STAC item ID.
        :return:
        """
        url = self._make_url('item/{}'.format(item_id))
        return self._delete(url)

    def search(self, catalog_id=None, bbox=None, geometry=None, start_datetime=None, end_datetime=None,
               spatial_operation=SpatialOperation.INTERSECT, item_ids=None, properties_filter=None, order_by=None,
               limit=None, page=None):
        """
        Query the STAC database.

        :param catalog_id: Catalog to search in.  If None then search entire database.
        :param bbox: Bounding box to search by.  Format is a sequence of the form [xmin, ymin, xmax, ymax]
            or [xmin, ymin, zmin, xmax, ymax, zmax].  Optional.
        :param geometry: Geometry to search by.  Dict of GeoJSON.  Optional.
        :param datetime start_datetime:
        :param datetime end_datetime:
        :param SpatialOperation spatial_operation: Type of spatial operation to perform between search geometry
            and stac item geometry.
        :param item_ids: List of item IDs to query.
        :param properties_filter: STAC properties filter.
        :param order_by: Columns to order result by.
        :param limit: Maximum number of items to return.
        :param page: Page number of results to query, starting at 1.  Page size is given by limit parameter.
        :return: List of STAC items, each item a dictionary.
        """

        # URL depends on whether catalog provided
        if catalog_id:
            url = self._make_url('catalog/{}/search'.format(catalog_id))
        else:
            url = self._make_url('search')

        body = {}
        if bbox:
            body['bbox'] = bbox
        if geometry:
            body['geometry'] = geometry
        if spatial_operation and not isinstance(spatial_operation, SpatialOperation):
            raise StacException('spatial_operation must be enum of type SpatialOperation')
        if spatial_operation is None:
            spatial_operation = SpatialOperation.INTERSECT
        body['spatial_operation'] = str(spatial_operation)

        if start_datetime and end_datetime:
            body['time'] = '{}/{}'.format(
                Stac.format_datetime_iso8601(start_datetime),
                Stac.format_datetime_iso8601(end_datetime))
        elif start_datetime or end_datetime:
            raise StacException('If search by time must specify both start_datetime and end_datetime')

        if item_ids:
            if not isinstance(item_ids, collections.abc.Sequence):
                raise StacException('item_ids must be a sequence')
            body['id'] = ','.join(str(item_id) for item_id in item_ids)

        return self._post(url, json=body)

    def _create_http_headers(self):
        """
        Return dictionary of HTTP headers to send with our web service requests.
        """
        return {
            'Authorization': 'Bearer {}'.format(self._token)
        }

    def _get(self, url, **kwargs):
        """
        Perform an HTTP GET on the goose API and return the result.

        :param url: URL to call
        :param kwargs: Keyword arguments supported by requests.get.
        :return: Dict or None.
        """
        self._message('GET: {}'.format(url))
        return self._handle_response(requests.get(url, **kwargs, headers=self._create_http_headers()))

    def _post(self, url, **kwargs):
        """
        Perform an HTTP POST on the goose API and return the result.

        :param url: URL to call
        :param kwargs: Keyword arguments supported by requests.post.
        :return: Dict or None.
        """
        self._message('POST: {}'.format(url))
        return self._handle_response(requests.post(url, **kwargs, headers=self._create_http_headers()))

    def _put(self, url, **kwargs):
        """
        Perform an HTTP PUT on the goose API and return the result.

        :param url: URL to call
        :param kwargs: Keyword arguments supported by requests.put.
        :return: Dict or None.
        """
        self._message('PUT: {}'.format(url))
        return self._handle_response(requests.put(url, **kwargs, headers=self._create_http_headers()))

    def _delete(self, url, **kwargs):
        """
        Perform an HTTP DELETE on the goose API and return the result.

        :param url: URL to call
        :param kwargs: Keyword arguments supported by requests.delete.
        :return: Dict or None.
        """
        self._message('DELETE: {}'.format(url))
        return self._handle_response(requests.delete(url, **kwargs, headers=self._create_http_headers()))

    def _url_append_path(self, url, path):
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

    def _make_url(self, path):
        return self._url_append_path(self.url, path)

    def _handle_response(self, response):
        """
        Handle response from the STAC web service.  We expect every response to be JSON and for
        all service methods to report exceptions the same way, so this single method will handle
        all web service responses.

        :param requests.Response response:
        :raises StacException: if error returned by web service
        :return: Web method response if request was successful.  This is None if the web method
            returned no body, otherwise it is deserialized JSON.
        """

        self._message('HTTP Status: {}'.format(response.status_code))

        # We expect every web request to return JSON, no exceptions.  In case of bad API-Gateway
        # configuration we may get HTML in some cases, which we raise an exception for.
        content_type = response.headers.get('Content-Type')
        if content_type not in ('application/json', 'application/hal+json'):
            raise StacException(
                'Service error:  STAC server response content-type is not JSON:  {}'.format(content_type), response)
        content = None
        if response.text:
            try:
                content = json.loads(response.text)
            except Exception as exp:
                raise StacException('Service error:  STAC server response body is invalid JSON', response) from exp

        if 200 <= response.status_code < 300:
            return content

        # API-Gateway and our own lambdas both us a "Message" property to hold an error message.
        message = content.get('Message', 'Error in catalog request.')
        request_id = content.get('request-id', None)

        # For errors we expect the response to have a JSON properties "message" and "request_id"
        if 400 <= response.status_code < 600:
            raise StacException(message, response, request_id)

        # Unrecognized HTTP status code
        raise StacException(
            'Service error:  Unsupported HTTP status {} returned.'.format(response.status_code), response, request_id)

    @staticmethod
    def format_datetime_iso8601(dt):
        assert isinstance(dt, datetime)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
