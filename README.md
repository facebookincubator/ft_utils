![Image](https://github.com/user-attachments/assets/f4ef78b9-8cc0-4264-971f-d6ac76884f3a)
# Welcome to ft_utils!

We're excited to share this library with you, designed to help you build high-performance applications with
Free Threaded Python.

## License

ft_utils is open-source software, licensed under the permissive MIT license. You can find the full license terms in our
[LICENSE file](LICENSE).

## Contributing and Code Standards

We'd love for you to contribute to ft_utils! To ensure that our codebase remains maintainable and efficient, we follow
some simple guidelines. Please take a look at our [CONTRIBUTING.md](CONTRIBUTING.md) document for more information.

### Extra Guidelines

In addition to these guidelines, we have a few extra rules to keep in mind:

* **Language**: We use C11 and Python as our only programming languages. Build scripts can be in other languages.
* **Cross-Platform Compatibility**: Our code must compile on Windows, Linux, and Mac(arm).
* **GIL and Free Threaded Python**: All functionality should work seamlessly on both GIL and Free Threaded Python, although results may vary slightly between the two environments.
* **Unit Tests**: Every feature must have at least one unit test to ensure it works correctly.
* **Benchmarks**: It is best practice to write benchmarks for all new features to further test and to drive our aim of high performance.

## Documentation

See to [documentation](docs/index.md).

## Build And CI

ft_utils is built and tested against the following configurations:

|               | manylinux: glibc 2.17+ x86-64 | manylinux: glibc 2.17+ i686 | musllinux: musl 1.2+ x86-64 | musllinux: musl 1.2+ i686 | Windows x86-64 | macOS 11.0+ ARM64 | manylinux: glibc 2.34+ x86-64 |
| ------------- | ----------------------------- | --------------------------- | --------------------------- | ------------------------- | -------------- | ----------------- | ----------------------------- |
| CPython 3.12  | ✅                            | ✅                          | ✅                          | ✅                        | ✅             | ✅                |                               |
| CPython 3.13  | ✅                            | ✅                          | ✅                          | ✅                        | ✅             | ✅                |                               |
| CPython 3.13t | ✅                            | ✅                          | ✅                          | ✅                        | ✅             | ✅                |                               |
| CPython 3.14  |                               |                             |                             |                           |                |                   | ✅                            |
| CPython 3.14t |                               |                             |                             |                           |                |                   | ✅                            |

These wheels are uploaded to and available on [PyPI](https://pypi.org/project/ft-utils/).

### Build from source

You will need a source code version of CPython. To run for Free Threaded Python, at the time of writing, this means
you will require CPython 3.13 and compile as 3.13t. This code will also compile under 3.12 but then you only get the
GIL version.

Please ensure you are in a virtual environment. If you cannot, or do not wish to do this then you will need to coomment
out the call to check_env() in setup.py.

Once you have everything in place, please execute setup.py as a python script:

```
python -P setup.py bdist_wheel
```

If this does not work due to networking then you might need use a proxy; for example:

```
https_proxy=http://fwdproxy:8080 python setup.py
```

To install just install the wheel; for example on Windows:

```
python -m pip install build\dist\ft_utils-0.1.0-cp314-cp314-win_amd64.whl
```

Or:

```
python -m pip install --force-reinstall build\dist\ft_utils-0.1.0-cp314-cp314-win_amd64.whl
```

### Testing from source

Once installed you can test the code via `python -m ft_utils.tests.test_run_all`. This will run all the tests and benchmarks which are known to be good and report any failures.
