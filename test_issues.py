# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-unsafe

import threading
import unittest

from ft_utils.concurrency import ConcurrentDict


class TestFoundIssues(unittest.TestCase):
    def test_13_dict_race(self):
        d = ConcurrentDict()
        data = {k: 0 for k in range(10)}
        for k, v in data.items():
            d[k] = v
        self.assertEqual(len(d.as_dict()), 10)

        def incr():
            keys = list(range(10))
            for _ in range(500_000):
                d[keys[_ % len(keys)]] += 1

        threads = [threading.Thread(target=incr) for _ in range(3)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(d.as_dict()), 10)


if __name__ == "__main__":
    unittest.main()
