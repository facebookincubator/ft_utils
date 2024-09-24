# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import gc
import unittest
import weakref

from ft_utils.concurrent import AtomicFlag, AtomicInt64, AtomicReference, ConcurrentDict
from ft_utils.local import BatchExecutor, LocalWrapper


class Foo:
    pass


class WeakReferenceTestBase(unittest.TestCase):
    def get_object_to_reference(self) -> object:
        return Foo()

    def test_weak_ref_direct(self) -> None:
        obj = self.get_object_to_reference()
        ref = weakref.ref(obj)
        self.assertEqual(ref(), obj)

    def test_weak_ref_in_list(self) -> None:
        obj = self.get_object_to_reference()
        lst = [obj]
        ref = weakref.ref(obj)
        self.assertEqual(ref(), obj)
        del lst
        self.assertEqual(ref(), obj)

    def test_weak_ref_in_cycle(self) -> None:
        l1 = [self.get_object_to_reference()]
        l2 = [l1, weakref.ref(l1[0])]
        ref1 = weakref.ref(l1[0])
        self.assertEqual(ref1(), l1[0])
        del l1
        del l2
        while gc.collect():
            pass
        self.assertIsNone(ref1())

    def test_weak_ref_deleted(self) -> None:
        obj = self.get_object_to_reference()
        ref = weakref.ref(obj)
        del obj
        self.assertIsNone(ref())


class TestWeakRefToLocalWrapper(WeakReferenceTestBase):
    def get_object_to_reference(self) -> LocalWrapper:
        return LocalWrapper(None)


class TestWeakRefToBatchExecutor(WeakReferenceTestBase):
    def get_object_to_reference(self) -> BatchExecutor:
        return BatchExecutor(lambda: None, 8)


class TestWeakRefToConcurrentDict(WeakReferenceTestBase):
    def get_object_to_reference(self) -> ConcurrentDict:
        return ConcurrentDict()


class TestWeakRefToAtomicInt64(WeakReferenceTestBase):
    def get_object_to_reference(self) -> AtomicInt64:
        return AtomicInt64()


class TestWeakRefToAtomicReference(WeakReferenceTestBase):
    def get_object_to_reference(self) -> AtomicReference:
        return AtomicReference()  # pyre-ignore[20]


class TestWeakRefToAtomicFlag(WeakReferenceTestBase):
    def get_object_to_reference(self) -> AtomicFlag:
        return AtomicFlag(True)


if __name__ == "__main__":
    unittest.main()
