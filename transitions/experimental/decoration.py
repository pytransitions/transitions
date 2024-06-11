def expect_override(func):
    setattr(func, "expect_override", True)
    return func
