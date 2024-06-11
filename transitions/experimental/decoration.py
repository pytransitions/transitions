from typing import Callable, ParamSpec

P = ParamSpec("P")


def expect_override(func: Callable[P, bool | None]) -> Callable[P, bool | None]:
    setattr(func, "expect_override", True)
    return func
