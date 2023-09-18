import nox

python = ["3.7", "3.8", "3.9", "3.10", "3.11"]
# nox.options.stop_on_first_error = True

@nox.session(
    python=python[-1]
)
def test_check_manifest(session):
    session.install("check-manifest")
    session.run("check-manifest")

@nox.session(
    python=python[-1]
)
def test_mypy(session):
    session.install(".")
    session.install("-rrequirements_mypy.txt")
    session.install("-rrequirements_diagrams.txt")
    session.run("mypy", "transitions")

@nox.session(
    python=python
)
def test(session):
    session.install(".")
    session.install("-rrequirements_test.txt")
    session.install("-rrequirements_diagrams.txt")
    session.run("pytest", "-nauto", "tests/")

@nox.session(
    python=python[-1]
)
def test_no_gv(session):
    session.install(".")
    session.install("pytest-cov", "pytest-xdist", "mock", "dill", "pycodestyle")
    session.run("pytest", "-nauto", "tests/")









