#
# test_search.py
#

from datetime import datetime
from dgcatalog import Stac


class TestSearch:
    def test_search1(self, stac):
        """
        Get a set of STAC items.

        :param stac: Pytest fixture - connection to Stac service
        """
        assert isinstance(stac, Stac)
        try:
            result = stac.search(start_datetime=datetime(2017, 1, 1), end_datetime=datetime(2017, 1, 2))
            print(result)
        except Exception as exp:
            print(exp)

    def test_bad_search1(self, stac):
        assert isinstance(stac, Stac)
        try:
            result = stac.search(geometry='bad geometry')
            print(result)
        except Exception as exp:
            print(exp)
