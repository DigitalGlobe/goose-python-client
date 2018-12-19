#
# tools.py
#
# Read an image from the DUC image service and convert it to a STAC item.
#

import argparse
import json
import requests
from datetime import datetime

from dgcatalog import Stac

# ArcGIS image service
image_service_url = 'https://api.discover.digitalglobe.com/v1/services/ImageServer/query'

# API key used by Search & Discovery tool.  May need to be changed in the future.
_api_key = 'iSar7CX37j2hb3Apxp7Po6i5ZDlicfkGa8voURju'


def duc_to_stac(image_identifier):
    """
    Read image catalog metadata from the DUC image service and return it as a STAC item.
    :param image_identifier:
    :return:
    """
    params = {
        'where': "image_identifier='{}'".format(image_identifier),
        'outFields': '*'
    }
    headers = {
        'x-api-key': _api_key
    }
    response = requests.post(image_service_url, headers=headers, data=params)
    try:
        body = json.loads(response.text)
    except Exception as exp:
        print(response.text)
        raise Exception('Image service response is not JSON')
    features = body.get('features')
    if not features:
        raise Exception('DUC image service did not return image {}'.format(image_identifier))
    return esri_feature_to_stac(features[0])


def esri_feature_to_stac(feature):
    """
    Convert an ESRI feature returned by an ArcGIS service to STAC.
    :param dict feature: Deserialized JSON of ArcGIS feature
    :return dict: STAC item
    """
    # Always specify type as MultiPolygon because ESRI rings are always nested as multipolygons,
    # even if it's only a single ring.
    attrs = feature['attributes']
    return {
        'type': 'MultiPolygon',
        'coordinates': feature['geometry']['rings'],
        'links': [
            {
                'rel': 'self',
                'href': 'https://api.digitalglobe.com/v2/stac/item/{}'.format(attrs['image_identifier'])
            }
        ],
        'assets': {
            'thumbnail': 'https://api.digitalglobe.com/v2/show/id={}'.format(attrs['image_identifier'])
        },
        'properties': {
            'datetime': Stac.format_datetime_iso8601(
                datetime.utcfromtimestamp(attrs['collect_time_start']/1000.0)),
            'sun_elevation_avg': attrs['sun_elevation_avg'],
            'sun_azimuth_avg': attrs['sun_azimuth_avg'],
            'pan_resolution_avg': attrs['pan_resolution_avg'],
            'multi_resolution_avg': attrs['multi_resolution_avg']
        }
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--image-id', required=True, help='DUC image identifier')
    args = parser.parse_args()

    print(duc_to_stac(args.image_id))
