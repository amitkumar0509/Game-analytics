# db_loader.py
import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from db_models import Base, Category, Competition, Complex, Venue, Competitor, CompetitorRanking, create_db_tables
from db_config import DatabaseConfig
from api_data_extractor import TennisDataExtractor
from sqlalchemy import create_engine


class DataLoader:
    """Manages the process of extracting data from API and loading it into the database."""

    def __init__(self):
        self.engine = create_engine(DatabaseConfig.get_connection_string())
        create_db_tables(self.engine)  # Ensure tables exist
        self.Session = sessionmaker(bind=self.engine)
        self.extractor = TennisDataExtractor()  # Instance of the API extractor

    def _insert_dataframe(self, df: pd.DataFrame, model_class: Base):
        """Inserts DataFrame records into the specified database table using SQLAlchemy ORM."""
        if df.empty:
            print(f"No data to insert into {model_class.__tablename__}.")
            return

        session = self.Session()
        try:
            data_to_insert = df.to_dict(orient='records')

            # Using session.merge for upsert functionality (insert or update if PK exists)
            for record in data_to_insert:
                instance = model_class(**record)
                session.merge(instance)  # merge handles existing primary keys by updating

            session.commit()
            print(f"Successfully inserted/merged {len(df)} records into {model_class.__tablename__}.")
        except IntegrityError as ie:
            session.rollback()
            print(f"Integrity error during insert into {model_class.__tablename__}: {ie}")
            print("This often means duplicate primary keys. Ensure your DataFrames are deduplicated before insertion.")
        except SQLAlchemyError as sa_err:
            session.rollback()
            print(f"SQLAlchemy error during insert into {model_class.__tablename__}: {sa_err}")
        except Exception as e:
            session.rollback()
            print(f"An unexpected error occurred during insert into {model_class.__tablename__}: {e}")
        finally:
            session.close()


    def load_all_data(self):
            """Orchestrates the extraction and loading of all data domains."""
            print("Starting data extraction and loading...")

            # --- Load Competitions Data ---
            print("\n--- Loading Competitions Data ---")
            categories_df, competitions_df = self.extractor.get_competitions_data()
            self._insert_dataframe(categories_df, Category)
            self._insert_dataframe(competitions_df, Competition)

            # --- Load Complexes Data ---
            print("\n--- Loading Complexes Data ---")
            complexes_df, venues_df = self.extractor.get_complexes_data()
            self._insert_dataframe(complexes_df, Complex)
            self._insert_dataframe(venues_df, Venue)

            # --- Load Doubles Competitor Rankings Data ---
            print("\n--- Loading Doubles Competitor Rankings Data ---")
            competitors_df, rankings_df = self.extractor.get_doubles_competitor_rankings_data()

            # Insert competitors first ---
            self._insert_dataframe(competitors_df, Competitor)

            # Filter rankings to ensure competitor_id exists in the processed competitors_df ---
            # Get the IDs of competitors that were actually inserted/merged
            inserted_competitor_ids = set(competitors_df['competitor_id'].tolist())

            # Filter rankings_df to only include records whose competitor_id is in our inserted_competitor_ids
            filtered_rankings_df = rankings_df[rankings_df['competitor_id'].isin(inserted_competitor_ids)]

            if len(rankings_df) != len(filtered_rankings_df):
                print(
                    f"Warning: {len(rankings_df) - len(filtered_rankings_df)} ranking entries were skipped due to missing competitor data.")


            self._insert_dataframe(filtered_rankings_df, CompetitorRanking)

            print("\nData loading process complete.")


if __name__ == "__main__":
    loader = DataLoader()
    loader.load_all_data()