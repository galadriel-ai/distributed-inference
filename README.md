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

**Setup shared network**
```
docker network create shared_network
# Update database/.env

# Update .env
# Make sure to add the correct DB_HOST to .env
DB_HOST="db"
```

**Run DB**
```
cd database
docker compose -f docker-compose-prod.yml up --build -d
```

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
