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

def read_blob(container, blob_name):
    client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    blob = client.get_container_client(container).get_blob_client(blob_name)
    return blob.download_blob().readall()

def upload_blob(data, container, blob_name):
    client = BlobServiceClient.from_connection_string(
        CONNECTION_STRING,
        max_block_size=4*1024*1024,
        max_single_put_size=4*1024*1024,
        retry_total=5,
        connection_timeout=300,
        read_timeout=300
    )
    container_client = client.get_container_client(container)
    container_client.get_blob_client(blob_name).upload_blob(
        data, overwrite=True, max_concurrency=4
    )
    print(f"Uploaded: {blob_name} → {container}")

def clean_deprivation():
    print("Reading deprivation index from bronze...")
    raw = read_blob("bronze", "deprivation/deprivation_index.xlsx")
    df = pd.read_excel(io.BytesIO(raw), sheet_name="IMD")

    print(f"Raw shape: {df.shape}")

    # Rename columns to snake_case
    df = df.rename(columns={
        "Local Authority District code (2019)" : "lad_code",
        "Local Authority District name (2019)" : "lad_name",
        "IMD - Average rank "                  : "imd_avg_rank",
        "IMD - Rank of average rank "          : "imd_rank_of_avg_rank",
        "IMD - Average score "                 : "imd_avg_score",
        "IMD - Rank of average score "         : "imd_rank_of_avg_score",
        "IMD - Proportion of LSOAs in most deprived 10% nationally " : "imd_pct_deprived_10",
        "IMD - Rank of proportion of LSOAs in most deprived 10% nationally " : "imd_rank_pct_deprived",
        "IMD 2019 - Extent "                   : "imd_extent",
        "IMD 2019 - Rank of extent "           : "imd_rank_extent",
        "IMD 2019 - Local concentration "      : "imd_local_concentration",
        "IMD 2019 - Rank of local concentration " : "imd_rank_local_concentration"
    })

    # Clean up
    df["lad_code"] = df["lad_code"].str.strip()
    df["lad_name"] = df["lad_name"].str.strip()
    df = df.dropna(subset=["lad_code", "imd_avg_score"])
    df = df.drop_duplicates(subset=["lad_code"])

    print(f"Clean shape: {df.shape}")
    print(f"Most deprived areas (top 5 by avg score):")
    print(df.nlargest(5, "imd_avg_score")[["lad_name", "imd_avg_score"]])

    return df

if __name__ == "__main__":
    df = clean_deprivation()

    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    upload_blob(csv_buffer.read(), "silver", "deprivation/deprivation_clean.csv")

    print("Silver deprivation done")