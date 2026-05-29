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

if __name__ == "__main__":
    print("Reading population estimates from bronze...")
    raw = read_blob("bronze", "population/population_estimates.xlsx")

    df = pd.read_excel(io.BytesIO(raw), sheet_name="MYE2 - Persons", header=7)

    print(f"Raw shape: {df.shape}")

    # Keep only local authority districts (code starts with E06, E07, E08, E09)
    lad_mask = df["Code"].str.match(r"^E0[6-9]", na=False)
    df = df[lad_mask].copy()

    # Keep only useful columns
    df = df[["Code", "Name", "Geography", "All ages"]].rename(columns={
        "Code"      : "lad_code",
        "Name"      : "lad_name",
        "Geography" : "geography_type",
        "All ages"  : "total_population"
    })

    # Clean up
    df["lad_code"] = df["lad_code"].str.strip()
    df["lad_name"] = df["lad_name"].str.strip()
    df["total_population"] = pd.to_numeric(df["total_population"], errors="coerce")
    df = df.dropna(subset=["lad_code", "total_population"])
    df = df.drop_duplicates(subset=["lad_code"])

    print(f"Clean shape: {df.shape}")
    print(f"Largest populations (top 5):")
    print(df.nlargest(5, "total_population")[["lad_name", "total_population"]])

    # Upload to silver
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
    client.get_container_client("silver").get_blob_client(
        "population/population_clean.csv"
    ).upload_blob(csv_buffer.read(), overwrite=True, max_concurrency=4)
    print("Uploaded: population/population_clean.csv → silver")
    print("Silver population done")