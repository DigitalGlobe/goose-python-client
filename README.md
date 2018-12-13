# goose-python-client

Note that this repo is named goose-python-client but the Python package it contains
is simply named "dgcatalog".  The repo is named the way it is to distinguish it from
other goose clients, like goose-js-client.  But we want a shorter name for the Python
package itself so that users can simply write "import dgcatalog".

## Using the package

Something like this...

```python
from dgcatalog import Stac
stac = Stac()
item = stac.item.get('1030010080D4FE00')
```

### Building a wheel

```
rm -rf build
rm -rf dgcatalog.egg-info
python setup.py sdist bdist_wheel
```