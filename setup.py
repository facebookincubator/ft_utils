# Copyright (c) Meta Platforms, Inc. and affiliates.

import os
import shutil
import sys

from contextlib import contextmanager
from distutils import sysconfig

from setuptools import Extension, find_packages, setup


def check_venv():
    if sys.prefix == sys.base_prefix:
        raise RuntimeError(
            "setpy.py must run in a virtualenv with the correct version "
            + "of python against which you will build the wheel."
        )


def check_core_headers():
    include_dir = sysconfig.get_python_inc()
    if include_dir is None:
        raise RuntimeError("Python source code headers are not available.")

    if not os.path.exists(os.path.join(include_dir, "internal", "pycore_object.h")):
        raise RuntimeError("Python source code core headers are not available.")


def check_setup():
    check_venv()
    check_core_headers()


def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)


def remove_directory_contents(path):
    for filename in os.listdir(path):
        filepath = os.path.join(path, filename)
        try:
            shutil.rmtree(filepath)
        except NotADirectoryError:
            os.remove(filepath)


def create_package_structure(build_dir):
    python_dir = os.path.join(build_dir, "ft_utils")
    tests_dir = os.path.join(python_dir, "tests")
    native_dir = os.path.join(python_dir, "native")

    create_directory(python_dir)
    create_directory(tests_dir)
    create_directory(native_dir)

    return python_dir, tests_dir, native_dir


def copy_files(build_dir, script_dir, python_dir, tests_dir, native_dir):
    for filename in os.listdir(script_dir):
        filepath = os.path.join(script_dir, filename)

        if filename.endswith(".py"):
            if filename.startswith("test_") or filename.endswith("_bench.py"):
                shutil.copy(filepath, tests_dir)
            else:
                shutil.copy(filepath, python_dir)
        elif filename.endswith(".c") or filename.endswith(".h"):
            shutil.copy(filepath, native_dir)
        elif filename.endswith(".md"):
            shutil.copy(filepath, build_dir)


def create_init_py(python_dir):
    init_py_path = os.path.join(python_dir, "__init__.py")
    with open(init_py_path, "w"):
        pass


def create_license(script_dir, build_dir):
    license_from = os.path.join(script_dir, "LICENSE")
    license_to = os.path.join(build_dir, "LICENSE")
    if os.path.exists(license_from):
        shutil.copy(license_from, license_to)
    else:
        with open(license_to, "w") as f:
            f.write(
                "See https://github.com/facebookincubator/SocketRocket/blob/main/LICENSE\n"
            )


def create_setup_cfg(build_dir):
    setup_cfg_path = os.path.join(build_dir, "setup.cfg")
    with open(setup_cfg_path, "w") as f:
        f.write("[options]\n")
        f.write("packages = find:\n")


@contextmanager
def setup_args(*args):
    original_argv = sys.argv[:]
    sys.argv = ["setup.py"] + list(args)
    try:
        yield
    finally:
        sys.argv = original_argv


def invoke_main():
    check_setup()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(script_dir, "build")

    create_directory(build_dir)
    remove_directory_contents(build_dir)

    python_dir, tests_dir, native_dir = create_package_structure(build_dir)
    copy_files(build_dir, script_dir, python_dir, tests_dir, native_dir)
    create_init_py(python_dir)
    create_license(script_dir, build_dir)
    create_setup_cfg(build_dir)

    c_extensions = []
    for filename in os.listdir(script_dir):
        if filename.endswith(".c"):
            include_dir = sysconfig.get_python_inc()
            module_name = os.path.splitext(filename)[0]
            source_file = os.path.join("ft_utils", "native", filename)
            c_extensions.append(
                Extension(
                    f"ft_utils.{module_name}",
                    [source_file],
                    include_dirs=[include_dir, os.path.join(include_dir, "internal")],
                )
            )

    with open(os.path.join(build_dir, "README.md")) as readme_file:
        long_descr = readme_file.read()

    os.chdir("build")
    with setup_args("bdist_wheel"):
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
            packages=find_packages(where=build_dir),
            ext_modules=c_extensions,
            classifiers=[
                "Development Status :: 1 - alpha/Unstable",
                "Intended Audience :: Developers",
                "License :: OSI Approved :: MIT License",
                "Programming Language :: Python :: 3.12",
                "Programming Language :: Python :: 3.13",
            ],
        )


if __name__ == "__main__":
    invoke_main()
