function lint {
  pylint --rcfile=setup.cfg distributedinference/*
}

function format {
  black .
}

function type-check {
  mypy distributedinference
}

function unit-test {
  python -m pytest tests
}

function ci {
  format && lint && unit-test
}

function cov {
  python -m pytest tests/unit \
    --cov-report html:tests/reports/coverage/htmlcov \
    --cov-report xml:tests/reports/coverage/cobertura-coverage.xml \
    --cov-report term \
    --cov=distributedinference
}