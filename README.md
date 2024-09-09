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

### Linting

```shell
pip install black
python -m black .
```

## Production deployment

**Run App**
```
./deploy.sh
```

**To run DB migrations**

```
source venv/bin/activate
cd database
alembic upgrade head
```
