#
# util.py
#
# Test utilities.
#

import json
import os
import os.path


def get_repo_dir():
    """
    Return absolute pathname of goose-python-client's repo.
    :return:
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_repo_dir_contents(repo_dirname):
    dirname = os.path.join(get_repo_dir(), repo_dirname)
    return [os.path.join(dirname, filename) for filename in os.listdir(dirname)]


def get_repo_file(repo_filename):
    return os.path.join(get_repo_dir(), repo_filename)


def get_dg_stac_item_schema():
    """
    Read and return DG stac item schema.
    :return: Dictionary of deserialized JSON for schema
    """
    dg_schema_filename = get_repo_file(r'dgloader\schemas\dg-stac-item-schema.json')
    with open(dg_schema_filename, 'r') as f:
        return json.load(f)
