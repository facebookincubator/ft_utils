# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import os
import shutil
import sys
import sysconfig

from contextlib import contextmanager

from setuptools import Extension, find_packages, setup


def check_compiler() -> None:
    """
    Check the default compiler for the current platform and fix up name clashed on windows.

    Prints the found compiler class.
    """
    import distutils.ccompiler as cc

    plat = os.name
    compiler = cc.get_default_compiler(plat)
    # pyre-ignore
    (module_name, class_name, long_description) = cc.compiler_class[compiler]

    module_name = "distutils." + module_name
    __import__(module_name)
    module = sys.modules[module_name]
    klass = vars(module)[class_name]
    print(f"Found compiler {module} -> {klass}")


def get_include_dir() -> str | None:
    """
    Get the include directory from sysconfig.

    Returns:
        The include directory path, or None if not available.
    """
    config_paths = sysconfig.get_paths()
    return config_paths["include"]


def check_core_headers() -> None:
    """
    Check if Python source code headers are available.

    Raises:
        RuntimeError: If headers are not available.
    """
    include_dir = get_include_dir()
    if include_dir is None:
        raise RuntimeError("Python source code headers are not available.")

    if not os.path.exists(os.path.join(include_dir, "internal", "pycore_object.h")):
        raise RuntimeError("Python source code core headers are not available.")


def check_setup() -> None:
    """
    Run setup checks (virtual environment, core headers, compiler).
    """
    check_core_headers()
    check_compiler()


def create_directory(path: str) -> None:
    """
    Create a directory at the given path if it does not exist.

    Args:
        path: The directory path to create.
    """
    if not os.path.exists(path):
        os.makedirs(path)


def remove_directory_contents(path: str) -> None:
    """
    Remove all contents of the given directory.

    Args:
        path: The directory path to clear.
    """
    for filename in os.listdir(path):
        filepath = os.path.join(path, filename)
        try:
            shutil.rmtree(filepath)
        except NotADirectoryError:
            os.remove(filepath)


def create_package_structure(build_dir: str) -> tuple[str, str, str]:
    """
    Create the package structure within the build directory.

    Args:
        build_dir: The build directory path.

    Returns:
        A tuple containing the python, tests, and native directory paths.
    """
    python_dir = os.path.join(build_dir, "ft_utils")
    tests_dir = os.path.join(python_dir, "tests")
    native_dir = os.path.join(python_dir, "native")

    create_directory(python_dir)
    create_directory(tests_dir)
    create_directory(native_dir)

    return python_dir, tests_dir, native_dir


def copy_files(
    build_dir: str, script_dir: str, python_dir: str, tests_dir: str, native_dir: str
) -> None:
    """
    Copy files from the script directory to their respective destinations.

    Args:
        build_dir: The build directory path.
        script_dir: The script directory path.
        python_dir: The python directory path.
        tests_dir: The tests directory path.
        native_dir: The native directory path.
    """
    for filename in os.listdir(script_dir):
        filepath = os.path.join(script_dir, filename)

        if filename.endswith(".py"):
            # Both benchmarks and test_ files are run as tests in CI.
            if filename.startswith("test_") or filename.endswith("_bench.py"):
                shutil.copy(filepath, tests_dir)
            # Do not copy yourself into the wheel.
            elif filename != "setup.py":
                shutil.copy(filepath, python_dir)
        elif filename.endswith(".c") or filename.endswith(".h"):
            shutil.copy(filepath, native_dir)
        elif filename.endswith(".md"):
            shutil.copy(filepath, build_dir)


def create_init_py(module_dir: str) -> None:
    """
    Create an empty __init__.py file in the given module directory if none exists.

    Args:
        module_dir: The module directory path.
    """
    init_py_path = os.path.join(module_dir, "__init__.py")
    if not os.path.exists(init_py_path):
        with open(init_py_path, "w"):
            pass


def create_license(script_dir: str, build_dir: str) -> None:
    """
    Create a license file in the build directory.

    Args:
        script_dir: The script directory path.
        build_dir: The build directory path.
    """
    license_from = os.path.join(script_dir, "LICENSE")
    license_to = os.path.join(build_dir, "LICENSE")
    if os.path.exists(license_from):
        shutil.copy(license_from, license_to)
    else:
        with open(license_to, "w") as f:
            f.write(
                "See https://github.com/facebookincubator/SocketRocket/blob/main/LICENSE\n"
            )


def create_setup_cfg(build_dir: str) -> None:
    """
    Create a setup.cfg file in the build directory.

    Args:
        build_dir: The build directory path.
    """
    setup_cfg_path = os.path.join(build_dir, "setup.cfg")
    with open(setup_cfg_path, "w") as f:
        f.write("[options]\n")
        f.write("packages = find:\n")


def invoke_main() -> None:
    """
    Run the main setup process.
    """
    check_setup()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(script_dir, "build")

    create_directory(build_dir)
    remove_directory_contents(build_dir)

    python_dir, tests_dir, native_dir = create_package_structure(build_dir)
    copy_files(build_dir, script_dir, python_dir, tests_dir, native_dir)
    create_init_py(python_dir)
    create_init_py(tests_dir)
    create_license(script_dir, build_dir)
    create_setup_cfg(build_dir)

    supporting_files = []
    extension_modules = []
    include_dir = get_include_dir()

    # Any file starting ft_ and ending .c will be compiled into all libraries as
    # support c file.
    for filename in os.listdir(native_dir):
        if filename.endswith(".c"):
            if filename.startswith("ft_"):
                supporting_files.append(filename)
            else:
                extension_modules.append(filename)

    c_extensions = []
    for module_filename in extension_modules:
        module_name = os.path.splitext(module_filename)[0]
        source_files = [os.path.join("ft_utils", "native", module_filename)]
        source_files += [
            os.path.join("ft_utils", "native", support_file)
            for support_file in supporting_files
        ]
        c_extensions.append(
            Extension(
                f"ft_utils.{module_name}",
                source_files,
                include_dirs=[
                    include_dir,
                    # pyre-ignore
                    os.path.join(include_dir, "internal"),
                ],
            )
        )

    with open(os.path.join(build_dir, "README.md")) as readme_file:
        long_descr = readme_file.read()

    os.chdir("build")
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
        ext_modules=c_extensions,
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
