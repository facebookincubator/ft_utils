# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-unsafe

import sys
import unittest
from unittest.mock import MagicMock, patch

from .benchmark_utils import (
    benchmark_operation,
    BenchmarkProvider,
    execute_benchmarks,
    ft_randchoice,
    ft_randint,
    parse_arguments,
    worker,
)


class FakeBench(BenchmarkProvider):
    def benchmark_foo(self):
        self.__class__.ran = True


class TestBenchmarkUtils(unittest.TestCase):
    def test_ft_randint(self):
        results = {ft_randint(1, 10) for _ in range(100)}
        self.assertTrue(all(1 <= num <= 10 for num in results))
        self.assertTrue(len(results) > 1)

    def test_ft_randint_reversed(self):
        results = {ft_randint(10, 1) for _ in range(100)}
        self.assertTrue(all(1 <= num <= 10 for num in results))

    def test_ft_randchoice(self):
        seq = ["apple", "banana", "cherry"]
        results = {ft_randchoice(seq) for _ in range(100)}
        self.assertEqual(set(seq), results)

    def test_ft_randchoice_empty(self):
        with self.assertRaises(IndexError):
            ft_randchoice([])

    def test_benchmark_provider_init(self):
        provider = BenchmarkProvider(100)
        self.assertEqual(provider._operations, 100)

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_arguments(self, mock_parse_args):
        mock_parse_args.return_value = MagicMock(operations=1000, threads=16)
        args = parse_arguments("Test")
        self.assertEqual(args.operations, 1000)
        self.assertEqual(args.threads, 16)

    @patch("time.time", side_effect=[1, 2])
    def test_benchmark_operation(self, mock_time):
        barrier = MagicMock()
        barrier.wait = MagicMock()
        result = benchmark_operation(lambda: None)
        self.assertEqual(result, 1)

    @patch("ft_utils.benchmark_utils.benchmark_operation", return_value=1.0)
    def test_worker(self, mock_benchmark_operation):
        barrier = MagicMock()
        results = worker(lambda: None, barrier)
        self.assertEqual(results, [1.0] * 5)

    def test_discovery(self):
        test_args = ["test_benchmark_utils", "--threads", "1", "--operations", "1"]
        with patch.object(sys, "argv", test_args):
            FakeBench.ran = False
            execute_benchmarks(FakeBench)
            self.assertTrue(FakeBench.ran)


if __name__ == "__main__":
    unittest.main()
