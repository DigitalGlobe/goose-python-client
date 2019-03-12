#
# load_inventory.py
#
# Tool to insert STAC items into DUC V2 database from inventory service.
#

import argparse
import base64
import boto3
import json
import os
import requests
import urllib.parse

from concurrent import futures
from datetime import datetime


class P2020Token:
    # I have no idea how long P2020 tokens last so keep it short, like 10 minutes
    token_max_age_seconds = 600

    def __init__(self):
        self.token = None
        self.token_generation_datetime = None

    def get_token(self):
        if self.token:
            elapsed = datetime.utcnow() - self.token_generation_datetime
            if elapsed.total_seconds() < self.token_max_age_seconds:
                return self.token
        self.generate_token()
        return self.token

    def generate_token(self):
        """
        Request new token from P2020 UAA service and store in self.token.  Standard P2020 environment
        variables must be set for client ID, client secret, and token server URL.
        """
        print("Getting P2020 environment variables\n")
        token_server = os.getenv('P2020_IDENTITY_TOKEN_SERVER')
        client_id = os.getenv('P2020_IDENTITY_CLIENT_ID')
        client_secret = os.getenv('P2020_IDENTITY_CLIENT_SECRET')

        if token_server is None or client_id is None or client_secret is None:
            raise Exception("Must set P2020 environment variables in order to generate token")

        print("Getting token from endpoint {0}\n".format(token_server))

        parsed_ts = urllib.parse.urlparse(token_server)

        token_url = urllib.parse.urlunparse(
            (parsed_ts.scheme, parsed_ts.netloc, parsed_ts.path + '/oauth/token', '', '', ''))

        encode_string = client_id + ':' + client_secret
        encode_string = base64.b64encode(encode_string.encode('ascii')).decode("ascii")
        auth_creds = 'Basic %s' % encode_string

        params = dict()
        params['client_id'] = client_id
        params['grant_type'] = 'client_credentials'
        headers = {
            'accept': 'application/json',
            'authorization': auth_creds
        }

        response = requests.post(token_url, params=params, headers=headers)

        j = json.loads(response.text)
        self.token = j['access_token']
        self.token_generation_datetime = datetime.utcnow()


class Inventory:
    """

    """

    inventory_service_default_url = 'https://inventory.apps.satcloud.space'
    inventory_selection_service_default_url = 'https://inventory-selection.apps.satcloud.space'

    bands_wv04 = [
        {
            'name': 'blue',
            'center_wavelength': 480
        },
        {
            'name': 'green',
            'center_wavelength': 545
        },
        {
            'name': 'red',
            'center_wavelength': 672.5
        },
        {
            'name': 'nir',
            'center_wavelength': 850
        },
        {
            'name': 'pan',
            'center_wavelength': 625
        }
    ]

    def __init__(self, inventory_service_url=None, inventory_selection_service_url=None, token=None,
                 error_file=None):
        """

        :param inventory_service_url:
        :param inventory_selection_service_url:
        :param token:
        :param error_file:  Image ID's of images inventory service returns non-200 for,
            or images that are no ingest complete
        """
        self.token = token
        self.error_file = error_file
        if inventory_service_url:
            self.inventory_service_url = inventory_service_url
        else:
            self.inventory_service_url = self.inventory_service_default_url
        if inventory_selection_service_url:
            self.inventory_selection_service_url = inventory_selection_service_url
        else:
            self.inventory_selection_service_url = self.inventory_selection_service_default_url
        self.executor = futures.ThreadPoolExecutor(max_workers=5)

    def set_token(self, token):
        self.token = token

    def list_images(self):
        """
        Query the inventory selection service's "images" endpoint to get a list of all images in the inventory
        database.
        :return: List of image identifiers
        """
        headers = {
            'Authorization': 'Bearer {}'.format(self.token)
        }
        # Hardcode date range that covers all WV04 images ever acquired.
        request = {
            'startTime': '2016-01-01T00:00:00Z',
            'endTime': '2020-01-01T00:00:00Z',
            'isGeospatial': True,
            'isOffEarth': False
        }
        uri = urllib.parse.urljoin(self.inventory_selection_service_url, 'images')
        print('POST {}'.format(uri))
        response = requests.post(uri, headers=headers, json=request)
        if response.status_code != 200:
            print(response.text)
            raise Exception('Failed to select all images from inventory selection service:  {}'.format(uri))
        body = json.loads(response.text)
        return body['imageIdentifiers']

    def get_image(self, image_id):
        """
        Request image from the inventory service
        :param image_id: Image ID
        :return: Dictionary of inventory service repsonse.  Return None if inventory service returns
            error or image is not ingest complete
        """
        headers = {
            'Authorization': 'Bearer {}'.format(self.token)
        }
        uri = urllib.parse.urljoin(self.inventory_service_url, 'images/geospatial-images/{}'.format(image_id))
        print('GET {}'.format(uri))
        response = requests.get(uri, headers=headers)
        if response.status_code != 200:
            print(response.text)
            if self.error_file:
                with open(self.error_file, 'a') as f:
                    print('{} {}'.format(image_id, response.status_code), file=f)
            return None
        metadata = json.loads(response.text)
        if not metadata.get('isIngestComplete'):
            print('Image {} is not ingest complete'.format(image_id))
            if self.error_file:
                with open(self.error_file, 'a') as f:
                    print('{} incomplete'.format(image_id), file=f)
            return None
        return metadata

    def get_sample_points_summary(self, image_id):
        """
        Request sample points information from the inventory service for the given image.
        :param image_id: Image ID
        :return: Dictionary of sample points information
        """
        headers = {
            'Authorization': 'Bearer {}'.format(self.token)
        }
        params = {
            'imageIdentifier': image_id,
            'returnSummary': 'True'
        }
        uri = urllib.parse.urljoin(self.inventory_service_url, 'image-sample-points')
        print('GET {}'.format(uri))
        response = requests.get(uri, headers=headers, params=params)
        if response.status_code != 200:
            print(response.text)
            raise Exception('Failed to load image from inventory service:  {}'.format(uri))
        return json.loads(response.text)

    def get_cloud(self, image_id):
        """
        Request cloud covers from the inventory selection service for the given image.
        Calls the endpoint cover-assignments/associated-items and requests coverTypeName=cloud.
        :param image_id: Image ID
        :return: Dictionary
        """
        headers = {
            'Authorization': 'Bearer {}'.format(self.token)
        }
        uri = urllib.parse.urljoin(self.inventory_selection_service_url, 'cover-assignments/associated-items')
        params = {
            'imageIdentifier': image_id,
            'coverTypeName': 'cloud'
        }
        response = requests.get(uri, headers=headers, params=params)
        if response.status_code != 200:
            print(response.text)
            raise Exception('Failed to load image cloud from inventory selection service:  {}'.format(uri))
        return json.loads(response.text)

    def get_stereo(self, image_id):
        """
        Request stereo images from the inventory selection service for the given image.
        :param image_id:
        :return:
        """
        headers = {
            'Authorization': 'Bearer {}'.format(self.token)
        }
        uri = urllib.parse.urljoin(self.inventory_selection_service_url, 'stereo/{}'.format(image_id))
        response = requests.get(uri, headers=headers)
        if response.status_code != 200:
            print(response.text)
            raise Exception('Failed to load stereo pairs from inventory sekectuib service:  {}'.format(uri))
        return json.loads(response.text)

    def read_item_from_inventory(self, image_id, catalog):
        """
        Read an image from inventory and return a GeoJSON feature collection containing
        a single feature for the STAC item and its attachments.
        :param image_id:
        :return: None if image is not ingest complete, access is not allowed, or could not be
            queried by inventory for some reason.
        """

        # We have to make three service queries to get all the information we need to create
        # the image's STAC item.  (For now we don't query stereo images because there aren't any.)
        # So use futures to run the three queries simultaneously.
        future_image = self.executor.submit(self.get_image, image_id)
        future_points = self.executor.submit(self.get_sample_points_summary, image_id)
        future_cloud = self.executor.submit(self.get_cloud, image_id)
        results = futures.wait([future_image, future_points, future_cloud])
        if results.not_done:
            print('Not all inventory requests worked')
        else:
            try:
                inventory_image = future_image.result()
                if inventory_image is None:
                    # Error captured by get_image and logged to file, so just return None
                    return None
                inventory_points = future_points.result()
                inventory_cloud = future_cloud.result()
                (stac, attachments) = self.create_stac_item(
                    inventory_image, inventory_points, inventory_cloud, None, catalog)
                return self.create_stac_item_feature_collection(stac, attachments)
            except Exception as exp:
                print('Exception for image {}:  {}'.format(image_id, exp))
        if self.error_file:
            with open(self.error_file, 'a') as f:
                print('{} other'.format(image_id), file=f)

    def create_stac_item(self, inventory_image, inventory_points, inventory_cloud, inventory_stereo, catalog):
        """
        Create and return a dictionary representing a STAC item for the given inventory image.
        :param inventory_image: Dictionary of image metadata returned by inventory service.
        :param inventory_points: Dictionary of sample points summary metadata returned by inventory service.
        :param inventory_cloud: Dictionary of cloud metadata returned by inventory selection service.
        :param inventory_stereo: Dictionary of stereo pair metadata returned by inventory selection service.
            May be None to just set dg:stereo_pair_identifiers to empty array.
        :return: Tuple (stac_item, stac_attachments)
        """

        image_id = self._get_property(inventory_image, 'imageIdentifier')

        vehicle_name = self._get_property(inventory_image, 'vehicleName')
        if vehicle_name == 'WV04':
            platform = 'WORLDVIEW04'
            bands = self.bands_wv04
        else:
            raise Exception("Unsupported vehicle: {}".format(vehicle_name))

        # Get summary sections for pan and multiband images.
        # TODO:  For now we're only handling WV04.  Code might change for other vehicles.
        summaries = inventory_points.get('samplePointSummaries')
        if not summaries:
            raise Exception('Inventory sample point summaries has no "samplePointSummaries" property')
        pan = None
        multi = None
        for summary in summaries:
            name = summary.get('bandsetName')
            if name == 'pan':
                if pan:
                    raise Exception('Inventory sample points has multiple "pan" summaries')
                pan = summary
            elif name == 'n1_r_g_b':
                if multi:
                    raise Exception('Inventory sample points has multiple "n1_r_g_b" summaries')
                multi = summary
            else:
                raise Exception('Inventory sample points summary has unrecognized name: "{}"'.format(name))
        if vehicle_name == 'WV04':
            if not pan:
                raise Exception('WV04 image has no "pan" sample points summary')
            if not multi:
                raise Exception('WV04 image has no "n1_r_g_b" sample points summary')

        # For getting angle properties we prefer to use the pan summary if it's available (which it
        # should always be), otherwise use the multispectral summary.
        main_summary = pan if pan else multi

        # Make sure scan direction is one of the exact values "forward" or "reverse".  Case matters.
        scan_direction = self._get_property(inventory_image, 'scanDirection').lower()
        if scan_direction not in ('forward', 'reverse'):
            raise Exception('Unrecognized scan direction: "{}"'.format(scan_direction))

        # Get cloud cover percentage from inventory selection service's cloud covers.  We only use
        # a cloud cover if has isBest=True, ignoring any other cloud covers.  This can result in
        # the STAC item having eo:cloud_cover == null.
        cloud_cover_percent = None
        covers = inventory_cloud.get('covers')
        if covers:
            for cover in covers:
                is_best = cover.get('isBest')
                if is_best:
                    cloud_cover_percent = float(cover.get('coverPercentage'))
                    break

        geometry = self._get_property(inventory_image, 'geometry')
        geometry.pop('crs', None)

        # In the following we assume inventory service returns timestamps in the same ISO 8601
        # format required by Goose STAC items.
        item = {
            'id': image_id,
            'type': 'Feature',
            'geometry': geometry,
            'assets': {},
            'links': [
                {
                    'rel': 'self',
                    'href': 'https://api.discover.digitalglobe.com/v2/stac/catalog/{}/item/{}'.format(catalog, image_id)
                }
            ],
            'properties': {
                'datetime': self._get_property(inventory_image, 'startTime'),
                'vendor': 'DigitalGlobe',

                'eo:gsd': self._get_property(pan, 'resolutionAvg'),
                'eo:platform': platform,
                'eo:constellation': 'WORLDVIEW',
                'eo:instrument': 'VNIR',
                'eo:bands': bands,
                'eo:azimuth': self._get_property(pan, 'spacecraftToTargetAzimuthAngleAvg'),
                'eo:sun_azimuth': self._get_property(main_summary, 'targetToSunAzimuthAngleAvg'),
                'eo:sun_elevation': self._get_property(main_summary, 'targetToSunElevationAngleAvg'),
                'eo:off_nadir': self._get_property(main_summary, 'spacecraftToTargetOffNadirAngleAvg'),
                # No EPSG code because assets can be in different coordinate systems
                'eo:epsg': None,
                'eo:cloud_cover': cloud_cover_percent,

                'dg:collect_time_start': self._get_property(inventory_image, 'startTime'),
                'dg:collect_time_end': self._get_property(inventory_image, 'endTime'),
                'dg:scan_direction': scan_direction,
                'dg:acquisition_rev_number': self._get_property(inventory_image, 'acquisitionRevNumber'),

                'dg:sun_elevation_min': self._get_property(main_summary, 'targetToSunElevationAngleMin'),
                'dg:sun_elevation_max': self._get_property(main_summary, 'targetToSunElevationAngleMax'),

                'dg:target_azimuth_min': self._get_property(main_summary, 'spacecraftToTargetAzimuthAngleMin'),
                'dg:target_azimuth_max': self._get_property(main_summary, 'spacecraftToTargetAzimuthAngleMax'),
                'dg:target_azimuth_start': self._get_property(main_summary, 'spacecraftToTargetAzimuthAngleStart'),
                'dg:target_azimuth_end': self._get_property(main_summary, 'spacecraftToTargetAzimuthAngleEnd'),

                'dg:off_nadir_min': self._get_property(main_summary, 'spacecraftToTargetOffNadirAngleMin'),
                'dg:off_nadir_max': self._get_property(main_summary, 'spacecraftToTargetOffNadirAngleMax'),
                'dg:off_nadir_start': self._get_property(main_summary, 'spacecraftToTargetOffNadirAngleStart'),
                'dg:off_nadir_end': self._get_property(main_summary, 'spacecraftToTargetOffNadirAngleEnd'),

                'dg:sun_azimuth_min': self._get_property(main_summary, 'targetToSunAzimuthAngleMin'),
                'dg:sun_azimuth_max': self._get_property(main_summary, 'targetToSunAzimuthAngleMax'),

                'dg:stereo_pair_identifiers':
                    [] if not inventory_stereo else self._get_property(inventory_stereo, 'stereoIdentifiers'),
                'dg:bits_per_pixel': 16,
                'dg:storage': None,
                'dg:processing_options': [],
                'dg:vnir_association': None,
                'dg:swir_association': None,
                'dg:cavis_association': None
            }
        }

        # Handle properties specific to pan and multispectral images.  When properties do not
        # apply we omit them entirely (not include them and set them to null).
        if pan:
            pan_properties = {
                'dg:pan_resolution_avg': self._get_property(pan, 'resolutionAvg'),
                'dg:pan_resolution_min': self._get_property(pan, 'resolutionMin'),
                'dg:pan_resolution_max': self._get_property(pan, 'resolutionMax'),
                'dg:pan_resolution_start': self._get_property(pan, 'resolutionStart'),
                'dg:pan_resolution_end': self._get_property(pan, 'resolutionEnd')
            }
            item['properties'].update(pan_properties)
        if multi:
            multi_properties = {
                'dg:multi_resolution_avg': self._get_property(pan, 'resolutionAvg'),
                'dg:multi_resolution_min': self._get_property(pan, 'resolutionMin'),
                'dg:multi_resolution_max': self._get_property(pan, 'resolutionMax'),
                'dg:multi_resolution_start': self._get_property(pan, 'resolutionStart'),
                'dg:multi_resolution_end': self._get_property(pan, 'resolutionEnd')
            }
            item['properties'].update(multi_properties)

        attachments = {}
        dap = self._get_property(inventory_image, 'dataAccessProfile')
        if dap:
            self.fix_dap(dap)
            attachments['data-access-profile'] = dap

        return (item, attachments)

    @staticmethod
    def fix_dap(dap):
        """
        Fix up a DAP policy in-place.
        :param dap:
        """
        policies = dap.get('policies')
        for policy in policies:
            policy.pop('name', None)
            policy['deny'] = Inventory.fix_scopes(policy['deny'])
            policy['allow'] = Inventory.fix_scopes(policy['allow'])

    @staticmethod
    def fix_scopes(scopes):
        """
        Fix a list of DAP scopes by applying a number of rules.

        We remove any DAF scope of the form "dataaccess.daf*".  When an image has a DAF
        scope we expect that it has three scopes in all:  the DAF scope, the dg.internal.system
        scope, and some other dataaccess scope containing the customer number.  In this situation
        we want to remove the DAF scope and the dg.internal.system scope leaving only the
        dataaccess scope containing the customer number.

        Here's a real example of an image with three such scopes:

        image_identifier                            allow
        ========================================================================
        03dde9f2-e5b3-41a0-93f0-1a0c16abd0dd-inv	dataaccess.59345
        03dde9f2-e5b3-41a0-93f0-1a0c16abd0dd-inv	dataaccess.daf81
        03dde9f2-e5b3-41a0-93f0-1a0c16abd0dd-inv	dg.internal.system

        In this case we want to leave this image with only the scope dataaccess.59345.

        :param scopes: List of scopes
        :return: Fixed list of scopes
        """

        # Accumulate fixed scopes in a set so we don't have duplicates.  I saw a case
        # where the allow list had both "Public" and "dataaccess.public"
        # in it, and we don't want the result to have "dataaccess.public" twice.
        result = set()

        has_daf = False
        for scope in scopes:
            lower = scope.lower()
            fixed = None
            if lower == 'public':
                fixed = 'dataaccess.public'
            elif lower == 'calibration':
                fixed = 'dataaccess.calibration'
            elif lower == 'experimental':
                fixed = 'dataaccess.experimental'
            elif lower.startswith('dataaccess.daf'):
                has_daf = True
            elif lower.startswith('dg.internal.'):
                # Ignore anything starting with dg.internal, e.g. "dg.internal.system" and "dg.internal.operations"
                pass
            elif lower == 'all':
                # Ignore "all" scopes which generally occur in the deny list
                pass
            else:
                # Anything else take as is, but lower cased.
                fixed = lower

            if fixed:
                result.add(fixed)

        # Require that an image with a DAF scope have at least some other scope.
        # We don't expect to ever see this but raise an exception because we *must* not allow it.
        if has_daf and not result:
            raise Exception('Image has DAF scope but not dataaccess customer scope')
        return list(result)

    def create_stac_item_feature_collection(self, item, attachments):
        """
        Create a GeoJSON feature collection suitable for inserting into the
        goose database containing a single STAC item and its attachments.
        :param item:
        :param attachments:
        :return:
        """
        return {
            'type': 'FeatureCollection',
            'features': [
                item
            ],
            'attachments': attachments
        }

    def _get_property(self, image_md, property_name):
        try:
            return image_md[property_name]
        except KeyError:
            raise Exception('Image metadata has no property "{}"'.format(property_name))


def list_images(inventory, filename):
    """
    Read all images from inventory and write their image IDs to the file.
    :param inventory: Inventory object.
    :param filename: File to write image ID's to.
    """
    print('Reading all image IDs from inventory service')
    image_ids = inventory.list_images()
    print('Writing file {}'.format(filename))
    with open(filename, 'wb') as f:
        f.write(os.linesep.join(image_ids).encode('utf-8'))


def process_images(inventory, catalog, images_todo_file, images_done_file, output_folder=None,
                   queue_url=None, max_images=None):
    """

    :param inventory: Inventory object.
    :param catalog: Name of existing STAC catalog to insert items into
    :param images_todo_file: File containing image ID's to be processed.
    :param images_done_file: File containing image ID's already processed.
    :param images_error_file:
    :param output_folder: Folder to write STAC items to.
    :param queue_url: SQS queue to send STAC items to.
    :param max_images: Maximum number of images to process before exiting.
    :return: Number of images processed
    """

    count = 0
    count_not_processed = 0
    start_time = None

    if queue_url:
        print('Creating SQS client')
        sqs_client = boto3.client('sqs')

    tokenizer = P2020Token()

    done_ids = []
    if os.path.exists(images_done_file):
        with open(images_done_file, 'r') as f:
            done_ids = set([line.strip() for line in f.readlines()])
            print('Read {} image IDs from done file'.format(len(done_ids)))

    with open(images_todo_file) as f:
        input_ids = [line.strip() for line in f.readlines() if line.strip() not in done_ids]
    print('Read {} images still to process'.format(len(input_ids)))

    done_file = None
    incomplete_file = None
    try:
        done_file = open(images_done_file, 'a')

        start_time = datetime.utcnow()
        for image_id in input_ids:
            count += 1
            print('Processing image {}:  {}'.format(count, image_id))

            inventory.set_token(tokenizer.get_token())
            feature_collection = inventory.read_item_from_inventory(image_id, catalog)
            if not feature_collection:
                count_not_processed += 1
            else:
                message = json.dumps(feature_collection, indent=4)
                if output_folder:
                    output_file = os.path.join(output_folder, image_id + '.geojson')
                    with open(output_file, 'w') as f:
                        print(message, file=f)
                if queue_url:
                    attributes = {
                        'catalog': {
                            'DataType': 'String',
                            'StringValue': catalog
                        }
                    }
                    sqs_client.send_message(QueueUrl=queue_url, MessageAttributes=attributes, MessageBody=message)

            if done_file:
                print(image_id, file=done_file, flush=True)

            if max_images and count >= max_images:
                break

            elapsed = datetime.utcnow() - start_time
            seconds_per_image = elapsed.total_seconds() / count
            print('Elapsed time:  {}  Seconds per image:  {}'.format(elapsed, seconds_per_image))

    finally:
        if done_file:
            done_file.close()
        if incomplete_file:
            incomplete_file.close()

    print()
    print('Total count:  {}'.format(count))
    print('Not processed: {}'.format(count_not_processed))
    if start_time:
        elapsed = datetime.utcnow() - start_time
        print('Elapsed time:  {}'.format(elapsed))
        seconds_per_image = elapsed.total_seconds() / count
        print('Seconds per image:  {}'.format(seconds_per_image))

    return count


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--list-images', required=False, help="List all images in inventory service and write to given file")

    # Options for files containing image ID's and the state of the bulk load.
    # When processing STAC items both of these options must be specified.
    parser.add_argument(
        '--todo-file', required=False, help="To-do list.  File containing image ID's to process")
    parser.add_argument(
        '--done-file', required=False, help="Done list.  File containing image ID's already processed")
    parser.add_argument(
        '--error-file', required=False, help="Error list.  File containing image ID's that failed to process")

    # Destinations for sending STAC items, either files or SQS queue
    parser.add_argument('--stac-folder', required=False, help="Folder to write STAC items to")
    parser.add_argument('--queue-url', required=False, help='SQS queue to send STAC items to')

    # Other options
    parser.add_argument('--max-images', required=False, type=int, help="Maximum number of images to process")
    parser.add_argument('--catalog', required=False, help="Catalog name to use in asset and link URI's")

    args = parser.parse_args()

    if args.list_images:
        inventory = Inventory()
        list_images(inventory, args.list_images)
    elif args.todo_file and args.done_file and args.error_file:
        if not args.catalog:
            print('Must specify command line option "--catalog" when processing images')
            exit(1)

        # We either write STAC items to files or send them to a queue
        has_destination = bool(args.stac_folder) ^ bool(args.queue_url)
        if not has_destination:
            print('Must specify either --stac-folder or --queue-url option, but not both')

        inventory = Inventory(error_file=args.error_file)
        process_images(inventory, args.catalog, args.todo_file, args.done_file,
                       output_folder=args.stac_folder, queue_url=args.queue_url, max_images=args.max_images)
    else:
        print('No action specified on command line')
