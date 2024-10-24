from logging.config import fileConfig

from sqlalchemy import create_engine

from alembic import context
from alembic.script import ScriptDirectory

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
import settings

config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
import database

# target_metadata = mymodel.Base.metadata
target_metadata = database.Base.metadata


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def process_revision_directives(context, _, directives):
    migration_script = directives[0]
    head_revision = ScriptDirectory.from_config(context.config).get_current_head()
    try:
        head_revision_int = int(head_revision)
    except TypeError or ValueError:
        new_rev_id = 1
    else:
        new_rev_id = head_revision_int + 1

    migration_script.rev_id = "{0:012}".format(new_rev_id)


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    urls = get_urls()
    for url in urls:
        print("\nrun migrations offline for url:", url)
        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    urls = get_urls()
    for url in urls:
        print("\nrun migrations online for url:", url)
        connectable = create_engine(url)

        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                process_revision_directives=process_revision_directives,
            )
            with context.begin_transaction():
                context.run_migrations()


def get_urls():
    url = "postgresql+psycopg://{}:{}@{}:{}/{}"
    return [
        url.format(
            settings.DB_USER,
            settings.DB_PASSWORD,
            settings.DB_HOST,
            settings.DB_PORT,
            settings.DB_DATABASE,
        )
    ]


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
