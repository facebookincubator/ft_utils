# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-unsafe

import unittest

try:
    import ft_utils._test_compat as _test_compat
except ImportError:
    # @manual
    import ft_utils.tests._test_compat as _test_compat  # pyre-ignore


class TestCompat(unittest.TestCase):
    def test_atomics(self):
        test_cls = _test_compat.TestCompat
        methods = [name for name in dir(test_cls) if callable(getattr(test_cls, name))]

        test_obj = test_cls()
        errs = []
        for method_name in methods:
            if str(method_name).startswith("test_atomic"):
                try:
                    method = getattr(test_cls, method_name)
                    method(test_obj)
                except AssertionError as e:
                    errs.append(e)
        self.assertEqual(errs, [], str(errs))

    def test_get_item_ref(self):
        d = {"a": 1, "b": 2}
        test_obj = _test_compat.TestCompat()
        self.assertEqual(test_obj.test_PyDict_GetItemRef(d, "a"), 1)
        self.assertEqual(test_obj.test_PyDict_GetItemRef(d, "b"), 2)
        self.assertIsNone(test_obj.test_PyDict_GetItemRef(d, "c"))
        with self.assertRaises(TypeError):
            test_obj.test_PyDict_GetItemRef(1, "a")


if __name__ == "__main__":
    unittest.main()
