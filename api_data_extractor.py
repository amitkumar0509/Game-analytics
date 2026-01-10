# api_data_extractor.py
import requests
import pandas as pd
from api_config import SportsRadarAPIConfig


class SportsRadarAPI:
    """Base class for SportRadar API interactions, handling specific API key per instance."""

    def __init__(self, api_key: str, base_url: str = SportsRadarAPIConfig.BASE_URL):
        self.api_key = api_key
        self.base_url = base_url
        if not self.api_key:
            raise ValueError("API key cannot be empty for SportsRadarAPI instance.")

    def _make_request(self, endpoint: str, params: dict = None) -> dict:
        """Makes an HTTP GET request to the SportRadar API."""
        if params is None:
            params = {}

        url = f"{self.base_url}{endpoint}"

        params["api_key"] = self.api_key  # API key now goes here as a URL parameter
        headers = {"accept": "application/json"}  # Keep other headers if needed

        print(f"Making request to: {url} with key (first 5 chars): {self.api_key[:5]}...")

        try:
            response = requests.get(url, headers=headers, params=params)  # Pass params and headers
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err} - {response.text}")
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"An unexpected error occurred: {req_err}")
        return None


class TennisDataExtractor:
    """Extracts and flattens tennis data from SportRadar API using specific API keys for each domain."""

    def __init__(self):
        # Create separate API instances for each domain, using their respective keys
        self.competitions_api = SportsRadarAPI(api_key=SportsRadarAPIConfig.COMPETITIONS_API_KEY)
        self.complexes_api = SportsRadarAPI(api_key=SportsRadarAPIConfig.COMPLEXES_API_KEY)
        self.competitors_api = SportsRadarAPI(api_key=SportsRadarAPIConfig.COMPETITORS_API_KEY)

    def get_competitions_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Collects competition data, parses JSON, and returns it as two DataFrames: categories and competitions.
        """
        endpoint = "competitions.json"
        data = self.competitions_api._make_request(endpoint)  # Use specific API instance

        if not data or 'competitions' not in data:
            print("No competition data found or invalid response.")
            return pd.DataFrame(), pd.DataFrame()

        all_categories = []
        all_competitions = []

        for comp_data in data['competitions']:
            # Extract Category Data
            category_info = comp_data.get('category', {})
            if category_info and category_info.get('id') and category_info.get('name'):
                all_categories.append({
                    'category_id': category_info['id'],
                    'category_name': category_info['name']
                })

            # Extract Competition Data
            all_competitions.append({
                'competition_id': comp_data.get('id'),
                'competition_name': comp_data.get('name'),
                'parent_id': comp_data.get('parent_id'),
                'type': comp_data.get('type'),
                'gender': comp_data.get('gender'),
                'category_id': category_info.get('id') if category_info else None,
                'level': comp_data.get('level')
            })

        # Deduplicate categories and ensure primary keys are not null
        categories_df = pd.DataFrame(all_categories).drop_duplicates(subset=['category_id']).dropna(
            subset=['category_id'])

        # Ensure essential competition fields are not null
        competitions_df = pd.DataFrame(all_competitions).dropna(
            subset=['competition_id', 'competition_name', 'type', 'gender'])

        return categories_df, competitions_df

    def get_complexes_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Collects complexes data, parses JSON, and returns it as two DataFrames: complexes and venues.
        """
        endpoint = "complexes.json"
        data = self.complexes_api._make_request(endpoint)  # Use specific API instance

        if not data or 'complexes' not in data:
            print("No complexes data found or invalid response.")
            return pd.DataFrame(), pd.DataFrame()

        all_complexes = []
        all_venues = []

        for complex_data in data['complexes']:
            complex_id = complex_data.get('id')
            if not complex_id:
                continue  # Skip complex if ID is missing

            all_complexes.append({
                'complex_id': complex_id,
                'complex_name': complex_data.get('name')
            })

            # Extract Venue Data
            for venue_data in complex_data.get('venues', []):
                if venue_data.get('id') and venue_data.get('name') and venue_data.get('city_name') and \
                        venue_data.get('country_name') and venue_data.get('country_code') and venue_data.get(
                    'timezone'):
                    all_venues.append({
                        'venue_id': venue_data.get('id'),
                        'venue_name': venue_data.get('name'),
                        'city_name': venue_data.get('city_name'),
                        'country_name': venue_data.get('country_name'),
                        'country_code': venue_data.get('country_code'),
                        'timezone': venue_data.get('timezone'),
                        'complex_id': complex_id
                    })

        complexes_df = pd.DataFrame(all_complexes).drop_duplicates(subset=['complex_id']).dropna(subset=['complex_id'])
        venues_df = pd.DataFrame(all_venues).drop_duplicates(subset=['venue_id']).dropna(
            subset=['venue_id', 'venue_name', 'city_name', 'country_name', 'country_code', 'timezone', 'complex_id'])

        return complexes_df, venues_df

    def get_doubles_competitor_rankings_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Collects doubles competitor rankings data, parses JSON based on observed structure,
        and returns it as two DataFrames: competitors and rankings.
        """
        endpoint = "double_competitors_rankings.json"
        data = self.competitors_api._make_request(endpoint)  # Use specific API instance

        if not data or 'rankings' not in data:
            print("No doubles rankings data found or invalid response.")
            return pd.DataFrame(), pd.DataFrame()

        all_competitors = []
        all_rankings = []

         # data['rankings'] now appears to be a list of categories (e.g., ATP, WTA)
        for ranking_category_entry in data.get('rankings', []):
            # Each entry in 'rankings' seems to contain a 'competitor_rankings' list
            for ranking_entry in ranking_category_entry.get('competitor_rankings', []):
                competitor_data = ranking_entry.get('competitor', {})
                competitor_id = competitor_data.get('id')

                if not competitor_id:
                    continue

                # Extract Competitor Data
                if competitor_data.get('id') and competitor_data.get('name') and competitor_data.get('country') and \
                        competitor_data.get('country_code') and competitor_data.get('abbreviation'):
                    all_competitors.append({
                        'competitor_id': competitor_id,
                        'name': competitor_data['name'],
                        'country': competitor_data['country'],
                        'country_code': competitor_data['country_code'],
                        'abbreviation': competitor_data['abbreviation']
                    })

                # Extract Ranking Data
                if ranking_entry.get('rank') is not None and ranking_entry.get('movement') is not None and \
                        ranking_entry.get('points') is not None and ranking_entry.get(
                    'competitions_played') is not None:
                    all_rankings.append({
                        'rank': ranking_entry['rank'],
                        'movement': ranking_entry['movement'],
                        'points': ranking_entry['points'],
                        'competitions_played': ranking_entry['competitions_played'],
                        'competitor_id': competitor_id
                    })


        competitors_df = pd.DataFrame(all_competitors).drop_duplicates(subset=['competitor_id']).dropna(
            subset=['competitor_id', 'name', 'country', 'country_code', 'abbreviation'])
        rankings_df = pd.DataFrame(all_rankings).dropna(
            subset=['rank', 'movement', 'points', 'competitions_played', 'competitor_id'])

        return competitors_df, rankings_df



if __name__ == "__main__":
    extractor = TennisDataExtractor()

    print("\n--- Testing Competition Data Extraction ---")
    categories_df, competitions_df = extractor.get_competitions_data()
    print("Categories Head:\n", categories_df.head())
    print("Competitions Head:\n", competitions_df.head())

    print("\n--- Testing Complexes Data Extraction ---")
    complexes_df, venues_df = extractor.get_complexes_data()
    print("Complexes Head:\n", complexes_df.head())
    print("Venues Head:\n", venues_df.head())

    print("\n--- Testing Competitor Rankings Data Extraction ---")
    competitors_df, rankings_df = extractor.get_doubles_competitor_rankings_data()
    print("Competitors Head:\n", competitors_df.head())
    print("Rankings Head:\n", rankings_df.head())