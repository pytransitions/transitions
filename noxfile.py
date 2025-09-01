import nox


python = ["3.8", "3.9", "3.10", "3.11", "3.12"]
nox.options.stop_on_first_error = True


@nox.session(python=python[-1])
def test_check_manifest(session):
    session.install("check-manifest")
    session.run("check-manifest")


@nox.session(python=python[-1])
def test_mypy(session):
    session.install(".")
    session.install("-rrequirements_test.txt")
    session.install("-rrequirements_diagrams.txt")
    session.install("-rrequirements_mypy.txt")
    session.run("pytest", "-nauto", "--doctest-modules", "tests/")


@nox.session(python=python)
def test(session):
    session.install(".")
    session.install("-rrequirements_test.txt")
    session.install("-rrequirements_diagrams.txt")
    session.run("pytest", "-nauto", "tests/")


@nox.session(python=python[-1])
def test_no_gv(session):
    session.install(".")
    session.install("-rrequirements_test.txt")
    session.run("pytest", "-nauto", "tests/")
