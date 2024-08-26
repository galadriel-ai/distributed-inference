# Distributed inference

### Setup

Requirements to run:

- python 3.12

```
pip install -r requirements.txt
```

### Run

```
python wsgi.py
```

### Unit testing

```shell
python -m pytest tests/unit
# Or
PYTHONPATH=. pytest tests/unit
```