import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import executor


def test_retry_placeholder_paths_are_rejected():
    assert executor.retry_command_has_placeholder("python3 -m py_compile /path/to/cli.py")
    assert executor.retry_command_has_placeholder("python3 <file>")
    assert executor.retry_command_has_placeholder("python3 your_file.py")


def test_normal_retry_command_is_allowed():
    assert not executor.retry_command_has_placeholder("python3 -m py_compile /home/chris/jarvis/cli.py")
    assert not executor.retry_command_has_placeholder("python3 -m py_compile cli.py")




def test_deterministic_retry_repairs_relative_core_py_compile():
    fixed = executor.deterministic_retry_command(
        "python3 -m py_compile cli.py",
        "[Errno 2] No such file or directory: 'cli.py'",
    )
    assert fixed == "python3 -m py_compile /home/chris/jarvis/cli.py"


def test_deterministic_retry_repairs_dot_relative_core_py_compile():
    fixed = executor.deterministic_retry_command(
        "python3 -m py_compile ./executor.py",
        "[Errno 2] No such file or directory: './executor.py'",
    )
    assert fixed == "python3 -m py_compile /home/chris/jarvis/executor.py"


def test_deterministic_retry_ignores_unrelated_errors():
    fixed = executor.deterministic_retry_command(
        "python3 -m py_compile cli.py",
        "SyntaxError: invalid syntax",
    )
    assert fixed == ""


def run_tests():
    test_items = [
        (name, fn)
        for name, fn in sorted(globals().items())
        if name.startswith("test_") and callable(fn)
    ]

    for name, fn in test_items:
        try:
            fn()
        except Exception:
            print(f"FAILED TEST: {name}")
            raise

    print(f"PASS: retry command placeholder guards ({len(test_items)} tests)")


if __name__ == "__main__":
    run_tests()
