# Copyright (c) Meta Platforms, Inc. and affiliates.

# pyre-unsafe

import os
import subprocess
import sys


def run_test(filename):
    print(f"Running {filename}...")
    f_head, f_tail = os.path.splitext(filename)
    if f_tail != ".py":
        raise ValueError(f"filename `{filename}` is not a Python (.py) file")
    module = f"ft_utils.tests.{f_head}"
    result = subprocess.run(
        [sys.executable, "-m", module], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if result.returncode != 0:
        print(f"{module} failed:")
        print(result.stdout.decode())
        print(result.stderr.decode())
        return False
    print(f"{module} passed:")
    print(result.stdout.decode())
    print(result.stderr.decode())
    return True


def invoke_main():
    test_dir = os.path.dirname(__file__)
    test_files = [
        f
        for f in os.listdir(test_dir)
        if f.startswith("test_") or f.endswith("_bench.py")
    ]
    all_passed = True
    for test_file in test_files:
        if "array" in test_file:
            continue  # These crash for now.
        if "test_run_all" in test_file:
            continue  # Recursion.
        if not run_test(test_file):
            all_passed = False
    if all_passed:
        print("TEST OK")
    else:
        print("TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    invoke_main()
