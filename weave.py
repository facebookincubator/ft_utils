# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-unsafe

import sys

import ft_utils._weave  # @manual


def _check_version():
    required_version = (3, 13)
    current_version = sys.version_info

    if current_version < required_version:
        raise RuntimeError(
            f"Python version {current_version} is not supported for tls. Please upgrade to at least version {required_version[0]}.{required_version[1]}"
        )


def register_native_destructor(*args):
    _check_version()
    sys.modules[__name__].register_native_destructor = (
        ft_utils._weave.register_native_destructor
    )
    return register_native_destructor(*args)


def unregister_native_destructor(*args):
    _check_version()
    sys.modules[__name__].unregister_native_destructor = (
        ft_utils._weave.unregister_native_destructor
    )
    return unregister_native_destructor(*args)
