# goose-python-client

Note that this repo is named goose-python-client but the Python package it contains
is simply named "goose".  The repo is named the way it is to distinguish it from
other goose clients, like goose-js-client.  But we want a shorter name for the Python
package itself so that users can simply write "import goose".

## Using the package

Something like this...

```python
from goose import Stac
stac = Stac()
item = stac.item.get('1030010080D4FE00')
```
