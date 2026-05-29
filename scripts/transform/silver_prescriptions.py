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
    print("Reading prescription data...")
    raw = read_blob("bronze", "prescriptions/pca_icb_snomed_2024_2025.csv")

    df = pd.read_csv(io.BytesIO(raw))
    print(f"Raw shape: {df.shape}")

    # only useful columns
    df = df[[
        "YEAR_DESC", "REGION_NAME", "REGION_CODE",
        "ICB_NAME", "ICB_CODE",
        "BNF_CHAPTER", "BNF_SECTION",
        "ITEMS", "TOTAL_QUANTITY", "NIC"
    ]].rename(columns={
        "YEAR_DESC"      : "year",
        "REGION_NAME"    : "region_name",
        "REGION_CODE"    : "region_code",
        "ICB_NAME"       : "icb_name",
        "ICB_CODE"       : "icb_code",
        "BNF_CHAPTER"    : "bnf_chapter",
        "BNF_SECTION"    : "bnf_section",
        "ITEMS"          : "items",
        "TOTAL_QUANTITY" : "total_quantity",
        "NIC"            : "nic"
    })

    # Clean
    df["region_name"] = df["region_name"].str.strip().str.title()
    df["icb_name"]    = df["icb_name"].str.strip().str.title()
    df["bnf_chapter"] = df["bnf_chapter"].str.strip().str.title()
    df["items"]       = pd.to_numeric(df["items"], errors="coerce")
    df["nic"]         = pd.to_numeric(df["nic"], errors="coerce")
    df = df.dropna(subset=["items", "region_name"])

    print(f"Clean shape: {df.shape}")
    print(f"Regions: {df['region_name'].unique().tolist()}")
    print(f"Top 5 BNF chapters by items:")
    print(df.groupby("bnf_chapter")["items"].sum().nlargest(5))

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
        "prescriptions/prescriptions_clean.csv"
    ).upload_blob(csv_buffer.read(), overwrite=True, max_concurrency=4)
    print("Uploaded: prescriptions/prescriptions_clean.csv → silver")
    print("Silver prescriptions done")