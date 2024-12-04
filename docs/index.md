# Free Threaded Python Documentation

Welcome to the documentation for Free Threaded Python and the ft_utils library. This documentation provides an introduction to the concepts and best practices of concurrent programming in Free Threaded Python, as well as a comprehensive guide to the ft_utils API.

## Introduction

* [Introduction to Free Threaded Python and ft_utils](introduction.md) - An overview of Free Threaded Python and the ft_utils library, including their purpose and benefits.

## Atomicity in Python

* [Solving Atomicity/Consistency Issues in Free Threaded Python](atomicity_in_Python.md) - A discussion of atomicity and consistency issues in Free Threaded Python, including solutions and best practices.

## ft_utils API Documentation

* [ft_utils API Documentation](ft_utils_api.md) - An overview of the ft_utils API, including its modules and classes.
* [concurrent Module Documentation](concurrent_api.md) - Documentation for the concurrent module, which provides foundational structures for scalable and efficient Free Threaded code.
* [local Module Documentation](local_api.md) - Documentation for the local module, which provides helper classes for moving processing from cross-thread to thread-local.
* [synchronization Module Documentation](synchronization_api.md) - Documentation for the synchronization module, which provides specialized lock types for Free Threaded programming.
* [weave Module Documentation](weave_api.md) - Documentation for the weave module, which provides advanced thread related functionality.

## Examples

* [FTPython Programming: Worked Examples](ft_worked_examples.md) - A worked examples demonstrating how to use ft_utils to write simple concurrent programs.

## Experimental

The `ft_utils.ENABLE_EXPERIMENTAL` flag defaults to False. When set to True some features are made available which are not fully supported and/or not fully backward compatible. The flag must be set before trying to use these features for the first time because of caching.

## On Github

* [Source on github](https://github.com/facebookincubator/ft_utils)
* [License - MIT](https://github.com/facebookincubator/ft_utils/blob/main/LICENSE)
* [Readme](https://github.com/facebookincubator/ft_utils/blob/main/README.md)
