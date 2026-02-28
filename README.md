# m-conf

m-conf project provides a ini-like configuration parser intended to generate a final configuration `dict` resulting from merging multiple ini-like configuration files.

## License

m-conf is distributed under MIT License. Please see the [LICENSE](LICENSE) file for details on copying and distribution.

## Basic usage

Given two configuration files:

- config1.cfg:

  ```txt
  # This is a comment

  [section]
  key1 = value1
  ```

- config2.cfg

  ```txt
  [section]
  key1 += 'another value'
  key2 = value2
  ```

By calling:

```py
cfg = m_conf.Parser().batch_load_file('config1.cfg', 'config2.cfg')
```

A resulting `cfg` will be returned:

```py
{
    'section': {
        'key1': ['value1', 'another value'],
        'key2': 'value2'
    }
}
```

Library also provides utilities for parsing a single file, parsing from string and much more.

## Configuration `dict`

Configuration dictionary returned by parsing is a specialized `dict` subclass, which provides access to nested entries additionally by using a flattened path.

Given this `dict`:

```py
# This is a built-in dict.
cfg = {
    'section': {
        'key': 'value'
    }
}

# m_conf.Config dict provides specialized accessors.
cfg = m_conf.Config(cfg)

# 'key' can be accessed using traditional way...
key = cfg['section']['key']

# ... or it can be accessed using a flattened path:
key_flat = cfg['section.key1']

# Both access methods lead to the same referenced object.
assert key == key_flat and key is key_flat
```
