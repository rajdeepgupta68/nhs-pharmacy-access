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

def read_gold(blob_name):
    client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    blob = client.get_container_client("gold").get_blob_client(blob_name)
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
    print("Building final regional summary...")

    df_pharm_dep  = read_gold("pharmacy_deprivation/pharmacy_deprivation.csv")
    df_rx_summary = read_gold("prescriptions/prescriptions_regional_summary.csv")

    # Summarise pharmacy/deprivation by broad region
    # Group local authorities into NHS regions manually
    region_map = {
        "Blackpool": "North West", "Knowsley": "North West",
        "Liverpool": "North West", "Manchester": "North West",
        "Burnley": "North West", "Blackburn with Darwen": "North West",
        "Middlesbrough": "North East And Yorkshire",
        "Kingston upon Hull, City of": "North East And Yorkshire",
        "Hartlepool": "North East And Yorkshire",
        "Birmingham": "Midlands",
    }

    df_pharm_dep["nhs_region"] = df_pharm_dep["lad_name"].map(region_map)

    # Regional deprivation averages
    regional_deprivation = (
        df_pharm_dep
        .groupby("nhs_region")
        .agg(
            avg_deprivation_score=("imd_avg_score", "mean"),
            avg_pharmacies_per_100k=("pharmacies_per_100k", "mean"),
            total_pharmacies=("pharmacy_count", "sum"),
            total_population=("total_population", "sum")
        )
        .reset_index()
        .dropna(subset=["nhs_region"])
        .round(2)
    )

    print("\nRegional deprivation summary:")
    print(regional_deprivation.to_string())

    # Merge 
    final = pd.merge(
        df_rx_summary,
        regional_deprivation,
        left_on="region_name",
        right_on="nhs_region",
        how="left"
    )

    final["items_per_1000_pop"] = (
        final["total_items"] / final["total_population"] * 1000
    ).round(2)

    print("\nFinal regional summary:")
    print(final[["region_name", "total_items", "avg_deprivation_score",
                 "avg_pharmacies_per_100k", "items_per_1000_pop"]].to_string())

    upload_gold(final, "regional_summary/regional_summary.csv")
    print("\nGold regional summary done")