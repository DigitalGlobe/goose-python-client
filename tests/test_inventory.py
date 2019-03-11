#
# test_inventory.py
#

import copy
from dgloader.inventory import Inventory


class TestInventory:
    def test_dap1(self):
        """
        Basic test that removes scopes we don't want.
        :return:
        """
        dap = {
            'policies': [
                {
                    'name': 'TheName',
                    'startDate': "2017-02-21T08:01:35Z",
                    'endDate': "9999-12-31T23:59:59Z",
                    'deny': [
                        'All'
                    ],
                    'allow': [
                        'dg.internal.system'
                    ]
                }
            ]
        }
        backup = copy.deepcopy(dap)
        Inventory.fix_dap(dap)
        self.assert_no_policy_name(dap)
        self.assert_policies(dap)
        self.assert_dates(backup, dap)

        # Both scope lists should be empty
        assert not dap['policies'][0]['deny']
        assert not dap['policies'][0]['allow']

    def test_dap2(self):
        """
        Test that a policy with a DAF scope requires some other dataaccess scope.
        """
        dap = {
            'policies': [
                {
                    'name': 'TheName',
                    'startDate': "2017-02-21T08:01:35Z",
                    'endDate': "9999-12-31T23:59:59Z",
                    'deny': [
                        'All'
                    ],
                    'allow': [
                        'dataaccess.daf100'
                    ]
                }
            ]
        }
        try:
            Inventory.fix_dap(dap)
            raise Exception('Exception should have been raised')
        except Exception as exp:
            print(exp)

    def test_dap3(self):
        """
        Test fixing a DAP where no scopes need to be changed or removed.
        :return:
        """
        dap = {
            'policies': [
                {
                    'name': 'TheName',
                    'startDate': "2017-02-21T08:01:35Z",
                    'endDate': "9999-12-31T23:59:59Z",
                    'deny': [
                        'dataaccess.user1',
                        'dataaccess.user2'
                    ],
                    'allow': [
                        'dataaccess.user3',
                        'dataaccess.user4',
                        'dataaccess.user5'
                    ]
                }
            ]
        }
        Inventory.fix_dap(dap)
        assert set(dap['policies'][0]['deny']) == {'dataaccess.user1', 'dataaccess.user2'}
        assert set(dap['policies'][0]['allow']) == {'dataaccess.user3', 'dataaccess.user4', 'dataaccess.user5'}

    def assert_no_policy_name(self, dap):
        """
        No policy in a dap can have a "name" property.
        :param dap:
        :return:
        """
        for policy in dap['policies']:
            assert 'name' not in policy

    def assert_policies(self, dap):
        for policy in dap['policies']:
            self.assert_scopes(policy['allow'])
            self.assert_scopes(policy['deny'])

    def assert_scopes(self, scopes):
        assert len(scopes) == len(set(scopes))
        for scope in scopes:
            assert scope == scope.lower()
            scope = scope.lower()
            assert scope != 'all'
            assert scope != 'public'
            assert scope != 'experimental'
            assert not scope.startswith('dg.system.')

    def assert_dates(self, before_dap, after_dap):
        """
        Verify that the startDate and endDate in each policy was not changed by the fix method.
        :param dap:
        :return:
        """
        for (before_policy, after_policy) in zip(before_dap['policies'], after_dap['policies']):
            assert before_policy['startDate'] == after_policy['startDate']
            assert before_policy['endDate'] == after_policy['endDate']
