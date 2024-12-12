# Distributed inference

[![unit tests](https://github.com/galadriel-ai/distributed-inference/actions/workflows/unit_test.yml/badge.svg)](https://github.com/galadriel-ai/distributed-inference/actions/workflows/unit_test.yml)

This repository contains the code for the centralised server (a.ka. distributed
inference)
that interfaces to the consumer side to get the inference request and schedule
it to the
`galadriel-node`s in the Galadriel network.

## Requirements to run

- python 3.12
- docker (latest version)
- docker-compose (latest version)
- git (latest version)

## Installation

### Install Python 3.12, Docker, Docker-Compose, and Git

- For linux (Ubuntu), run the following commands:

```shell
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12
sudo apt-get install git docker docker-compose
```

- For macOS, run the following commands:

```shell
brew install python@3.12
brew install docker docker-compose git
```

Check if all the above has installed properly:

```shell
python3 --version
docker --version
docker-compose --version
git --version
```

### Clone the repository

Clone the `distributed-inference` repo and prepare it for running:

```shell
git clone https://github.com/galadriel-ai/distributed-inference.git
cd distributed-inference
pip3 install -r requirements.txt

```

### Install Database

We use postgres to store all the information about the nodes and the requests.
To setup the database, run the
following
command:

```shell
cd database
cp template.env .env
docker-compose up --build -d
```

### Insert Dummy Data

```shell
cd ..
PYTHONPATH=. python scripts/insert_users.py
PYTHONPATH=. python scripts/insert_node.py
```

`inset_node.py` has a variable `user_id` which should be updated with one of
the `id` from `user_profile` table.
For now this has to be done manually but in future we will automate this.

### Run the server:

```shell
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
python -m pylint --rcfile=setup.cfg distributedinference/*
python -m mypy .

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

**Adding credits**

```
source venv/bin/activate

PYTHONPATH=. python scripts/add_credits.py --help

# By email
PYTHONPATH=. python scripts/add_credits.py --email kristjan@galadriel.com --credits "0.2"
# Or user_profile.id
PYTHONPATH=. python scripts/add_credits.py --user_id 06710e92-acb3-784f-8000-aa9e8972ba51 --credits "0.2"
```

## Documentation

User facing documentation is hosted on https://docs.galadriel.com

To export openapi.json:

```
PYTHONPATH=. python scripts/export_openapi.py
```

