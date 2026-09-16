# Changelog

## 0.2.0 (unreleased)

### Breaking

- Dropped support for Python 3.12. `requires-python` is now `>=3.13`, so 3.12
  users stay on 0.1.0 rather than receiving an incompatible upgrade.

### Added

- Linux `aarch64` wheels.
- A source distribution is now published alongside the wheels, so platforms
  without a matching wheel can build from source.
- 3.14 and 3.14t wheels for macOS and Windows; previously 3.14 was published
  for Linux x86_64 only.

### Fixed

- Corrected package metadata. Project metadata now lives solely in
  `pyproject.toml`; it was previously duplicated in `setup.py`, where
  setuptools silently ignored it.

## 0.1.0

- Initial release.
