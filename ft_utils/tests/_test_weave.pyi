# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

def reset() -> None:
    """Reset the destructor test values."""
    ...

def register_destructor_1() -> None:
    """Register a reset destructor for a tls 1"""
    ...

def register_destructor_reset_1() -> None:
    """Register a destructor for a tls 1"""
    ...

def unregister_destructor_1() -> int:
    """Unregister a destructor for a tls 1"""
    ...

def register_destructor_2() -> None:
    """Register a destructor for a tls 2"""
    ...

def unregister_destructor_2() -> int:
    """Unregister a destructor for a tls 2"""
    ...

def get_destructor_called_1() -> int:
    """Get the value of destructor_called_1"""
    ...

def get_destructor_called_2() -> int:
    """Get the value of destructor_called_2"""
    ...
