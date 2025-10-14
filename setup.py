# Copyright (c) Meta Platforms, Inc. and affiliates.
# pyre-strict

import os
import sys
import sysconfig
from pathlib import Path

from setuptools import Extension, setup


def build_extensions() -> list[Extension]:
    """Build list of Extension objects for C extensions."""
    python_include = sysconfig.get_paths()["include"]
    include_dirs = [
        python_include,
        os.path.join(python_include, "internal"),
        "src/include",
    ]

    extensions = [
        Extension(
            "ft_utils._concurrency",
            sources=[
                "src/native/_concurrency/_concurrency.c",
                "src/native/_concurrency/ft_core.c",
            ],
            include_dirs=include_dirs,
        ),
        Extension(
            "ft_utils._weave",
            sources=["src/native/_weave/_weave.c"],
            include_dirs=include_dirs,
        ),
        Extension(
            "ft_utils.local",
            sources=["src/native/local/local.c"],
            include_dirs=include_dirs,
        ),
        Extension(
            "ft_utils.synchronization",
            sources=["src/native/synchronization/synchronization.c"],
            include_dirs=include_dirs,
        ),
        Extension(
            "ft_utils._test_compat",
            sources=["src/ft_utils/tests/_test_compat.c"],
            include_dirs=include_dirs,
        ),
        Extension(
            "ft_utils._test_weave",
            sources=["src/ft_utils/tests/_test_weave.c"],
            include_dirs=include_dirs,
        ),
    ]

    return extensions


def invoke_main() -> None:
    with open("README.md") as readme_file:
        long_descr = readme_file.read()

    setup(
        name="ft_utils",
        version="0.1.0",
        description="A utility library for Free Threaded Python programming",
        long_description=long_descr,
        long_description_content_type="text/markdown",
        author="Meta Platforms, Inc.",
        author_email="open-source@fb.com",
        url="https://github.com/facebookincubator/ft_utils",
        license="MIT",
        packages=["ft_utils", "ft_utils.native", "ft_utils.tests"],
        ext_modules=build_extensions(),
        classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3.12",
            "Programming Language :: Python :: 3.13",
            "Programming Language :: Python :: 3.14",
        ],
    )


if __name__ == "__main__":
    invoke_main()
