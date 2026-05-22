"""Verify BigQuery setup before running data collection."""

import os
import sys


def check_environment():
    """Check if environment is properly configured for BigQuery."""
    
    print("=" * 60)
    print("BigQuery Environment Check")
    print("=" * 60)
    
    issues = []
    
    # Check for GOOGLE_APPLICATION_CREDENTIALS
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        print(f"✓ GOOGLE_APPLICATION_CREDENTIALS: {creds_path}")
        if os.path.exists(creds_path):
            print("  ✓ Credentials file exists")
        else:
            issues.append("Credentials file does not exist at specified path")
            print("  ✗ Credentials file NOT found")
    else:
        print("✗ GOOGLE_APPLICATION_CREDENTIALS not set")
        issues.append("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
    
    # Check for project ID
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project_id:
        print(f"✓ GOOGLE_CLOUD_PROJECT: {project_id}")
    else:
        print("✗ GOOGLE_CLOUD_PROJECT not set (will use default from credentials)")
    
    # Try importing BigQuery
    try:
        from google.cloud import bigquery
        print("✓ google-cloud-bigquery package installed")
    except ImportError:
        issues.append("google-cloud-bigquery not installed")
        print("✗ google-cloud-bigquery NOT installed")
        print("  Run: pip install google-cloud-bigquery")
    
    return issues


def test_connection():
    """Test BigQuery connection with a simple query."""
    
    print("\n" + "=" * 60)
    print("Testing BigQuery Connection")
    print("=" * 60)
    
    try:
        from google.cloud import bigquery
        
        client = bigquery.Client()
        print(f"✓ Connected to project: {client.project}")
        
        # Test with a simple GDELT query
        test_query = """
        SELECT COUNT(*) as cnt
        FROM `gdelt-bq.gdeltv2.events`
        WHERE SQLDATE = 20250201
        LIMIT 1
        """
        
        print("Running test query on GDELT...")
        result = client.query(test_query).result()
        for row in result:
            print(f"✓ Query successful! Found {row.cnt:,} events for 2025-02-01")
        
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def print_setup_instructions():
    """Print setup instructions for BigQuery access."""
    
    print("\n" + "=" * 60)
    print("SETUP INSTRUCTIONS")
    print("=" * 60)
    print("""
To use BigQuery for GDELT data collection, follow these steps:

1. CREATE A GOOGLE CLOUD PROJECT (if you don't have one)
   - Go to: https://console.cloud.google.com/
   - Create a new project or use an existing one

2. ENABLE THE BIGQUERY API
   - Go to: https://console.cloud.google.com/apis/library/bigquery.googleapis.com
   - Click "Enable"

3. CREATE A SERVICE ACCOUNT
   - Go to: https://console.cloud.google.com/iam-admin/serviceaccounts
   - Click "Create Service Account"
   - Name: "gdelt-reader" (or similar)
   - Grant role: "BigQuery Job User" and "BigQuery Data Viewer"
   - Click "Create Key" → JSON → Download

4. SET ENVIRONMENT VARIABLES
   Add to your shell profile (~/.zshrc or ~/.bashrc):

   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-service-account-key.json"
   export GOOGLE_CLOUD_PROJECT="your-project-id"

   Then run: source ~/.zshrc

5. ALTERNATIVE: Use gcloud CLI
   If you have gcloud CLI installed:

   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID

6. INSTALL PYTHON PACKAGES
   pip install -r requirements.txt

NOTE: GDELT data in BigQuery is publicly accessible, so you only need
basic BigQuery permissions. However, queries do incur costs (about $5
per TB scanned). Our query should scan ~1-5 GB, costing a few cents.
""")


def main():
    """Run all checks and provide guidance."""
    
    issues = check_environment()
    
    if not issues:
        success = test_connection()
        if success:
            print("\n✓ All checks passed! You're ready to run data_collection.py")
            return 0
    
    print_setup_instructions()
    return 1


if __name__ == "__main__":
    sys.exit(main())