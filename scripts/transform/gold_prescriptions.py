import os
import io
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

def read_silver(blob_name):
    client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    blob = client.get_container_client("silver").get_blob_client(blob_name)
    return pd.read_csv(io.BytesIO(blob.download_blob().readall()))

def upload_gold(df, blob_name):
    client = BlobServiceClient.from_connection_string(
        CONNECTION_STRING,
        max_block_size=4*1024*1024,
        max_single_put_size=4*1024*1024,
        retry_total=5,
        connection_timeout=300,
        read_timeout=300
    )
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    client.get_container_client("gold").get_blob_client(blob_name).upload_blob(
        csv_buffer.read(), overwrite=True, max_concurrency=4
    )
    print(f"Uploaded: {blob_name} → gold")

if __name__ == "__main__":
    print("Loading silver prescriptions...")
    df = read_silver("prescriptions/prescriptions_clean.csv")
    print(f"Shape: {df.shape}")

    # Gold table 2a - prescriptions by region and BNF chapter
    regional_bnf = (
        df.groupby(["region_name", "bnf_chapter"])
        .agg(
            total_items=("items", "sum"),
            total_nic=("nic", "sum"),
            total_quantity=("total_quantity", "sum")
        )
        .reset_index()
    )

    print(f"Regional BNF shape: {regional_bnf.shape}")
    print(regional_bnf.head())

    # Gold table 2b - prescriptions by region only 
    regional_summary = (
        df.groupby("region_name")
        .agg(
            total_items=("items", "sum"),
            total_nic=("nic", "sum"),
            unique_drug_categories=("bnf_chapter", "nunique")
        )
        .reset_index()
        .sort_values("total_items", ascending=False)
    )

    print(f"\nRegional summary:")
    print(regional_summary.to_string())

    upload_gold(regional_bnf, "prescriptions/prescriptions_by_region_bnf.csv")
    upload_gold(regional_summary, "prescriptions/prescriptions_regional_summary.csv")
    print("\nGold prescriptions done")