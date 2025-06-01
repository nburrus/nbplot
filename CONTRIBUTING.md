# Making a new release

- Bump the version numbers in `pyproject.toml` and `nbplot/__init__.py`

```
pip install build
python3 -m build
twine upload dist/*
```

Username is always `__token__`
