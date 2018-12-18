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

    def test_search1(self, stac):
        """
        Get a set of STAC items.

        :param stac: Pytest fixture - connection to Stac service
        """
        assert isinstance(stac, Stac)
        result = stac.search(limit=10, start_datetime=datetime(2010, 1, 1), end_datetime=datetime(2015, 1, 1))
        print(result)
