#
# test_catalog.py
#
# Test catalog functionality in the goose API.
#

from goose import Stac


class TestCatalog:
    url = 'https://api-dev-2.discover.digitalglobe.com/v2/stac'

    def test_catalog1(self):
        stac = Stac(url=self.url)
        result = stac.catalog.get()
        print(result)
