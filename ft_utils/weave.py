# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import sys

import ft_utils._weave  # @manual


def _check_enabled(version: bool = True, experimental: bool = True) -> None:
    if experimental:
        if not ft_utils.ENABLE_EXPERIMENTAL:
            raise RuntimeError("Experimental support not enabled for ft_utils")
    required_version = (3, 13)
    current_version = sys.version_info

    if current_version < required_version:
        raise RuntimeError(
            f"Python version {current_version}; >={required_version[0]}.{required_version[1]} is required"
        )


def register_native_destructor(var: int, destructor: int) -> None:
    """Register a native C ABI destructor for native thread local storage."""
    _check_enabled()
    sys.modules[
        __name__
    ].register_native_destructor = ft_utils._weave.register_native_destructor
    return register_native_destructor(var, destructor)


def unregister_native_destructor(var: int) -> bool:
    """Unregister any already registered destructors for the storage pointed to by the argument and return if any unregistered."""
    _check_enabled()
    sys.modules[
        __name__
    ].unregister_native_destructor = ft_utils._weave.unregister_native_destructor
    return unregister_native_destructor(var)
