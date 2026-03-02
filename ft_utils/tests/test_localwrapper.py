# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-strict

import asyncio
import gc
import traceback
import types
import unittest
from collections.abc import Iterator
from contextlib import ContextDecorator
from typing import Any

from ft_utils.local import LocalWrapper


class TestLocalWrapperSmokes(unittest.TestCase):
    def setUp(self) -> None:
        self.obj: list[int] = [1, 2, 3]
        self.wrapper: LocalWrapper = LocalWrapper(self.obj)

    def test_constructor(self) -> None:
        self.assertIsNotNone(self.wrapper)
        self.assertEqual(self.wrapper.wrapped, self.obj)

    def test_getattr(self) -> None:
        self.assertEqual(self.wrapper.append, self.obj.append)

    def test_setattr(self) -> None:
        class Thing:
            pass

        wrapper: LocalWrapper = LocalWrapper(Thing())
        new_attr: int = 123
        wrapper.new_attr = new_attr
        self.assertEqual(wrapper.new_attr, new_attr)

    def test_getitem(self) -> None:
        self.assertEqual(self.wrapper[1], self.obj[1])

    def test_setitem(self) -> None:
        self.wrapper[1] = 100
        self.assertEqual(self.wrapper[1], 100)

    def test_delitem(self) -> None:
        del self.wrapper[1]
        self.assertEqual(len(self.wrapper), 2)

    def test_len(self) -> None:
        self.assertEqual(len(self.wrapper), len(self.obj))

    def test_iter(self) -> None:
        self.assertListEqual(list(iter(self.wrapper)), self.obj)

    def test_call(self) -> None:
        self.wrapper.append(4)
        self.assertIn(4, self.wrapper)

    def test_str(self) -> None:
        self.assertEqual(str(self.wrapper), str(self.obj))

    def test_richcompare(self) -> None:
        another_wrapper: LocalWrapper = LocalWrapper([1, 2, 3])
        self.assertEqual(self.wrapper, another_wrapper)

    def test_number_operations(self) -> None:
        # Test a few number operations
        self.assertEqual(self.wrapper + [4, 5], self.obj + [4, 5])
        self.assertEqual(self.wrapper * 2, self.obj * 2)

    def test_inplace_operations(self) -> None:
        self.wrapper += [4, 5]
        self.obj += [4, 5]
        self.assertEqual(self.wrapper, self.obj)
        self.wrapper *= 3
        self.obj *= 3
        self.assertEqual(self.wrapper, self.obj)

    def test_inplace_operations_recursive(self) -> None:
        id_checker: object = self.wrapper.wrapped
        self.wrapper += LocalWrapper([4, 5])
        self.assertIs(id_checker, self.wrapper.wrapped)
        self.assertIs(self.wrapper.wrapped, self.obj)
        id_checker = self.obj
        self.obj += LocalWrapper([4, 5])
        self.assertIs(type(self.obj), list)
        # See T196065060 - This should be asserIs but something is not working.
        self.assertIsNot(id_checker, self.obj)
        self.assertNotEqual(self.wrapper, self.obj)
        self.assertNotEqual(self.obj, self.wrapper)

    def test_bool(self) -> None:
        self.assertTrue(bool(self.wrapper))

    def test_int_float(self) -> None:
        num_wrapper: LocalWrapper = LocalWrapper(10)
        self.assertEqual(int(num_wrapper), 10)
        self.assertEqual(float(num_wrapper), 10.0)

    def test_gc(self) -> None:
        del self.wrapper
        gc.collect()
        self.assertTrue(gc.garbage == [])
        self.wrapper = LocalWrapper(self)
        gc.collect()
        self.assertTrue(gc.garbage == [])
        self.wrapper = LocalWrapper((self, self))
        gc.collect()
        self.assertTrue(gc.garbage == [])
        self.wrapper = LocalWrapper([self, None])
        self.wrapper[1] = self.wrapper
        gc.collect()
        self.assertTrue(gc.garbage == [])

    def test_repr(self) -> None:
        obj_repr: str = repr(self.obj)
        wrapper_repr: str = repr(self.wrapper)
        expected_repr: str = f"<LocalWrapper: {obj_repr}>"
        self.assertEqual(wrapper_repr, expected_repr)

    def test_dict(self) -> None:
        ld: LocalWrapper = LocalWrapper({})
        ld[1] = 2
        self.assertEqual(ld[1], 2)
        self.assertTrue(1 in ld)
        for k, v in ld.items():
            self.assertEqual(k, 1)
            self.assertEqual(v, 2)
        del ld[1]
        self.assertFalse(1 in ld)
        ld[1] = "dog"
        ld[1] = 3
        for k in ld.keys():
            self.assertEqual(k, 1)
        for v in ld.values():
            self.assertEqual(v, 3)

    def test_slice(self) -> None:
        tp: tuple[int, ...] = (1, 2, 3, 4, 5, 6)
        w: LocalWrapper = LocalWrapper(tp)
        self.assertIs(w[:], tp)
        self.assertEqual(w[:2], tp[:2])
        self.assertEqual(w[2:], tp[2:])
        self.assertEqual(w[1:4], tp[1:4])
        self.assertEqual(w[-2:-1], tp[-2:-1])


class TestLocalWrapperBytearray(unittest.TestCase):
    def setUp(self) -> None:
        self.wrapper: LocalWrapper = LocalWrapper(bytearray([1, 2]))

    def test_bytearray_addition(self) -> None:
        self.assertEqual(self.wrapper + self.wrapper, bytearray([1, 2, 1, 2]))
        self.assertEqual(self.wrapper + self.wrapper.wrapped, bytearray([1, 2, 1, 2]))
        self.assertEqual(self.wrapper.wrapped + self.wrapper, bytearray([1, 2, 1, 2]))

    def test_bytearray_multiplication(self) -> None:
        self.assertEqual(self.wrapper * 2, bytearray([1, 2, 1, 2]))

    def test_bytearray_eq(self) -> None:
        self.assertTrue(self.wrapper == self.wrapper.wrapped)
        self.assertTrue(self.wrapper.wrapped == self.wrapper)


class TestLocalWrapperIterExtra(unittest.TestCase):
    def setUp(self) -> None:
        self.obj: tuple[int, ...] = (1, 2, 3)
        self.wrapper: LocalWrapper = LocalWrapper(self.obj)

    def test_empty_iter(self) -> None:
        empty_wrapper: LocalWrapper = LocalWrapper([])
        self.assertListEqual(list(iter(empty_wrapper)), [])

    def test_exception_in_iteration(self) -> None:
        class CustomIterable:
            def __iter__(self) -> "CustomIterable":
                return self

            def __next__(self) -> None:
                raise RuntimeError("Test Exception")

        error_wrapper: LocalWrapper = LocalWrapper(CustomIterable())
        with self.assertRaises(RuntimeError):
            list(iter(error_wrapper))

    def test_multiple_iterations(self) -> None:
        iter1: tuple[object, ...] = tuple(iter(self.wrapper))
        iter2: tuple[object, ...] = tuple(iter(self.wrapper))
        self.assertEqual(iter1, self.obj)
        self.assertEqual(iter2, self.obj)


class TestLocalWrapperHash(unittest.TestCase):
    def setUp(self) -> None:
        self.obj: str = "Hello World"
        self.wrapper: LocalWrapper = LocalWrapper(self.obj)

    def test_hash(self) -> None:
        obj_hash: int = hash(self.obj)
        wrapper_hash: int = hash(self.wrapper)
        self.assertEqual(wrapper_hash, obj_hash)

    def test_hash_consistency(self) -> None:
        wrapper_hash1: int = hash(self.wrapper)
        wrapper_hash2: int = hash(self.wrapper)
        self.assertEqual(wrapper_hash1, wrapper_hash2)

    def test_hash_equality(self) -> None:
        another_wrapper: LocalWrapper = LocalWrapper(self.obj)
        self.assertEqual(hash(self.wrapper), hash(another_wrapper))
        another_wrapper = LocalWrapper(self.wrapper)
        self.assertEqual(hash(self.wrapper), hash(another_wrapper))


class TestLocalWrapperBuffer(unittest.TestCase):
    def setUp(self) -> None:
        self.byte_array: bytearray = bytearray(b"example data")
        self.wrapper: LocalWrapper = LocalWrapper(self.byte_array)

    def test_getbuffer(self) -> None:
        buf = memoryview(self.wrapper)
        self.assertEqual(buf.tobytes(), self.byte_array)

    def test_releasebuffer(self) -> None:
        buf = memoryview(self.wrapper)
        del buf
        # If no exceptions, assume success
        self.assertTrue(True)

    def test_buffer_integrity(self) -> None:
        with memoryview(self.wrapper) as buf:
            buf[0] = ord("z")
        self.assertEqual(self.byte_array[0], ord("z"))

    def test_buffer_type(self) -> None:
        buf = memoryview(self.wrapper)
        self.assertIsInstance(buf, memoryview)


class NumberAPI:
    def __init__(self, value: Any) -> None:
        self.value: Any = value

    def __add__(self, other: Any) -> Any:
        return self.value + other

    def __sub__(self, other: Any) -> Any:
        return self.value - other

    def __mul__(self, other: Any) -> Any:
        return self.value * other

    def __truediv__(self, other: Any) -> Any:
        return self.value / other

    def __floordiv__(self, other: Any) -> Any:
        return self.value // other

    def __mod__(self, other: Any) -> Any:
        return self.value % other

    def __pow__(self, other: Any, modulus: Any = None) -> Any:
        return self.value**other

    def __lshift__(self, other: Any) -> Any:
        return self.value << other

    def __rshift__(self, other: Any) -> Any:
        return self.value >> other

    def __and__(self, other: Any) -> Any:
        return self.value & other

    def __or__(self, other: Any) -> Any:
        return self.value | other

    def __xor__(self, other: Any) -> Any:
        return self.value ^ other

    def __iadd__(self, other: Any) -> "NumberAPI":
        self.value += other
        return self

    def __isub__(self, other: Any) -> "NumberAPI":
        self.value -= other
        return self

    def __imul__(self, other: Any) -> "NumberAPI":
        self.value *= other
        return self

    def __itruediv__(self, other: Any) -> "NumberAPI":
        self.value /= other
        return self

    def __ifloordiv__(self, other: Any) -> "NumberAPI":
        self.value //= other
        return self

    def __imod__(self, other: Any) -> "NumberAPI":
        self.value %= other
        return self

    def __ipow__(self, other: Any) -> "NumberAPI":
        self.value **= other
        return self

    def __ilshift__(self, other: Any) -> "NumberAPI":
        self.value <<= other
        return self

    def __irshift__(self, other: Any) -> "NumberAPI":
        self.value >>= other
        return self

    def __iand__(self, other: Any) -> "NumberAPI":
        self.value &= other
        return self

    def __ior__(self, other: Any) -> "NumberAPI":
        self.value |= other
        return self

    def __ixor__(self, other: Any) -> "NumberAPI":
        self.value ^= other
        return self

    def __invert__(self) -> Any:
        return ~(self.value)

    def __divmod__(self, other: Any) -> tuple[Any, Any]:
        return divmod(self.value, other)

    def __pos__(self) -> Any:
        return +(self.value)

    def __neg__(self) -> Any:
        return -(self.value)

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        return self.value == other

    def __int__(self) -> int:
        return int(self.value)

    def __float__(self) -> float:
        return float(self.value)


class TestLocalWrapperInt(unittest.TestCase):
    def setUp(self) -> None:
        self.num: object = 10
        self.wrapper: LocalWrapper = LocalWrapper(self.num)

    def test_add(self) -> None:
        result: object = self.wrapper + 5
        self.assertEqual(result, 15)

    def test_subtract(self) -> None:
        result: object = self.wrapper - 5
        self.assertEqual(result, 5)

    def test_multiply(self) -> None:
        result: object = self.wrapper * 5
        self.assertEqual(result, 50)

    def test_divide(self) -> None:
        result: object = self.wrapper / 2
        self.assertEqual(result, 5)

    def test_floor_divide(self) -> None:
        result: object = self.wrapper // 3
        self.assertEqual(result, 3)

    def test_modulus(self) -> None:
        result: object = self.wrapper % 3
        self.assertEqual(result, 1)

    def test_power(self) -> None:
        result: object = self.wrapper**2
        self.assertEqual(result, 100)

    def test_negative(self) -> None:
        result: object = -self.wrapper
        self.assertEqual(result, -10)

    def test_positive(self) -> None:
        result: object = +self.wrapper
        self.assertEqual(result, 10)

    def test_absolute(self) -> None:
        negative_wrapper: LocalWrapper = LocalWrapper(-10)
        result: object = abs(negative_wrapper)
        self.assertEqual(result, 10)

    def test_inplace_add(self) -> None:
        self.wrapper += 5
        self.assertEqual(self.wrapper, 15)

    def test_inplace_subtract(self) -> None:
        self.wrapper -= 5
        self.assertEqual(self.wrapper, 5)

    def test_inplace_multiply(self) -> None:
        self.wrapper *= 5
        self.assertEqual(self.wrapper, 50)

    def test_inplace_divide(self) -> None:
        self.wrapper /= 2
        self.assertEqual(self.wrapper, 5)

    def test_inplace_floor_divide(self) -> None:
        self.wrapper //= 3
        self.assertEqual(self.wrapper, 3)

    def test_inplace_modulus(self) -> None:
        self.wrapper %= 3
        self.assertEqual(self.wrapper, 1)

    def test_inplace_power(self) -> None:
        self.wrapper **= 2
        self.assertEqual(self.wrapper, 100)

    def test_bool(self) -> None:
        self.assertTrue(bool(self.wrapper))
        zero_wrapper: LocalWrapper = LocalWrapper(0)
        self.assertFalse(bool(zero_wrapper))

    def test_int(self) -> None:
        self.assertEqual(int(self.wrapper), 10)

    def test_float(self) -> None:
        self.assertEqual(float(self.wrapper), 10.0)

    def test_divmod(self) -> None:
        self.assertEqual(divmod(self.wrapper, 3), (3, 1))

    def test_invertd(self) -> None:
        self.assertEqual(~self.wrapper, -11)


class TestLocalWrapperNotImpl(unittest.TestCase):
    def setUp(self) -> None:
        self.not_num: object = object()
        self.wrapper: LocalWrapper = LocalWrapper(self.not_num)

    def test_add(self) -> None:
        with self.assertRaises(TypeError):
            self.wrapper + 5

    def test_subtract(self) -> None:
        with self.assertRaises(TypeError):
            self.wrapper - 5

    def test_multiply(self) -> None:
        with self.assertRaises(TypeError):
            self.wrapper * 5

    def test_divide(self) -> None:
        with self.assertRaises(TypeError):
            self.wrapper / 2

    def test_floor_divide(self) -> None:
        with self.assertRaises(TypeError):
            self.wrapper // 3

    def test_modulus(self) -> None:
        with self.assertRaises(TypeError):
            self.wrapper % 3

    def test_power(self) -> None:
        with self.assertRaises(TypeError):
            self.wrapper**2

    def test_negative(self) -> None:
        with self.assertRaises(TypeError):
            -self.wrapper

    def test_positive(self) -> None:
        with self.assertRaises(TypeError):
            +self.wrapper

    def test_absolute(self) -> None:
        with self.assertRaises(TypeError):
            abs(self.wrapper)

    def test_inplace_add(self) -> None:
        with self.assertRaises(TypeError):
            self.wrapper += 5

    def test_inplace_subtract(self) -> None:
        with self.assertRaises(TypeError):
            self.wrapper -= 5

    def test_inplace_multiply(self) -> None:
        with self.assertRaises(TypeError):
            self.wrapper *= 5

    def test_inplace_divide(self) -> None:
        with self.assertRaises(TypeError):
            self.wrapper /= 2

    def test_inplace_floor_divide(self) -> None:
        with self.assertRaises(TypeError):
            self.wrapper //= 3

    def test_inplace_modulus(self) -> None:
        with self.assertRaises(TypeError):
            self.wrapper %= 3

    def test_inplace_power(self) -> None:
        with self.assertRaises(TypeError):
            self.wrapper **= 2

    def test_bool(self) -> None:
        class Thing:
            def __bool__(self) -> bool:
                raise TypeError("Just to check")

        wrapper: LocalWrapper = LocalWrapper(Thing())
        with self.assertRaises(TypeError):
            bool(wrapper)

    def test_int(self) -> None:
        with self.assertRaises(TypeError):
            int(self.wrapper)

    def test_float(self) -> None:
        with self.assertRaises(TypeError):
            float(self.wrapper)

    def test_divmod(self) -> None:
        with self.assertRaises(TypeError):
            divmod(self.wrapper, 3)

    def test_invertd(self) -> None:
        with self.assertRaises(TypeError):
            ~self.wrapper


class AttrDel(ContextDecorator):
    def __init__(self, obj: type[object], attr: str) -> None:
        self.obj: type[object] = obj
        self.attr: str = attr
        self.has_attr: bool = hasattr(obj, attr)
        if self.has_attr:
            self.value: object = getattr(obj, attr)

    def __enter__(self) -> None:
        if self.has_attr:
            delattr(self.obj, self.attr)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: types.TracebackType | None,
    ) -> None:
        if self.has_attr:
            setattr(self.obj, self.attr, self.value)


class TestLocalWrapperNumberAPI(TestLocalWrapperInt):
    def setUp(self) -> None:
        self.num: object = NumberAPI(10)
        self.wrapper: LocalWrapper = LocalWrapper(self.num)


class ASequence:
    def __init__(self) -> None:
        self._items: list[object] = []

    def __getitem__(self, index: Any) -> Any:
        return self._items[index]

    def __setitem__(self, index: Any, value: Any) -> None:
        self._items[index] = value

    def __delitem__(self, index: Any) -> None:
        del self._items[index]

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[object]:
        return iter(self._items)

    def __iadd__(self, other: Any) -> "ASequence":
        if other is self:
            self._items += self._items
        else:
            self._items += other
        return self

    def append(self, item: object) -> None:
        self._items.append(item)

    def __repr__(self) -> str:
        return f"ASequence({self._items})"


class TestMutations(unittest.TestCase):
    def testRemoveAdd(self) -> None:
        num: NumberAPI = NumberAPI(10)
        wrapper: LocalWrapper = LocalWrapper(num)
        with AttrDel(NumberAPI, "__add__"):
            with self.assertRaisesRegex(
                TypeError, "unsupported operand type.*NumberAPI.*int"
            ):
                res = wrapper + 1
        res = wrapper + 1
        self.assertEqual(res, 11)

    def testAddAdd(self) -> None:
        with AttrDel(NumberAPI, "__add__"):
            num: NumberAPI = NumberAPI(10)
            wrapper: LocalWrapper = LocalWrapper(num)
            with self.assertRaisesRegex(
                TypeError, "unsupported operand type.*NumberAPI.*int"
            ):
                res = wrapper + 1
        res = wrapper + 1
        self.assertEqual(res, 11)

    def testChangeWrapped(self) -> None:
        wrapper: LocalWrapper = LocalWrapper(23)
        with self.assertRaises(AttributeError):
            wrapper.wrapped = 24

    def testChangeType(self) -> None:
        class Mutato(ASequence):
            def __init__(self, seq: list[object]) -> None:
                super().__init__()
                self._items = seq

        mut: Mutato = Mutato([1, 2, 3, 4])
        wrapper: LocalWrapper = LocalWrapper(mut)
        wrapper += wrapper
        mut.__class__ = NumberAPI  # pyre-ignore[8]
        mut.__init__(0)  # pyre-ignore[6, 16]
        wrapper += 23
        self.assertEqual(wrapper / 1, 23)


class Matrix:
    def __init__(self, rows: int, cols: int) -> None:
        self.rows: int = rows
        self.cols: int = cols
        self.data: list[list[int]] = [[0 for _ in range(cols)] for _ in range(rows)]

    def __getitem__(self, index: int) -> list[int]:
        return self.data[index]

    def __setitem__(self, index: int, value: list[int]) -> None:
        self.data[index] = value

    def __matmul__(self, other: "Matrix") -> "Matrix":
        if self.cols != other.rows:
            raise ValueError("Matrices cannot be multiplied")
        result: Matrix = Matrix(self.rows, other.cols)
        for i in range(self.rows):
            for j in range(other.cols):
                for k in range(self.cols):
                    result[i][j] += self[i][k] * other[k][j]
        return result

    def __imatmul__(self, other: "Matrix") -> "Matrix":
        if self.cols != other.rows:
            raise ValueError("Matrices cannot be multiplied")
        result: Matrix = Matrix(self.rows, other.cols)
        for i in range(self.rows):
            for j in range(other.cols):
                for k in range(self.cols):
                    result[i][j] += self[i][k] * other[k][j]
        self.data = result.data
        return self

    def __repr__(self) -> str:
        return str(self.data)


class TestLocalWrapperMatrix(unittest.TestCase):
    def setUp(self) -> None:
        m1: Matrix = Matrix(2, 2)
        m1[0][0] = 1
        m1[0][1] = 2
        m1[1][0] = 3
        m1[1][1] = 4
        m2: Matrix = Matrix(2, 2)
        m2[0][0] = 5
        m2[0][1] = 6
        m2[1][0] = 7
        m2[1][1] = 8
        self.m1: Matrix = m1
        self.m2: Matrix = m2
        self.wrapped1: LocalWrapper = LocalWrapper(m1)
        self.wrapped2: LocalWrapper = LocalWrapper(m2)

    def test_matrix_multiply(self) -> None:
        result: object = self.m1 @ self.m2
        self.assertEqual(result.data, [[19, 22], [43, 50]])
        result = self.wrapped1 @ self.wrapped2
        self.assertEqual(result.data, [[19, 22], [43, 50]])
        result = self.wrapped1 @ self.m2
        self.assertEqual(result.data, [[19, 22], [43, 50]])
        result = self.m1 @ self.wrapped2
        self.assertEqual(result.data, [[19, 22], [43, 50]])

    def test_inplacematrix_multiply(self) -> None:
        self.wrapped1 @= self.wrapped2
        self.assertEqual(self.m1.data, [[19, 22], [43, 50]])


class TestLocalWrapperSequenceAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.seq: list[int] = [1, 2, 3, 4, 5]
        self.wrapper: LocalWrapper = LocalWrapper(self.seq)

    def test_getitem(self) -> None:
        self.assertEqual(self.wrapper[2], 3)

    def test_setitem(self) -> None:
        self.wrapper[2] = 99
        self.assertEqual(self.wrapper[2], 99)

    def test_delitem(self) -> None:
        del self.wrapper[2]
        self.assertNotIn(3, self.wrapper)

    def test_len(self) -> None:
        self.assertEqual(len(self.wrapper), 5)

    def test_concat(self) -> None:
        result: object = self.wrapper + [6, 7]
        self.assertEqual(result, [1, 2, 3, 4, 5, 6, 7])

    def test_repeat(self) -> None:
        result: object = self.wrapper * 2
        self.assertEqual(result, [1, 2, 3, 4, 5, 1, 2, 3, 4, 5])

    def test_contains(self) -> None:
        self.assertTrue(3 in self.wrapper)
        self.assertFalse(6 in self.wrapper)

    def test_iter(self) -> None:
        items: list[object] = [item for item in self.wrapper]
        self.assertEqual(items, [1, 2, 3, 4, 5])
        it: Any = iter(self.wrapper)
        self.assertEqual(next(it), 1)
        self.assertEqual(next(it), 2)
        self.assertEqual(next(it), 3)
        self.assertEqual(next(it), 4)
        self.assertEqual(next(it), 5)
        with self.assertRaises(StopIteration):
            next(it)

    def test_slice_get(self) -> None:
        self.assertEqual(self.wrapper[1:3], [2, 3])

    def test_slice_set(self) -> None:
        self.wrapper[1:3] = [8, 9]
        self.assertEqual(self.wrapper[1], 8)
        self.assertEqual(self.wrapper[2], 9)

    def test_slice_del(self) -> None:
        del self.wrapper[1:3]
        self.assertEqual(list(self.wrapper), [1, 4, 5])

    def test_error_on_non_sequence(self) -> None:
        with self.assertRaises(TypeError):
            non_seq_wrapper: LocalWrapper = LocalWrapper(10)
            non_seq_wrapper[0]

    def test_error_on_out_of_bounds(self) -> None:
        with self.assertRaises(IndexError):
            _ = self.wrapper[10]

    def test_error_on_wrong_type_index(self) -> None:
        with self.assertRaises(TypeError):
            _ = self.wrapper["a"]


class WithSlots:
    __slots__ = ["a", "b"]

    def __init__(self, a: object, b: object) -> None:
        self.a: object = a
        self.b: object = b


class WithProperties:
    def __init__(self, value: object) -> None:
        self._value: object = value

    @property
    def value(self) -> object:
        return self._value

    @value.setter
    def value(self, new_value: object) -> None:
        self._value = new_value


class TestLocalWrapperAttributes(unittest.TestCase):
    def test_slots_get_set(self) -> None:
        obj: WithSlots = WithSlots(1, 2)
        wrapper: LocalWrapper = LocalWrapper(obj)
        # Test getting attributes
        self.assertEqual(wrapper.a, 1)
        self.assertEqual(wrapper.b, 2)
        # Test setting attributes
        wrapper.a = 10
        wrapper.b = 20
        self.assertEqual(wrapper.a, 10)
        self.assertEqual(wrapper.b, 20)

    def test_properties_get_set(self) -> None:
        obj: WithProperties = WithProperties(100)
        wrapper: LocalWrapper = LocalWrapper(obj)
        # Test getting property
        self.assertEqual(wrapper.value, 100)
        # Test setting property
        wrapper.value = 200
        self.assertEqual(wrapper.value, 200)

    def test_error_on_nonexistent_attribute(self) -> None:
        obj: WithSlots = WithSlots(1, 2)
        wrapper: LocalWrapper = LocalWrapper(obj)
        with self.assertRaises(AttributeError):
            _ = wrapper.nonexistent

    def test_error_on_getting_nonexistent_attribute(self) -> None:
        obj: WithProperties = WithProperties(100)
        wrapper: LocalWrapper = LocalWrapper(obj)
        with self.assertRaises(AttributeError):
            wrapper.nonexistent


class TestLocalWrapperCallables(unittest.TestCase):
    def setUp(self) -> None:
        def sample_function(x: int, y: int) -> int:
            return x + y

        self.func = sample_function
        self.wrapper: LocalWrapper = LocalWrapper(sample_function)

    def test_callable_invocation(self) -> None:
        result: object = self.wrapper(10, 20)
        expected: int = self.func(10, 20)
        self.assertEqual(result, expected)

    def test_error_on_non_callable(self) -> None:
        non_callable: int = 123
        non_callable_wrapper: LocalWrapper = LocalWrapper(non_callable)
        with self.assertRaises(TypeError):
            non_callable_wrapper()


class TestLocalWrapperCallableExceptions(unittest.TestCase):
    def setUp(self) -> None:
        def sample_function(x: int, y: int) -> None:
            raise ValueError("Intentional error for testing.")

        self.func = sample_function
        self.wrapper: LocalWrapper = LocalWrapper(sample_function)

    def test_callable_exception_propagation(self) -> None:
        with self.assertRaises(ValueError) as context:
            self.wrapper(10, 20)
        self.assertEqual(str(context.exception), "Intentional error for testing.")

    def test_exception_stack_trace(self) -> None:
        try:
            self.wrapper(10, 20)
        except ValueError:
            stack_trace: str = traceback.format_exc()
            self.assertIn("sample_function", stack_trace)
            self.assertIn("test_exception_stack_trace", stack_trace)


class TestLocalWrapperWithCoroutine(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        # Define a simple coroutine
        async def sample_coroutine(x: int, y: int) -> int:
            await asyncio.sleep(0.1)  # Simulate async operation
            return x + y

        self.coro = sample_coroutine
        self.wrapper: LocalWrapper = LocalWrapper(sample_coroutine)

    async def test_coroutine_invocation(self) -> None:
        # Test if the wrapped coroutine can be awaited and returns the correct result
        result: object = await self.wrapper(10, 20)
        expected: int = await self.coro(10, 20)
        self.assertEqual(result, expected)

    async def test_coroutine_exception_propagation(self) -> None:
        # Define a coroutine that raises an exception
        async def error_coroutine() -> None:
            await asyncio.sleep(0.1)
            raise ValueError("Intentional error for testing.")

        error_wrapper: LocalWrapper = LocalWrapper(error_coroutine)

        # Test if the exception raised by the wrapped coroutine is propagated
        with self.assertRaises(ValueError) as context:
            await error_wrapper()
        self.assertEqual(str(context.exception), "Intentional error for testing.")


class ContextBase:
    def __init__(self) -> None:
        self.enter_called: bool = False
        self.exit_called: bool = False


class MissingExitContextManager(ContextBase):
    def __enter__(self) -> str:
        self.enter_called = True
        return "enter_value"


class MissingEnterContextManager(ContextBase):
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> bool:
        self.exit_called = True
        return False  # Do not suppress exceptions


class SimpleContextManager(MissingEnterContextManager, MissingExitContextManager):
    pass


class RaisingContextManager:
    def __init__(self, raise_exit: bool = False, raise_enter: bool = False) -> None:
        self.raise_exit: bool = raise_exit
        self.raise_enter: bool = raise_enter
        self.enter_called: bool = False
        self.exit_called: bool = False

    def __enter__(self) -> str:
        self.enter_called = True
        if self.raise_enter:
            raise ValueError("Enter")
        return "enter_value"

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> bool:
        self.exit_called = True
        if self.raise_exit:
            raise ValueError("Exit")
        return False  # Do not suppress exceptions


class TestLocalWrapperContext(unittest.TestCase):
    def test_context_manager(self) -> None:
        simple_cm: SimpleContextManager = SimpleContextManager()
        local_wrapper: LocalWrapper = LocalWrapper(simple_cm)
        with local_wrapper as value:
            self.assertEqual(value, "enter_value")
            self.assertTrue(simple_cm.enter_called)
        self.assertTrue(simple_cm.exit_called)

    def test_missing_exit(self) -> None:
        ctx_mgr: MissingExitContextManager = MissingExitContextManager()
        local_wrapper: LocalWrapper = LocalWrapper(ctx_mgr)

        def checker() -> None:
            with local_wrapper as value:
                self.assertEqual(value, "enter_value")

        with self.assertRaisesRegex(AttributeError, "__exit__"):
            checker()
        self.assertTrue(ctx_mgr.enter_called)

    def test_missing_enter(self) -> None:
        ctx_mgr: MissingEnterContextManager = MissingEnterContextManager()
        local_wrapper: LocalWrapper = LocalWrapper(ctx_mgr)

        def checker() -> None:
            with local_wrapper as value:
                pass

        with self.assertRaisesRegex(AttributeError, "__enter__"):
            checker()
        self.assertFalse(ctx_mgr.exit_called)

    def test_enter_raising(self) -> None:
        ctx_mgr: RaisingContextManager = RaisingContextManager(raise_enter=True)
        local_wrapper: LocalWrapper = LocalWrapper(ctx_mgr)

        def checker() -> None:
            with local_wrapper as value:
                pass

        with self.assertRaisesRegex(ValueError, "Enter"):
            checker()
        self.assertTrue(ctx_mgr.enter_called)
        self.assertFalse(ctx_mgr.exit_called)

    def test_exit_raising(self) -> None:
        ctx_mgr: RaisingContextManager = RaisingContextManager(raise_exit=True)
        local_wrapper: LocalWrapper = LocalWrapper(ctx_mgr)

        def checker() -> None:
            with local_wrapper as value:
                pass

        with self.assertRaisesRegex(ValueError, "Exit"):
            checker()
        self.assertTrue(ctx_mgr.enter_called)
        self.assertTrue(ctx_mgr.exit_called)

    def test_raise_body(self) -> None:
        ctx_mgr: SimpleContextManager = SimpleContextManager()
        local_wrapper: LocalWrapper = LocalWrapper(ctx_mgr)

        def checker() -> None:
            with local_wrapper as value:
                raise ValueError("Body")

        with self.assertRaisesRegex(ValueError, "Body"):
            checker()
        self.assertTrue(ctx_mgr.enter_called)
        self.assertTrue(ctx_mgr.exit_called)


if __name__ == "__main__":
    unittest.main()
