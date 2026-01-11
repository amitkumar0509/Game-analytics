# db_config.py
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()  # Load environment variables from .env file


class DatabaseConfig:
    DB_TYPE = os.getenv("DB_TYPE", "mysql").lower()
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    _default_port = "3306" if DB_TYPE == "mysql" else "5432"
    DB_PORT = os.getenv("DB_PORT", _default_port)
    DB_NAME = os.getenv("DB_NAME")

    # Basic check for missing DB credentials
    if not all([DB_USER, DB_PASSWORD, DB_NAME]):
        missing_db_creds = [k for k, v in {
            "DB_USER": DB_USER,
            "DB_PASSWORD": DB_PASSWORD,
            "DB_NAME": DB_NAME
        }.items() if not v]
        raise ValueError(
            "ERROR: The following database credentials are missing or empty in your .env file: "
            f"{', '.join(missing_db_creds)}.\n"
            "Please ensure they are correctly set in the .env file."
        )

    @classmethod
    def _get_driver(cls) -> str:
        if cls.DB_TYPE == "postgresql":
            return "postgresql+psycopg2"
        if cls.DB_TYPE == "mysql":
            return "mysql+pymysql"
        raise ValueError(
            "Unsupported database type specified in .env (DB_TYPE). Supported values are 'mysql' and 'postgresql'."
        )

    @classmethod
    def get_connection_string(cls) -> str:
        driver = cls._get_driver()
        user = quote_plus(cls.DB_USER)
        password = quote_plus(cls.DB_PASSWORD)
        return f"{driver}://{user}:{password}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"

    @classmethod
    def ensure_database_exists(cls) -> None:
        """Creates the configured database if it does not already exist (MySQL only)."""
        if cls.DB_TYPE != "mysql":
            return

        driver = cls._get_driver()
        user = quote_plus(cls.DB_USER)
        password = quote_plus(cls.DB_PASSWORD)
        admin_connection_uri = f"{driver}://{user}:{password}@{cls.DB_HOST}:{cls.DB_PORT}/"

        safe_db_name = cls.DB_NAME.replace("`", "")

        engine = create_engine(admin_connection_uri, isolation_level="AUTOCOMMIT")
        try:
            with engine.connect() as connection:
                    connection.execute(text(f"CREATE DATABASE IF NOT EXISTS `{safe_db_name}`"))
        finally:
            engine.dispose()