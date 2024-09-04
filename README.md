# Welcome to ft_utils!

We're excited to share this library with you, designed to help you build high-performance applications with Free Threaded Python.

## License

ft_utils is open-source software, licensed under the permissive MIT license. You can find the full license terms in our [LICENSE file](LICENSE).

## Contributing and Code Standards

We'd love for you to contribute to ft_utils! To ensure that our codebase remains maintainable and efficient, we follow some simple guidelines. Please take a look at our [CONTRIBUTING.md](CONTRIBUTING.md) document for more information.

### Extra Guidelines

In addition to these guidelines, we have a few extra rules to keep in mind:

* **Language**: We use C11 and Python as our only programming languages. Build scripts can be in other languages.
* **Cross-Platform Compatibility**: Our code must compile on Windows, Linux, and Mac(arm).
* **GIL and Free Threaded Python**: All functionality should work seamlessly on both GIL and Free Threaded Python, although results may vary slightly between the two environments.
* **Unit Tests**: Every feature must have at least one unit test to ensure it works correctly.
* **Benchmarks**: It is best practice to write benchmarks for all new features to further test and to drive our aim of high performance.
