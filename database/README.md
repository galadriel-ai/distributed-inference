# Distributed inference database

Manage databases schemas and migrations

## Setup

Install or update

```shell
conda env update -f environment.yml
```

Initialise environment

```shell
pip install -r requirements.txt
```

```shell
cp template.env .env
```

### Database

Postgres databases can be run in docker locally:

```shell
docker-compose up
```

Init databases locally:

```shell
alembic upgrade head
```

## Migrations

To upgrade database define new table or edit existing ones in *database.py*

Once changes are made run the command to create migration script:

```bash
alembic revision --autogenerate -m "<Insert migration name>"
```

Upgrading database

```shell
alembic upgrade head
```

Downgrading database

```shell
alembic downgrade -1
```
