# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import unittest
from typing import Callable

try:
    import ft_utils._test_compat as _test_compat
except ImportError:
    # @manual
    import ft_utils.tests._test_compat as _test_compat  # pyre-ignore[21]


class TestCompat(unittest.TestCase):
    def test_atomics(self) -> None:
        # pyre-ignore[16]: Module has no attribute
        test_cls = _test_compat.TestCompat
        methods: list[str] = [
            name for name in dir(test_cls) if callable(getattr(test_cls, name))
        ]

        test_obj: object = test_cls()
        errs: list[AssertionError] = []
        for method_name in methods:
            if str(method_name).startswith("test_atomic"):
                try:
                    method: Callable[..., object] = getattr(test_cls, method_name)
                    method(test_obj)
                except AssertionError as e:
                    errs.append(e)
        self.assertEqual(errs, [], str(errs))

    def test_get_item_ref(self) -> None:
        d: dict[str, int] = {"a": 1, "b": 2}
        # pyre-ignore[16]: Module has no attribute
        test_obj: object = _test_compat.TestCompat()
        # pyre-ignore[16]: object has no attribute
        self.assertEqual(test_obj.test_PyDict_GetItemRef(d, "a"), 1)
        # pyre-ignore[16]
        self.assertEqual(test_obj.test_PyDict_GetItemRef(d, "b"), 2)
        # pyre-ignore[16]
        self.assertIsNone(test_obj.test_PyDict_GetItemRef(d, "c"))
        with self.assertRaises(TypeError):
            # pyre-ignore[16]
            test_obj.test_PyDict_GetItemRef(1, "a")


if __name__ == "__main__":
    unittest.main()
