"""
Usage:
    1. First, verify BigQuery setup:
       python setup_bigquery.py

    2. Run data collection:
       python data_collection.py

    3. Run Python Shiny dashboard:
       python -m shiny run shiny_app/app.py --host 127.0.0.1 --port 8004
"""

from data_collection import run_pipeline, load_processed_data


def main():
    print("\nTo collect data, run: python data_collection.py")
    print("To check BigQuery setup, run: python setup_bigquery.py")
    print("To run the Shiny dashboard, run: python -m shiny run shiny_app/app.py --host 127.0.0.1 --port 8004")


if __name__ == "__main__":
    main()
