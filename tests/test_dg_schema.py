#
# test_dg_schema.py
#
# Test the DigitalGlobe STAC item schema dg-stac-item-schema.json
#

import jsonschema
import json
import tests.util


class TestDgSchema:
    def test_valid_schemas(self):
        """
        Test some valid DG STAC items against the schema dg-stac-item-schema.json
        """
        schema = tests.util.get_dg_stac_item_schema()
        for test_item in tests.util.get_repo_dir_contents(r'testdata\test-dg-items-valid'):
            print('Testing valid item {}'.format(test_item))
            with open(test_item, 'r') as f:
                item = json.load(f)
            jsonschema.validate(item, schema)

    def test_invalid_schemas(self):
        """
        Test some valid DG STAC items against the schema dg-stac-item-schema.json
        """
        schema = tests.util.get_dg_stac_item_schema()
        for test_item in tests.util.get_repo_dir_contents(r'testdata\test-dg-items-invalid'):
            print('Testing invalid item {}'.format(test_item))
            with open(test_item, 'r') as f:
                item = json.load(f)
            try:
                jsonschema.validate(item, schema)
                raise Exception('Invalid STAC item should have failed validation')
            except jsonschema.exceptions.ValidationError:
                pass
