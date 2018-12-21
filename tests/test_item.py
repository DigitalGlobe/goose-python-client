#
# test_item.py
#

from dgcatalog.tools import duc_get_image


class TestItem:
    def test_item1(self, stac):
        """
        Test operations on an item.
        :param stac:
        :return:
        """

        # An item we expect to be in the "wv" catalog
        item_id = '4d8ab5aa-46ac-4cab-84d2-c1423fc9b848-inv'
        catalog_id = 'wv'

        item = stac.get_item(item_id)
        print('Item exists: {}'.format(bool(item)))

        deleted = stac.delete_item(item_id, catalog_id)
        print("Item deleted: {}".format(deleted))

        print('Getting item from DUC')
        new_item = duc_get_image(image_id=item_id)
        if not new_item:
            raise Exception('Could not get image from DUC: {}'.format(item_id))

        stac.insert_item(new_item, catalog_id)

        # Get item by catalog again
        item = stac.get_item(item_id, catalog_id)

    def test_item2(self, stac):
        """
        Test inserting a group of items at once.

        :param stac:
        :return:
        """
        catalog_id = 'wv'
        item_ids = [
            "1d952420-11f8-4ad9-a6dd-68b0d73cc4bf-inv",
            "1da4257c-6d37-47fc-bf75-c37febc9cb0c-inv",
            "1e119369-25f4-426d-9d5b-4201b0929fe9-inv",
            "1e983832-608f-4b71-8e85-8a90e9dd43c8-inv",
            "1f4fd90c-03c7-4a33-bb3b-322ec9a73781-inv"
        ]
        for item_id in item_ids:
            print('Deleting item {}: {}'.format(item_id, stac.delete_item(item_id, catalog_id)))

        print('Getting items from DUC')
        items = [duc_get_image(item_id) for item_id in item_ids]
        print('Inserting items')
        stac.insert_items(items, catalog_id)
        print('Getting items')
        for item_id in item_ids:
            item = stac.get_item(item_id, catalog_id)
            if not item:
                raise Exception('Could not get item {}'.format(item_id))

    def test_item3(self, stac):
        """
        Test getting an item that doesn't exist.
        :param stac:
        :return:
        """
        assert stac.get_item('no-such-item-id') is None
