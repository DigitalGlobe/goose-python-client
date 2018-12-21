#
# tools.py
#
# Read an image from the DUC image service and convert it to a STAC item.
#

import argparse
import json
import re
import requests
from datetime import datetime

from dgcatalog import Stac

# ArcGIS image service
image_service_url = 'https://api.discover.digitalglobe.com/v1/services/ImageServer/query'

# API key used by Search & Discovery tool.  May need to be changed in the future.
_api_key = 'iSar7CX37j2hb3Apxp7Po6i5ZDlicfkGa8voURju'


def duc_get_image(image_id=None, image_ids=None):
    """
    Read image catalog metadata from the DUC image service and return it as a STAC item.
    :param str image_id: Single image ID to request
    :param list image_ids: Sequence of image IDs to request
    :return: If image_id specified then dict of STAC item, or None if it doesn't exist.
    If image_ids specified then list of STAC item dicts.
    """

    if (image_id and image_ids) or not (image_id or image_ids):
        raise Exception('Specify one of the image_id or image_ids parameters.')
    elif image_id:
        validate_image_id(image_id)
        query = "image_identifier='{}'".format(image_id)
    elif image_ids:
        for imgid in image_ids:
            validate_image_id(imgid)
        query = "image_identifier in ({})".format(','.join(["'" + imgid + "'" for imgid in image_ids]))

    params = {
        'where': query,
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
    if image_id:
        if not features:
            return None
        else:
            return esri_feature_to_stac(features[0])
    else:
        return [esri_feature_to_stac(f) for f in features]


def duc_query(query):
    """
    Read image catalog metadata from the DUC image service and return STAC items.
    :param str query: Query for ArcGIS image service "where" parameter.  Please make sure it's well-formed.
    :return: List of STAC items
    """
    params = {
        'where': query,
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
        return []
    else:
        return [esri_feature_to_stac(f) for f in features]


def esri_feature_to_stac(feature):
    """
    Convert an ESRI feature returned by an ArcGIS service to STAC.
    :param dict feature: Deserialized JSON of ArcGIS feature
    :return dict: STAC item
    """

    attrs = feature['attributes']
    vehicle_name = attrs['vehicle_name']
    if vehicle_name == 'GE01':
        platform = 'GEOEYE01'
    elif vehicle_name == 'WV01':
        platform = 'WORLDVIEW01'
    elif vehicle_name == 'WV02':
        platform = 'WORLDVIEW02'
    elif vehicle_name == 'WV03':
        platform = 'WORLDVIEW03'
    elif vehicle_name == 'WV04':
        platform = 'WORLDVIEW04'
    else:
        raise Exception('Unrecognized vehicle name: {}'.format(vehicle_name))

    return {
        'id': attrs['image_identifier'],
        'type': 'Feature',
        'geometry': {
            # ArcGIS doesn't differentiate between Polygons and MultiPolygons.  So just
            # go with Polygon and hope it works.
            'type': 'Polygon',
            'coordinates': feature['geometry']['rings']
        },
        'links': [
            {
                'rel': 'self',
                'href': 'https://api.digitalglobe.com/v2/stac/item/{}'.format(attrs['image_identifier'])
            }
        ],
        'assets': {
            'thumbnail': {
                'title': 'Browse',
                'href': 'https://api.digitalglobe.com/v2/show/id={}'.format(attrs['image_identifier'])
            }
        },
        'properties': {
            "vendor": "DigitalGlobe",
            'datetime': format_arcgis_feature_timestamp(attrs['collect_time_start']),
            "eo:gsd": attrs['pan_resolution_avg'],
            "eo:platform": platform,
            "eo:constellation": "WORLDVIEW",
            "eo:instrument": attrs['sensor_name'],
            "eo:azimuth": attrs['target_azimuth_avg'],
            "eo:sun_azimuth": attrs['sun_azimuth_avg'],
            "eo:sun_elevation": attrs['sun_elevation_avg'],
            "eo:off_nadir": attrs['off_nadir_avg'],
            "eo:cloud_cover": attrs['cloud_cover_percentage'],
            "eo:epsg": None,
            "dg:collect_time_start": format_arcgis_feature_timestamp(attrs['collect_time_start']),
            "dg:collect_time_end": format_arcgis_feature_timestamp(attrs['collect_time_end']),
            "dg:scan_direction": attrs['scan_direction'].lower(),
            "dg:acquisition_rev_number": None,          # TODO
            "dg:pan_resolution_min": attrs['pan_resolution_min'],
            "dg:pan_resolution_start": attrs['pan_resolution_start'],
            "dg:pan_resolution_max": attrs['pan_resolution_max'],
            "dg:pan_resolution_end": attrs['pan_resolution_end'],
            "dg:pan_resolution_avg": attrs['pan_resolution_avg'],
            "dg:multi_resolution_max": attrs['multi_resolution_max'],
            "dg:multi_resolution_min": attrs['multi_resolution_min'],
            "dg:multi_resolution_end": attrs['multi_resolution_end'],
            "dg:multi_resolution_avg": attrs['multi_resolution_avg'],
            "dg:multi_resolution_start": attrs['multi_resolution_start'],
            "dg:sun_elevation_max": attrs['sun_elevation_max'],
            "dg:sun_elevation_min": attrs['sun_elevation_min'],
            "dg:target_azimuth_max": attrs['target_azimuth_max'],
            "dg:target_azimuth_end": attrs['target_azimuth_end'],
            "dg:target_azimuth_min": attrs['target_azimuth_min'],
            "dg:target_azimuth_start": attrs['target_azimuth_start'],
            "dg:off_nadir_max": attrs['off_nadir_max'],
            "dg:off_nadir_start": attrs['off_nadir_start'],
            "dg:off_nadir_end": attrs['off_nadir_end'],
            "dg:off_nadir_min": attrs['off_nadir_min'],
            "dg:sun_azimuth_max": attrs['sun_azimuth_max'],
            "dg:sun_azimuth_min": attrs['sun_azimuth_min'],
            "dg:stereo_pair_identifiers": [],
            "dg:bits_per_pixel": 16
        }
    }


def format_arcgis_feature_timestamp(esri_timestamp):
    """
    Format ArcGIS feature timestamp to ISO8601 format we use in JSON.
    :param float esri_timestamp:  Timestamp in milliseconds from Unix epoch.
    :return: Timestamp as UTC string
    """
    return Stac.format_datetime_iso8601(
        datetime.utcfromtimestamp(esri_timestamp/1000.0))


def validate_image_id(image_id):
    """
    Raise Exception if image_id is invalid.
    :param image_id:
    :return:
    """
    # We do the same test we use for the database constraint.  Basically we're
    # just guarding against SQL injection here.
    if not re.fullmatch('^(([a-z0-9])|([a-z0-9][a-z0-9_.-]*[a-z0-9]))$', image_id, re.IGNORECASE):
        raise Exception('Invalid image ID: {}'.format(image_id))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--image-id', required=True, help='DUC image identifier')
    args = parser.parse_args()

    print(duc_to_stac(args.image_id))
