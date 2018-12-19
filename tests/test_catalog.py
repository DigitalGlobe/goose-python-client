#
# test_catalog.py
#
# Test catalog functionality in the goose API.
#

from datetime import datetime
from dgcatalog import Stac


class TestCatalog:
    def test_catalog1(self, stac):
        """
        Get all catalogs.

        :param stac: Pytest fixture - connection to Stac service
        """
        assert isinstance(stac, Stac)
        result = stac.get_catalog()
        print(result)

    def test_get_item1(self, stac):
        item = stac.get_item('10400100108FCE00')
        print(item)

    def test_search1(self, stac):
        """
        Get a set of STAC items.

        :param stac: Pytest fixture - connection to Stac service
        """
        assert isinstance(stac, Stac)
        result = stac.search(limit=10, start_datetime=datetime(2010, 1, 1), end_datetime=datetime(2015, 1, 1))
        print(result)

    def test_bad_search1(self, stac):
        assert isinstance(stac, Stac)
        try:
            result = stac.search(geometry='bad geometry')
            print(result)
        except Exception as exp:
            print(exp)

    def test_catalog_update(self, stac):
        catalog = stac.get_catalog('wv04')
        catalog['description'] = 'DigitalGlobe WorldView 4 images'
        stac.update_catalog(catalog)

    def test_catalog_update_fails1(self, stac):
        try:
            stac.update_catalog({'id': 'no-such-id'})
            assert False
        except Exception as exp:
            print(exp)
