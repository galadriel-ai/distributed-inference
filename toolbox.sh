function lint {
  pylint --rcfile=setup.cfg distributedinference/*
}

function format {
  black .
}

function unit-test {
  python -m pytest tests
}

function ci {
  format && lint && unit-test
}