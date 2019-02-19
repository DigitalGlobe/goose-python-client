#
# load_inventory.py
#
# Tool to insert STAC items into DUC V2 database from inventory service.
#

import argparse
import base64
import json
import os
import requests
import sys
import urllib.parse


class Inventory:
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
            'name': 'pan'
        }
    ]

    def __init__(self, inventory_service_url=None, inventory_selection_service_url=None, token=None):
        self.token = token
        if inventory_service_url:
            self.inventory_service_url = inventory_service_url
        else:
            self.inventory_service_url = self.inventory_service_default_url
        if inventory_selection_service_url:
            self.inventory_selection_service_url = inventory_selection_service_url
        else:
            self.inventory_selection_service_url = self.inventory_selection_service_default_url

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
        headers = {
            'Authorization': 'Bearer {}'.format(self.token)
        }
        uri = urllib.parse.urljoin(self.inventory_service_url, 'images/geospatial-images/{}'.format(image_id))
        print('GET {}'.format(uri))
        response = requests.get(uri, headers=headers)
        if response.status_code != 200:
            print(response.text)
            raise Exception('Failed to load image from inventory service:  {}'.format(uri))
        return json.loads(response.text)

    def get_sample_points_summary(self, image_id):
        """
        Call the inventory service's image-sample-points method to get summary sample point
        metadata.
        :param image_id:
        :return:
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
        headers = {
            'Authorization': 'Bearer {}'.format(self.token)
        }
        uri = urllib.parse.urljoin(self.inventory_selection_service_url, 'stereo/{}'.format(image_id))
        response = requests.get(uri, headers=headers)
        if response.status_code != 200:
            print(response.text)
            raise Exception('Failed to load stereo pairs from inventory sekectuib service:  {}'.format(uri))
        return json.loads(response.text)

    def create_stac_item(self, image_md, points_md, cloud_md, stereo_md):
        """
        Create and return a dictionary representing a STAC item for the given inventory image.
        :param image_md: Dictionary of image metadata returned by inventory service.
        :param points_md: Dictionary of sample points summary metadata returned by inventory service.
        :param cloud_md: Dictionary of cloud metadata returned by inventory selection service.
        :param stereo_md: Dictionary of stereo pair metadata returned by inventory selection service.
        :return: Tuple (stac_item, stac_attachments)
        """

        vehicle_name = self.get_property(image_md, 'vehicleName')
        if vehicle_name == 'WV04':
            platform = 'WORLDVIEW04'
            bands = self.bands_wv04
        else:
            raise Exception("Unsupported vehicle: {}".format(vehicle_name))


        # Get summary sections for pan and multiband images.
        # TODO:  For now we're only handling WV04.  Code might change for other vehicles.
        summaries = points_md.get('samplePointSummaries')
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
        scan_direction = self.get_property(image_md, 'scanDirection').lower()
        if scan_direction not in ('forward', 'reverse'):
            raise Exception('Unrecognized scan direction: "{}"'.format(scan_direction))

        # Get EPSG code.  There are multiple GeoJSON footprints in the inventory metadata each
        # with a coordinate system specified.  We'll just use the one in the toplevel "geometry" property.
        try:
            epsg_name = image_md['geometry']['crs']['properties']['name']
        except Exception:
            raise Exception('Could not find coordinate system in inventory image metadata.')
        try:
            epsg = int(epsg_name.split(':')[1])
        except Exception:
            raise Exception('Could not parse EPSG code in coordinate system name: "{}"'.format(epsg_name))

        # Get cloud cover percentage from inventory selection service's cloud covers.  We only use
        # a cloud cover if has isBest=True, ignoring any other cloud covers.  This can result in
        # the STAC item having eo:cloud_cover == null.
        cloud_cover_percent = None
        covers = cloud_md.get('covers')
        if covers:
            for cover in covers:
                is_best = cover.get('isBest')
                if is_best:
                    cloud_cover_percent = float(cover.get('coverPercentage'))
                    break

        # In the following we assume inventory service returns timestamps in the same ISO 8601
        # format required by Goose STAC items.
        item = {
            'properties': {
                'datetime': self.get_property(image_md, 'startTime'),
                'vendor': 'DigitalGlobe',

                'eo:gsd': self.get_property(pan, 'resolutionAvg'),
                'eo:platform': platform,
                'eo:constellation': 'WORLDVIEW',
                'eo:instrument': 'VNIR',
                'eo:bands': bands,
                'eo:azimuth': self.get_property(pan, 'spacecraftToTargetAzimuthAngleAvg'),
                'eo:sun_azimuth': self.get_property(main_summary, 'targetToSunAzimuthAngleAvg'),
                'eo:sun_elevation': self.get_property(main_summary, 'targetToSunElevationAngleAvg'),
                'eo:off_nadir': self.get_property(main_summary, 'spacecraftToTargetOffNadirAngleAvg'),
                'eo:epsg': epsg,
                'eo:cloud_cover': cloud_cover_percent,

                'dg:collect_time_start': self.get_property(image_md, 'startTime'),
                'dg:collect_time_end': self.get_property(image_md, 'endTime'),
                'dg:scan_direction': scan_direction,
                'dg:acquisition_rev_number': self.get_property(image_md, 'acquisitionRevNumber'),

                'dg:sun_elevation_min': self.get_property(main_summary, 'targetToSunElevationAngleMin'),
                'dg:sun_elevation_max': self.get_property(main_summary, 'targetToSunElevationAngleMax'),

                'dg:target_azimuth_min': self.get_property(main_summary, 'spacecraftToTargetAzimuthAngleMin'),
                'dg:target_azimuth_max': self.get_property(main_summary, 'spacecraftToTargetAzimuthAngleMax'),
                'dg:target_azimuth_start': self.get_property(main_summary, 'spacecraftToTargetAzimuthAngleStart'),
                'dg:target_azimuth_end': self.get_property(main_summary, 'spacecraftToTargetAzimuthAngleEnd'),

                'dg:off_nadir_min': self.get_property(main_summary, 'spacecraftToTargetOffNadirAngleMin'),
                'dg:off_nadir_max': self.get_property(main_summary, 'spacecraftToTargetOffNadirAngleMax'),
                'dg:off_nadir_start': self.get_property(main_summary, 'spacecraftToTargetOffNadirAngleStart'),
                'dg:off_nadir_end': self.get_property(main_summary, 'spacecraftToTargetOffNadirAngleEnd'),

                'dg:sun_azimuth_min': self.get_property(main_summary, 'targetToSunAzimuthAngleMin'),
                'dg:sun_azimuth_max': self.get_property(main_summary, 'targetToSunAzimuthAngleMax'),

                'dg:stereo_pair_identifiers': self.get_property(stereo_md, 'stereoIdentifiers'),
                'dg:bits_per_pixel': 16,
                'dg:storage': 'online',
                'dg:processing_options': [
                    'atmospheric_compensation',
                    'high_definition',
                    'pan_sharp',
                    'ortho'
                ]
            }
        }

        # Handle properties specific to pan and multispectral images.  When properties do not
        # apply we omit them entirely (not include them and set them to null).
        if pan:
            pan_properties = {
                'dg:pan_resolution_avg': self.get_property(pan, 'resolutionAvg'),
                'dg:pan_resolution_min': self.get_property(pan, 'resolutionMin'),
                'dg:pan_resolution_max': self.get_property(pan, 'resolutionMax'),
                'dg:pan_resolution_start': self.get_property(pan, 'resolutionStart'),
                'dg:pan_resolution_end': self.get_property(pan, 'resolutionEnd')
            }
            pan['properties'].update(pan_properties)
        if multi:
            multi_properties = {
                'dg:multi_resolution_avg': self.get_property(pan, 'resolutionAvg'),
                'dg:multi_resolution_min': self.get_property(pan, 'resolutionMin'),
                'dg:multi_resolution_max': self.get_property(pan, 'resolutionMax'),
                'dg:multi_resolution_start': self.get_property(pan, 'resolutionStart'),
                'dg:multi_resolution_end': self.get_property(pan, 'resolutionEnd')
            }
            pan['properties'].update(multi_properties)

        attachments = {}
        dap = self.get_property(image_md, 'dataAccessProfile')
        if dap:
            attachments['data-access-profile'] = dap

        return (item, attachments)

    def get_property(self, image_md, property_name):
        try:
            return image_md[property]
        except KeyError:
            raise Exception('Image metadata has no property "{}"'.format(property_name))


def generate_token():
    sys.stderr.write("Getting P2020 environment variables\n")
    token_server = os.getenv('P2020_IDENTITY_TOKEN_SERVER')
    client_id = os.getenv('P2020_IDENTITY_CLIENT_ID')
    client_secret = os.getenv('P2020_IDENTITY_CLIENT_SECRET')

    if token_server is None or client_id is None or client_secret is None:
        sys.stderr.write("Must set P2020 environment variables in order to generate token\n")
        sys.exit(0)

    sys.stderr.write("Getting token from endpoint {0}\n".format(token_server))

    parsed_ts = urllib.parse.urlparse(token_server)

    token_url = urllib.parse.urlunparse((parsed_ts.scheme, parsed_ts.netloc, parsed_ts.path + '/oauth/token', '', '', ''))

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
    return j['access_token']


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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--list-images', required=True, help='List all images in inventory service and write to given file')
    args = parser.parse_args()

    print('Generating token...')
    token = generate_token()

    inventory = Inventory(token=token)

    if args.list_images:
        list_images(inventory, args.list_images)
    else:
        print('No action specified on command line')
