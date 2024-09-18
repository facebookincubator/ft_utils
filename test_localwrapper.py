# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-unsafe

import asyncio
import gc
import traceback
import unittest

from contextlib import ContextDecorator

from ft_utils.local import LocalWrapper


class TestLocalWrapperSmokes(unittest.TestCase):
    def setUp(self):
        self.obj = [1, 2, 3]
        self.wrapper = LocalWrapper(self.obj)

    def test_constructor(self):
        self.assertIsNotNone(self.wrapper)
        self.assertEqual(self.wrapper.wrapped, self.obj)

    def test_getattr(self):
        self.assertEqual(self.wrapper.append, self.obj.append)

    def test_setattr(self):
        class Thing:
            pass

        wrapper = LocalWrapper(Thing())
        new_attr = 123
        wrapper.new_attr = new_attr
        self.assertEqual(wrapper.new_attr, new_attr)

    def test_getitem(self):
        self.assertEqual(self.wrapper[1], self.obj[1])

    def test_setitem(self):
        self.wrapper[1] = 100
        self.assertEqual(self.wrapper[1], 100)

    def test_delitem(self):
        del self.wrapper[1]
        self.assertEqual(len(self.wrapper), 2)

    def test_len(self):
        self.assertEqual(len(self.wrapper), len(self.obj))

    def test_iter(self):
        self.assertListEqual(list(iter(self.wrapper)), self.obj)

    def test_call(self):
        self.wrapper.append(4)
        self.assertIn(4, self.wrapper)

    def test_str(self):
        self.assertEqual(str(self.wrapper), str(self.obj))

    def test_richcompare(self):
        another_wrapper = LocalWrapper([1, 2, 3])
        self.assertEqual(self.wrapper, another_wrapper)

    def test_number_operations(self):
        # Test a few number operations
        self.assertEqual(self.wrapper + [4, 5], self.obj + [4, 5])
        self.assertEqual(self.wrapper * 2, self.obj * 2)

    def test_inplace_operations(self):
        self.wrapper += [4, 5]
        self.obj += [4, 5]
        self.assertEqual(self.wrapper, self.obj)
        self.wrapper *= 3
        self.obj *= 3
        self.assertEqual(self.wrapper, self.obj)

    def test_inplace_operations_recursive(self):
        id_checker = self.wrapper.wrapped
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

    def test_bool(self):
        self.assertTrue(bool(self.wrapper))

    def test_int_float(self):
        num_wrapper = LocalWrapper(10)
        self.assertEqual(int(num_wrapper), 10)
        self.assertEqual(float(num_wrapper), 10.0)

    def test_gc(self):
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

    def test_repr(self):
        obj_repr = repr(self.obj)
        wrapper_repr = repr(self.wrapper)
        expected_repr = f"<LocalWrapper: {obj_repr}>"
        self.assertEqual(wrapper_repr, expected_repr)

    def test_dict(self):
        ld = LocalWrapper({})
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

    def test_slice(self):
        tp = 1, 2, 3, 4, 5, 6
        w = LocalWrapper(tp)
        self.assertIs(w[:], tp)
        self.assertEqual(w[:2], tp[:2])
        self.assertEqual(w[2:], tp[2:])
        self.assertEqual(w[1:4], tp[1:4])
        self.assertEqual(w[-2:-1], tp[-2:-1])


class TestLocalWrapperBytearray(unittest.TestCase):
    def setUp(self):
        self.wrapper = LocalWrapper(bytearray([1, 2]))

    def test_bytearray_addition(self):
        self.assertEqual(self.wrapper + self.wrapper, bytearray([1, 2, 1, 2]))
        self.assertEqual(self.wrapper + self.wrapper.wrapped, bytearray([1, 2, 1, 2]))
        self.assertEqual(self.wrapper.wrapped + self.wrapper, bytearray([1, 2, 1, 2]))

    def test_bytearray_multiplication(self):
        self.assertEqual(self.wrapper * 2, bytearray([1, 2, 1, 2]))

    def test_bytearray_eq(self):
        self.assertTrue(self.wrapper == self.wrapper.wrapped)
        self.assertTrue(self.wrapper.wrapped == self.wrapper)


class TestLocalWrapperIterExtra(unittest.TestCase):
    def setUp(self):
        self.obj = (1, 2, 3)
        self.wrapper = LocalWrapper(self.obj)

    def test_empty_iter(self):
        empty_wrapper = LocalWrapper([])
        self.assertListEqual(list(iter(empty_wrapper)), [])

    def test_exception_in_iteration(self):
        class CustomIterable:
            def __iter__(self):
                return self

            def __next__(self):
                raise RuntimeError("Test Exception")

        error_wrapper = LocalWrapper(CustomIterable())
        with self.assertRaises(RuntimeError):
            list(iter(error_wrapper))

    def test_multiple_iterations(self):
        iter1 = tuple(iter(self.wrapper))
        iter2 = tuple(iter(self.wrapper))
        self.assertEqual(iter1, self.obj)
        self.assertEqual(iter2, self.obj)


class TestLocalWrapperHash(unittest.TestCase):
    def setUp(self):
        self.obj = "Hello World"
        self.wrapper = LocalWrapper(self.obj)

    def test_hash(self):
        obj_hash = hash(self.obj)
        wrapper_hash = hash(self.wrapper)
        self.assertEqual(wrapper_hash, obj_hash)

    def test_hash_consistency(self):
        wrapper_hash1 = hash(self.wrapper)
        wrapper_hash2 = hash(self.wrapper)
        self.assertEqual(wrapper_hash1, wrapper_hash2)

    def test_hash_equality(self):
        another_wrapper = LocalWrapper(self.obj)
        self.assertEqual(hash(self.wrapper), hash(another_wrapper))
        another_wrapper = LocalWrapper(self.wrapper)
        self.assertEqual(hash(self.wrapper), hash(another_wrapper))


class TestLocalWrapperBuffer(unittest.TestCase):
    def setUp(self):
        self.byte_array = bytearray(b"example data")
        self.wrapper = LocalWrapper(self.byte_array)

    def test_getbuffer(self):
        buf = memoryview(self.wrapper)
        self.assertEqual(buf.tobytes(), self.byte_array)

    def test_releasebuffer(self):
        buf = memoryview(self.wrapper)
        del buf
        # If no exceptions, assume success
        self.assertTrue(True)

    def test_buffer_integrity(self):
        with memoryview(self.wrapper) as buf:
            buf[0] = ord("z")
        self.assertEqual(self.byte_array[0], ord("z"))

    def test_buffer_type(self):
        buf = memoryview(self.wrapper)
        self.assertIsInstance(buf, memoryview)


class NumberAPI:
    def __init__(self, value):
        self.value = value

    def __add__(self, other):
        return self.value + other

    def __sub__(self, other):
        return self.value - other

    def __mul__(self, other):
        return self.value * other

    def __truediv__(self, other):
        return self.value / other

    def __floordiv__(self, other):
        return self.value // other

    def __mod__(self, other):
        return self.value % other

    def __pow__(self, other, modulus=None):
        return self.value**other

    def __lshift__(self, other):
        return self.value << other

    def __rshift__(self, other):
        return self.value >> other

    def __and__(self, other):
        return self.value & other

    def __or__(self, other):
        return self.value | other

    def __xor__(self, other):
        return self.value ^ other

    def __iadd__(self, other):
        self.value += other
        return self

    def __isub__(self, other):
        self.value -= other
        return self

    def __imul__(self, other):
        self.value *= other
        return self

    def __itruediv__(self, other):
        self.value /= other
        return self

    def __ifloordiv__(self, other):
        self.value //= other
        return self

    def __imod__(self, other):
        self.value %= other
        return self

    def __ipow__(self, other):
        self.value **= other
        return self

    def __ilshift__(self, other):
        self.value <<= other
        return self

    def __irshift__(self, other):
        self.value >>= other
        return self

    def __iand__(self, other):
        self.value &= other
        return self

    def __ior__(self, other):
        self.value |= other
        return self

    def __ixor__(self, other):
        self.value ^= other
        return self

    def __invert__(self):
        return ~(self.value)

    def __divmod__(self, other):
        return divmod(self.value, other)

    def __pos__(self):
        return +(self.value)

    def __neg__(self):
        return -(self.value)

    def __eq__(self, other):
        if self is other:
            return True
        return self.value == other

    def __int__(self):
        return int(self.value)

    def __float__(self):
        return float(self.value)


class TestLocalWrapperInt(unittest.TestCase):
    def setUp(self):
        self.num = 10
        self.wrapper = LocalWrapper(self.num)

    def test_add(self):
        result = self.wrapper + 5
        self.assertEqual(result, 15)

    def test_subtract(self):
        result = self.wrapper - 5
        self.assertEqual(result, 5)

    def test_multiply(self):
        result = self.wrapper * 5
        self.assertEqual(result, 50)

    def test_divide(self):
        result = self.wrapper / 2
        self.assertEqual(result, 5)

    def test_floor_divide(self):
        result = self.wrapper // 3
        self.assertEqual(result, 3)

    def test_modulus(self):
        result = self.wrapper % 3
        self.assertEqual(result, 1)

    def test_power(self):
        result = self.wrapper**2
        self.assertEqual(result, 100)

    def test_negative(self):
        result = -self.wrapper
        self.assertEqual(result, -10)

    def test_positive(self):
        result = +self.wrapper
        self.assertEqual(result, 10)

    def test_absolute(self):
        negative_wrapper = LocalWrapper(-10)
        result = abs(negative_wrapper)
        self.assertEqual(result, 10)

    def test_inplace_add(self):
        self.wrapper += 5
        self.assertEqual(self.wrapper, 15)

    def test_inplace_subtract(self):
        self.wrapper -= 5
        self.assertEqual(self.wrapper, 5)

    def test_inplace_multiply(self):
        self.wrapper *= 5
        self.assertEqual(self.wrapper, 50)

    def test_inplace_divide(self):
        self.wrapper /= 2
        self.assertEqual(self.wrapper, 5)

    def test_inplace_floor_divide(self):
        self.wrapper //= 3
        self.assertEqual(self.wrapper, 3)

    def test_inplace_modulus(self):
        self.wrapper %= 3
        self.assertEqual(self.wrapper, 1)

    def test_inplace_power(self):
        self.wrapper **= 2
        self.assertEqual(self.wrapper, 100)

    def test_bool(self):
        self.assertTrue(bool(self.wrapper))
        zero_wrapper = LocalWrapper(0)
        self.assertFalse(bool(zero_wrapper))

    def test_int(self):
        self.assertEqual(int(self.wrapper), 10)

    def test_float(self):
        self.assertEqual(float(self.wrapper), 10.0)

    def test_divmod(self):
        self.assertEqual(divmod(self.wrapper, 3), (3, 1))

    def test_invertd(self):
        self.assertEqual(~self.wrapper, -11)


class TestLocalWrapperNotImpl(unittest.TestCase):
    def setUp(self):
        self.not_num = object()
        self.wrapper = LocalWrapper(self.not_num)

    def test_add(self):
        with self.assertRaises(TypeError):
            self.wrapper + 5

    def test_subtract(self):
        with self.assertRaises(TypeError):
            self.wrapper - 5

    def test_multiply(self):
        with self.assertRaises(TypeError):
            self.wrapper * 5

    def test_divide(self):
        with self.assertRaises(TypeError):
            self.wrapper / 2

    def test_floor_divide(self):
        with self.assertRaises(TypeError):
            self.wrapper // 3

    def test_modulus(self):
        with self.assertRaises(TypeError):
            self.wrapper % 3

    def test_power(self):
        with self.assertRaises(TypeError):
            self.wrapper**2

    def test_negative(self):
        with self.assertRaises(TypeError):
            -self.wrapper

    def test_positive(self):
        with self.assertRaises(TypeError):
            +self.wrapper

    def test_absolute(self):
        with self.assertRaises(TypeError):
            abs(self.wrapper)

    def test_inplace_add(self):
        with self.assertRaises(TypeError):
            self.wrapper += 5

    def test_inplace_subtract(self):
        with self.assertRaises(TypeError):
            self.wrapper -= 5

    def test_inplace_multiply(self):
        with self.assertRaises(TypeError):
            self.wrapper *= 5

    def test_inplace_divide(self):
        with self.assertRaises(TypeError):
            self.wrapper /= 2

    def test_inplace_floor_divide(self):
        with self.assertRaises(TypeError):
            self.wrapper //= 3

    def test_inplace_modulus(self):
        with self.assertRaises(TypeError):
            self.wrapper %= 3

    def test_inplace_power(self):
        with self.assertRaises(TypeError):
            self.wrapper **= 2

    def test_bool(self):
        class Thing:
            def __bool__(self):
                raise TypeError("Just to check")

        wrapper = LocalWrapper(Thing())
        with self.assertRaises(TypeError):
            bool(wrapper)

    def test_int(self):
        with self.assertRaises(TypeError):
            int(self.wrapper)

    def test_float(self):
        with self.assertRaises(TypeError):
            float(self.wrapper)

    def test_divmod(self):
        with self.assertRaises(TypeError):
            divmod(self.wrapper, 3)

    def test_invertd(self):
        with self.assertRaises(TypeError):
            ~self.wrapper


class AttrDel(ContextDecorator):
    def __init__(self, obj, attr):
        self.obj = obj
        self.attr = attr
        self.has_attr = hasattr(obj, attr)
        if self.has_attr:
            self.value = getattr(obj, attr)

    def __enter__(self):
        if self.has_attr:
            delattr(self.obj, self.attr)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.has_attr:
            setattr(self.obj, self.attr, self.value)


class TestLocalWrapperNumberAPI(TestLocalWrapperInt):
    def setUp(self):
        self.num = NumberAPI(10)
        self.wrapper = LocalWrapper(self.num)


class ASequence:
    def __init__(self):
        self._items = []

    def __getitem__(self, index):
        return self._items[index]

    def __setitem__(self, index, value):
        self._items[index] = value

    def __delitem__(self, index):
        del self._items[index]

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __iadd__(self, other):
        if other is self:
            self._items += self._items
        else:
            self._items += other
        return self

    def append(self, item):
        self._items.append(item)

    def __repr__(self):
        return f"ASequence({self._items})"


class TestMutations(unittest.TestCase):
    def testRemoveAdd(self):
        num = NumberAPI(10)
        wrapper = LocalWrapper(num)
        with AttrDel(NumberAPI, "__add__"):
            with self.assertRaisesRegex(
                TypeError, "unsupported operand type.*NumberAPI.*int"
            ):
                res = wrapper + 1
        res = wrapper + 1
        self.assertEqual(res, 11)

    def testAddAdd(self):
        with AttrDel(NumberAPI, "__add__"):
            num = NumberAPI(10)
            wrapper = LocalWrapper(num)
            with self.assertRaisesRegex(
                TypeError, "unsupported operand type.*NumberAPI.*int"
            ):
                res = wrapper + 1
        res = wrapper + 1
        self.assertEqual(res, 11)

    def testChangeWrapped(self):
        wrapper = LocalWrapper(23)
        with self.assertRaises(AttributeError):
            wrapper.wrapped = 24

    def testChangeType(self):
        class Mutato(ASequence):
            def __init__(self, seq):
                super().__init__()
                self._items = seq

        mut = Mutato([1, 2, 3, 4])
        wrapper = LocalWrapper(mut)
        wrapper += wrapper
        mut.__class__ = NumberAPI
        mut.__init__(0)
        wrapper += 23
        self.assertEqual(wrapper / 1, 23)


class Matrix:
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.data = [[0 for _ in range(cols)] for _ in range(rows)]

    def __getitem__(self, index):
        return self.data[index]

    def __setitem__(self, index, value):
        self.data[index] = value

    def __matmul__(self, other):
        if self.cols != other.rows:
            raise ValueError("Matrices cannot be multiplied")
        result = Matrix(self.rows, other.cols)
        for i in range(self.rows):
            for j in range(other.cols):
                for k in range(self.cols):
                    result[i][j] += self[i][k] * other[k][j]
        return result

    def __imatmul__(self, other):
        if self.cols != other.rows:
            raise ValueError("Matrices cannot be multiplied")
        result = Matrix(self.rows, other.cols)
        for i in range(self.rows):
            for j in range(other.cols):
                for k in range(self.cols):
                    result[i][j] += self[i][k] * other[k][j]
        self.data = result.data
        return self

    def __repr__(self):
        return str(self.data)


class TestLocalWrapperMatrix(unittest.TestCase):
    def setUp(self):
        m1 = Matrix(2, 2)
        m1[0][0] = 1
        m1[0][1] = 2
        m1[1][0] = 3
        m1[1][1] = 4
        m2 = Matrix(2, 2)
        m2[0][0] = 5
        m2[0][1] = 6
        m2[1][0] = 7
        m2[1][1] = 8
        self.m1 = m1
        self.m2 = m2
        self.wrapped1 = LocalWrapper(m1)
        self.wrapped2 = LocalWrapper(m2)

    def test_matrix_multiply(self):
        result = self.m1 @ self.m2
        self.assertEqual(result.data, [[19, 22], [43, 50]])
        result = self.wrapped1 @ self.wrapped2
        self.assertEqual(result.data, [[19, 22], [43, 50]])
        result = self.wrapped1 @ self.m2
        self.assertEqual(result.data, [[19, 22], [43, 50]])
        result = self.m1 @ self.wrapped2
        self.assertEqual(result.data, [[19, 22], [43, 50]])

    def test_inplacematrix_multiply(self):
        self.wrapped1 @= self.wrapped2
        self.assertEqual(self.m1.data, [[19, 22], [43, 50]])


class TestLocalWrapperSequenceAPI(unittest.TestCase):
    def setUp(self):
        self.seq = [1, 2, 3, 4, 5]
        self.wrapper = LocalWrapper(self.seq)

    def test_getitem(self):
        self.assertEqual(self.wrapper[2], 3)

    def test_setitem(self):
        self.wrapper[2] = 99
        self.assertEqual(self.wrapper[2], 99)

    def test_delitem(self):
        del self.wrapper[2]
        self.assertNotIn(3, self.wrapper)

    def test_len(self):
        self.assertEqual(len(self.wrapper), 5)

    def test_concat(self):
        result = self.wrapper + [6, 7]
        self.assertEqual(result, [1, 2, 3, 4, 5, 6, 7])

    def test_repeat(self):
        result = self.wrapper * 2
        self.assertEqual(result, [1, 2, 3, 4, 5, 1, 2, 3, 4, 5])

    def test_contains(self):
        self.assertTrue(3 in self.wrapper)
        self.assertFalse(6 in self.wrapper)

    def test_iter(self):
        items = [item for item in self.wrapper]
        self.assertEqual(items, [1, 2, 3, 4, 5])
        it = iter(self.wrapper)
        self.assertEqual(next(it), 1)
        self.assertEqual(next(it), 2)
        self.assertEqual(next(it), 3)
        self.assertEqual(next(it), 4)
        self.assertEqual(next(it), 5)
        with self.assertRaises(StopIteration):
            next(it)

    def test_slice_get(self):
        self.assertEqual(self.wrapper[1:3], [2, 3])

    def test_slice_set(self):
        self.wrapper[1:3] = [8, 9]
        self.assertEqual(self.wrapper[1], 8)
        self.assertEqual(self.wrapper[2], 9)

    def test_slice_del(self):
        del self.wrapper[1:3]
        self.assertEqual(list(self.wrapper), [1, 4, 5])

    def test_error_on_non_sequence(self):
        with self.assertRaises(TypeError):
            non_seq_wrapper = LocalWrapper(10)
            non_seq_wrapper[0]

    def test_error_on_out_of_bounds(self):
        with self.assertRaises(IndexError):
            _ = self.wrapper[10]

    def test_error_on_wrong_type_index(self):
        with self.assertRaises(TypeError):
            _ = self.wrapper["a"]


class WithSlots:
    __slots__ = ["a", "b"]

    def __init__(self, a, b):
        self.a = a
        self.b = b


class WithProperties:
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value


class TestLocalWrapperAttributes(unittest.TestCase):
    def test_slots_get_set(self):
        obj = WithSlots(1, 2)
        wrapper = LocalWrapper(obj)
        # Test getting attributes
        self.assertEqual(wrapper.a, 1)
        self.assertEqual(wrapper.b, 2)
        # Test setting attributes
        wrapper.a = 10
        wrapper.b = 20
        self.assertEqual(wrapper.a, 10)
        self.assertEqual(wrapper.b, 20)

    def test_properties_get_set(self):
        obj = WithProperties(100)
        wrapper = LocalWrapper(obj)
        # Test getting property
        self.assertEqual(wrapper.value, 100)
        # Test setting property
        wrapper.value = 200
        self.assertEqual(wrapper.value, 200)

    def test_error_on_nonexistent_attribute(self):
        obj = WithSlots(1, 2)
        wrapper = LocalWrapper(obj)
        with self.assertRaises(AttributeError):
            _ = wrapper.nonexistent

    def test_error_on_getting_nonexistent_attribute(self):
        obj = WithProperties(100)
        wrapper = LocalWrapper(obj)
        with self.assertRaises(AttributeError):
            wrapper.nonexistent


class TestLocalWrapperCallables(unittest.TestCase):
    def setUp(self):
        def sample_function(x, y):
            return x + y

        self.func = sample_function
        self.wrapper = LocalWrapper(sample_function)

    def test_callable_invocation(self):
        result = self.wrapper(10, 20)
        expected = self.func(10, 20)
        self.assertEqual(result, expected)

    def test_error_on_non_callable(self):
        non_callable = 123
        non_callable_wrapper = LocalWrapper(non_callable)
        with self.assertRaises(TypeError):
            non_callable_wrapper()


class TestLocalWrapperCallableExceptions(unittest.TestCase):
    def setUp(self):
        def sample_function(x, y):
            raise ValueError("Intentional error for testing.")

        self.func = sample_function
        self.wrapper = LocalWrapper(sample_function)

    def test_callable_exception_propagation(self):
        with self.assertRaises(ValueError) as context:
            self.wrapper(10, 20)
        self.assertEqual(str(context.exception), "Intentional error for testing.")

    def test_exception_stack_trace(self):
        try:
            self.wrapper(10, 20)
        except ValueError as e:
            stack_trace = traceback.format_exc()
            self.assertIn("sample_function", stack_trace)
            self.assertIn("test_exception_stack_trace", stack_trace)


class TestLocalWrapperWithCoroutine(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Define a simple coroutine
        async def sample_coroutine(x, y):
            await asyncio.sleep(0.1)  # Simulate async operation
            return x + y

        self.coro = sample_coroutine
        self.wrapper = LocalWrapper(sample_coroutine)

    async def test_coroutine_invocation(self):
        # Test if the wrapped coroutine can be awaited and returns the correct result
        result = await self.wrapper(10, 20)
        expected = await self.coro(10, 20)
        self.assertEqual(result, expected)

    async def test_coroutine_exception_propagation(self):
        # Define a coroutine that raises an exception
        async def error_coroutine():
            await asyncio.sleep(0.1)
            raise ValueError("Intentional error for testing.")

        error_wrapper = LocalWrapper(error_coroutine)

        # Test if the exception raised by the wrapped coroutine is propagated
        with self.assertRaises(ValueError) as context:
            await error_wrapper()
        self.assertEqual(str(context.exception), "Intentional error for testing.")


class ContextBase:
    def __init__(self):
        self.enter_called = False
        self.exit_called = False


class MissingExitContextManager(ContextBase):
    def __enter__(self):
        self.enter_called = True
        return "enter_value"


class MissingEnterContextManager(ContextBase):
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit_called = True
        return False  # Do not suppress exceptions


class SimpleContextManager(MissingEnterContextManager, MissingExitContextManager):
    pass


class RaisingContextManager:
    def __init__(self, raise_exit=False, raise_enter=False):
        self.raise_exit = raise_exit
        self.raise_enter = raise_enter
        self.enter_called = False
        self.exit_called = False

    def __enter__(self):
        self.enter_called = True
        if self.raise_enter:
            raise ValueError("Enter")
        return "enter_value"

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit_called = True
        if self.raise_exit:
            raise ValueError("Exit")
        return False  # Do not suppress exceptions


class TestLocalWrapperContext(unittest.TestCase):
    def test_context_manager(self):
        simple_cm = SimpleContextManager()
        local_wrapper = LocalWrapper(simple_cm)
        with local_wrapper as value:
            self.assertEqual(value, "enter_value")
            self.assertTrue(simple_cm.enter_called)
        self.assertTrue(simple_cm.exit_called)

    def test_missing_exit(self):
        ctx_mgr = MissingExitContextManager()
        local_wrapper = LocalWrapper(ctx_mgr)

        def checker():
            with local_wrapper as value:
                self.assertEqual(value, "enter_value")

        with self.assertRaisesRegex(AttributeError, "__exit__"):
            checker()
        self.assertTrue(ctx_mgr.enter_called)

    def test_missing_enter(self):
        ctx_mgr = MissingEnterContextManager()
        local_wrapper = LocalWrapper(ctx_mgr)

        def checker():
            with local_wrapper as value:
                pass

        with self.assertRaisesRegex(AttributeError, "__enter__"):
            checker()
        self.assertFalse(ctx_mgr.exit_called)

    def test_enter_raising(self):
        ctx_mgr = RaisingContextManager(raise_enter=True)
        local_wrapper = LocalWrapper(ctx_mgr)

        def checker():
            with local_wrapper as value:
                pass

        with self.assertRaisesRegex(ValueError, "Enter"):
            checker()
        self.assertTrue(ctx_mgr.enter_called)
        self.assertFalse(ctx_mgr.exit_called)

    def test_exit_raising(self):
        ctx_mgr = RaisingContextManager(raise_exit=True)
        local_wrapper = LocalWrapper(ctx_mgr)

        def checker():
            with local_wrapper as value:
                pass

        with self.assertRaisesRegex(ValueError, "Exit"):
            checker()
        self.assertTrue(ctx_mgr.enter_called)
        self.assertTrue(ctx_mgr.exit_called)

    def test_raise_body(self):
        ctx_mgr = SimpleContextManager()
        local_wrapper = LocalWrapper(ctx_mgr)

        def checker():
            with local_wrapper as value:
                raise ValueError("Body")

        with self.assertRaisesRegex(ValueError, "Body"):
            checker()
        self.assertTrue(ctx_mgr.enter_called)
        self.assertTrue(ctx_mgr.exit_called)
