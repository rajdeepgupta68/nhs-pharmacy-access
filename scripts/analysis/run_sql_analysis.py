import os
import io
import duckdb
import pandas as pd
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = (
    f"DefaultEndpointsProtocol=https;"
    f"AccountName={os.getenv('AZURE_STORAGE_ACCOUNT')};"
    f"AccountKey={os.getenv('AZURE_STORAGE_KEY')};"
    f"EndpointSuffix=core.windows.net"
)

def read_gold(blob_name):
    client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    blob = client.get_container_client("gold").get_blob_client(blob_name)
    return pd.read_csv(io.BytesIO(blob.download_blob().readall()))

def run_sql_file(con, sql_path):
    print(f"\n{'='*60}")
    print(f"Running: {sql_path}")
    print('='*60)

    with open(sql_path, 'r') as f:
        content = f.read()

    
    queries = []
    current = []
    for line in content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('--'):
            continue
        current.append(line)
        if stripped.endswith(';'):
            query = '\n'.join(current).strip().rstrip(';')
            if query:
                queries.append(query)
            current = []

    for i, query in enumerate(queries):
        print(f"\n--- Query {i+1} ---")
        try:
            result = con.execute(query).df()
            print(result.to_string(index=False))
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    print("Loading gold tables from Azure...")
    df_pharmacy_deprivation      = read_gold("pharmacy_deprivation/pharmacy_deprivation.csv")
    df_prescriptions_by_region_bnf = read_gold("prescriptions/prescriptions_by_region_bnf.csv")
    df_prescriptions_regional    = read_gold("prescriptions/prescriptions_regional_summary.csv")

    print(f"pharmacy_deprivation: {df_pharmacy_deprivation.shape}")
    print(f"prescriptions_by_region_bnf: {df_prescriptions_by_region_bnf.shape}")
    print(f"prescriptions_regional_summary: {df_prescriptions_regional.shape}")

    # Register tables in DuckDB
    con = duckdb.connect()
    con.register("pharmacy_deprivation", df_pharmacy_deprivation)
    con.register("prescriptions_by_region_bnf", df_prescriptions_by_region_bnf)
    con.register("prescriptions_regional_summary", df_prescriptions_regional)

    # Run all three SQL analysis files
    sql_files = [
        "sql/analysis_deprivation_vs_access.sql",
        "sql/analysis_prescriptions_by_region.sql",
        "sql/analysis_pharmacy_density.sql"
    ]

    for sql_file in sql_files:
        run_sql_file(con, sql_file)

    print("\nAll analysis complete")