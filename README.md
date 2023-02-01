# m-conf

m-conf project probides a ini-like configuration parser intended to generate a final configuration `dict` resulting from merging multiple ini-like configuration files.

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
m_conf.load(Path(config1.cfg), Path(config2.cfg))
```

A resulting `dict` will be returned:

```py
{
    'section': {
        'key1': ['value1', 'another value'],
        'key2': ['value2']
    }
}
```
