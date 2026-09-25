import sys
from logging.config import fileConfig
from pathlib import Path
from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context

# Add repository root to Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.models import Base
from core.config import settings

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_database_url() -> str:
    url = config.get_main_option("sqlalchemy.url")
    if not url or "driver://user:pass" in url:
        url = settings.DATABASE_URL
    return url

def run_migrations_offline() -> None:
    url = get_database_url()
    is_sqlite = url.startswith("sqlite")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=is_sqlite,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    url = get_database_url()
    is_sqlite = url.startswith("sqlite")

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
