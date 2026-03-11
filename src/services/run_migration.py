import os
from argparse import Namespace
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from alembic.util.exc import CommandError

from extensions import SqlBaseModel
from extensions.sqlalchemy import SessionLocal
from extensions.sqlalchemy.init import DATABASE_URL
from modules.user.models.user_model import UserModel
from modules.admin.models.admin_model import AdminModel

BASE_DIR = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = BASE_DIR / "extensions" / "migrations"
ALEMBIC_INI = MIGRATIONS_DIR / "alembic.ini"
VERSIONS_DIR = MIGRATIONS_DIR / "versions"
target_metadata = SqlBaseModel.metadata
alembicConfig = Config(
    str(ALEMBIC_INI),
    cmd_opts=Namespace(autogenerate=True, ignore_unknown_revisions=True, x=None)
)

session = SessionLocal()
session.execute(text("DROP TABLE IF EXISTS alembic_version;"))

session.commit()
alembicConfig.set_main_option("sqlalchemy.url", DATABASE_URL)
alembicConfig.set_main_option("script_location", str(MIGRATIONS_DIR))
isExist = VERSIONS_DIR.exists()
if not isExist:
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
command.stamp(alembicConfig, revision="head")
command.revision(alembicConfig, autogenerate=True)
try:
    command.upgrade(alembicConfig, revision="head")
except CommandError as exc:
    message = str(exc)
    if "Can't locate revision identified by" in message:
        session.execute(text("DELETE FROM alembic_version;"))
        session.commit()
        command.stamp(alembicConfig, revision="head")
        command.upgrade(alembicConfig, revision="head")
    else:
        raise
command.stamp(alembicConfig, revision="head")

session.close()
exit(0)
