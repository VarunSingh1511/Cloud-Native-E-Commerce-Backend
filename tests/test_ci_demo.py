"""TEMPORARY: a deliberately failing test, to show that CI stops a broken change."""


def test_ci_catches_a_failing_test() -> None:
    assert 1 + 1 == 3
