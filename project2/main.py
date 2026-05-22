"""
Usage:
    1. First, verify BigQuery setup:
       python setup_bigquery.py

    2. Run data collection:
       python data_collection.py

    3. (Later) Run dashboard:
       python -m shiny run app.py
"""

from data_collection import run_pipeline, load_processed_data


def main():
    print("\nTo collect data, run: python data_collection.py")
    print("To check BigQuery setup, run: python setup_bigquery.py")


if __name__ == "__main__":
    main()