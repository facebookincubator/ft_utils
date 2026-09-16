# Copyright (c) Meta Platforms, Inc. and affiliates.

import os
import sysconfig

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext


class BuildExtInplace(build_ext):
    """Custom build_ext to ensure extensions are placed in the correct package directory."""

    def get_ext_fullpath(self, ext_name: str) -> str:
        """Override to ensure extensions go to ft_utils/ directory."""
        fullpath = super().get_ext_fullpath(ext_name)
        # If running with --inplace, adjust the path to put files in ft_utils/ directory
        if self.inplace:
            # Change from ./_concurrency.so to ./ft_utils/_concurrency.so
            filename = os.path.basename(fullpath)
            # Get the package path from the extension name
            parts = ext_name.split(".")
            if parts[0] == "ft_utils":
                # Place in the ft_utils package directory
                fullpath = os.path.join("ft_utils", filename)
        return fullpath


def build_extensions() -> list[Extension]:
    """Build list of Extension objects for C extensions."""
    python_include = sysconfig.get_paths()["include"]
    include_dirs = [
        python_include,
        os.path.join(python_include, "internal"),
        "native/include",
        "native/src",
    ]

    extensions = [
        Extension(
            "ft_utils._concurrency",
            sources=[
                "native/src/_concurrency.c",
                "native/src/ft_core.c",
                "native/src/concurrent_data_structures/concurrent_dict.c",
                "native/src/concurrent_data_structures/atomic_int64.c",
                "native/src/concurrent_data_structures/atomic_reference.c",
                "native/src/concurrent_data_structures/concurrent_deque.c",
            ],
            include_dirs=include_dirs,
        ),
        Extension(
            "ft_utils._weave",
            sources=["native/src/_weave.c"],
            include_dirs=include_dirs,
        ),
        Extension(
            "ft_utils.local",
            sources=["native/src/local.c"],
            include_dirs=include_dirs,
        ),
        Extension(
            "ft_utils.synchronization",
            sources=["native/src/synchronization.c"],
            include_dirs=include_dirs,
        ),
        Extension(
            "ft_utils._test_compat",
            sources=["ft_utils/tests/_test_compat.c"],
            include_dirs=include_dirs,
        ),
        Extension(
            "ft_utils._test_weave",
            sources=["ft_utils/tests/_test_weave.c"],
            include_dirs=include_dirs,
        ),
    ]

    return extensions


def invoke_main() -> None:
    # Project metadata lives in pyproject.toml ([project]); setuptools ignores
    # anything duplicated here, so only the C extension build belongs in setup.py.
    setup(
        ext_modules=build_extensions(),
        cmdclass={"build_ext": BuildExtInplace},
    )


if __name__ == "__main__":
    invoke_main()
