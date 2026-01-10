# api_config.py
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

class SportsRadarAPIConfig:
    BASE_URL = "https://api.sportradar.com/tennis/trial/v3/en/"

    # --- Specific API Keys for each domain ---
    COMPETITIONS_API_KEY = os.getenv("SPORTSRADAR_COMPETITIONS_API_KEY")
    COMPLEXES_API_KEY = os.getenv("SPORTSRADAR_COMPLEXES_API_KEY")
    COMPETITORS_API_KEY = os.getenv("SPORTSRADAR_COMPETITORS_API_KEY")

    # Basic check for missing keys
    if not all([COMPETITIONS_API_KEY, COMPLEXES_API_KEY, COMPETITORS_API_KEY]):
        missing_keys = [k for k, v in {
            "SPORTSRADAR_COMPETITIONS_API_KEY": COMPETITIONS_API_KEY,
            "SPORTSRADAR_COMPLEXES_API_KEY": COMPLEXES_API_KEY,
            "SPORTSRADAR_COMPETITORS_API_KEY": COMPETITORS_API_KEY
        }.items() if not v]
        raise ValueError(
            f"ERROR: The following SportRadar API keys are missing or empty in your .env file: {', '.join(missing_keys)}.\n"
            "Please ensure they are correctly set in the .env file."
        )