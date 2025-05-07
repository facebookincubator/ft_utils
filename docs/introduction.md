![Image](https://github.com/user-attachments/assets/f4ef78b9-8cc0-4264-971f-d6ac76884f3a)
# Introduction to Free Threaded Python and ft_utils

Welcome to the documentation for ft_utils, a library designed to support fast and scalable concurrent programming in Free Threaded Python. This documentation aims to provide not only a comprehensive guide to the ft_utils API but also an introduction to the concepts and best practices of concurrent programming in Free Threaded Python.

## What is Free Threaded Python?

Free Threaded Python is a build of the Python interpreter that removes the Global Interpreter Lock (GIL), allowing true parallel execution of threads. This change enables developers to take full advantage of multi-core processors and write high-performance concurrent code. However, it also introduces new challenges, such as ensuring atomicity and thread safety.

To help you navigate these challenges, we've included a section on [Atomicity in Python](atomicity_in_Python.md), which discusses the implications of removing the GIL and provides guidance on how to ensure thread safety in your code.

## ft_utils Library

The ft_utils library provides a set of tools and data structures designed to make concurrent programming in Free Threaded Python easier and more efficient. The library includes features such as atomic integers, concurrent dictionaries, and batch executors, all of which are designed to help you write fast and scalable concurrent code.

For a comprehensive overview of the ft_utils API, please see our [API documentation](ft_utils_api.md).

## Getting Started

If you're new to concurrent programming in Free Threaded Python, we recommend starting with our [worked examples](ft_worked_examples.md), which demonstrates how to use ft_utils to write a simple concurrent programs. These examples will give you a hands-on understanding of how to apply the concepts and best practices discussed in this documentation.

We hope this documentation helps you get started with concurrent programming in Free Threaded Python and makes the most of the ft_utils library. If you have any questions or feedback, please don't hesitate to reach out.
