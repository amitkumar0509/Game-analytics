# db_config.py
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

class DatabaseConfig:
    DB_TYPE = os.getenv("DB_TYPE", "postgresql")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME")

    # Basic check for missing DB credentials
    if not all([DB_USER, DB_PASSWORD, DB_NAME]):
        missing_db_creds = [k for k, v in {
            "DB_USER": DB_USER,
            "DB_PASSWORD": DB_PASSWORD,
            "DB_NAME": DB_NAME
        }.items() if not v]
        raise ValueError(
            f"ERROR: The following database credentials are missing or empty in your .env file: {', '.join(missing_db_creds)}.\n"
            "Please ensure they are correctly set in the .env file."
        )

    @classmethod
    def get_connection_string(cls):
        if cls.DB_TYPE == "postgresql":
            return f"postgresql+psycopg2://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        else:
            raise ValueError("Unsupported database type specified in .env (DB_TYPE). Only 'postgresql' is supported for this project.")