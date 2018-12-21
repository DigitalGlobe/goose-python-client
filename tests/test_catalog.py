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

    def test_catalog2(self, stac):
        """
        Get a particular catalog.
        :param stac:
        :return:
        """
        assert isinstance(stac, Stac)
        result = stac.get_catalog('wv')
        assert result
        print(result)

    def test_catalog_update(self, stac):
        assert isinstance(stac, Stac)
        catalog = stac.get_catalog('wv')
        catalog['description'] = 'DigitalGlobe WorldView 4 image catalog'
        result = stac.update_catalog(catalog)
        assert not result

    def test_catalog_update_fails1(self, stac):
        try:
            assert isinstance(stac, Stac)
            catalog = stac.get_catalog('wv')
            # Either description or title is required, I forget which
            catalog['description'] = None
            catalog['title'] = None
            stac.update_catalog(catalog)
            assert False
        except Exception as exp:
            print(exp)
