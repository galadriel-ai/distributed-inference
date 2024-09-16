# Distributed inference

### Setup

Requirements to run:

- python 3.12

```
pip install -r requirements.txt
```

### Setup database

Check README in database/README.md

### Run

```
python wsgi.py
```

### Insert some data to DB

Modify the data to insert however you wish
```
PYTHONPATH=. python scripts/insert_users.py
```

Modify the user_id with the result from the previous script
```
PYTHONPATH=. python scripts/insert_node.py
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
