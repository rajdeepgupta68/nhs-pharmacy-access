import os
from azure.storage.blob import BlobServiceClient, BlobBlock
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING = (
    f"DefaultEndpointsProtocol=https;"
    f"AccountName={os.getenv('AZURE_STORAGE_ACCOUNT')};"
    f"AccountKey={os.getenv('AZURE_STORAGE_KEY')};"
    f"EndpointSuffix=core.windows.net"
)

def upload_file(local_path, blob_name, container_name="bronze"):
    client = BlobServiceClient.from_connection_string(
        CONNECTION_STRING,
        max_block_size=4*1024*1024,        # 4MB chunks
        max_single_put_size=4*1024*1024,   # anything larger goes in chunks
        retry_total=5,                      # retry 5 times on failure
        connection_timeout=300,             # 5 min timeout
        read_timeout=300
    )
    container = client.get_container_client(container_name)
    file_size = os.path.getsize(local_path)
    print(f"Uploading {local_path} ({file_size / 1024 / 1024:.1f} MB)...")
    with open(local_path, "rb") as f:
        container.get_blob_client(blob_name).upload_blob(
            f,
            overwrite=True,
            max_concurrency=4              # parallel chunk uploads
        )
    print(f"Done: {blob_name} → {container_name}")

if __name__ == "__main__":
    files_to_upload = [
        ("data/raw/pca_icb_snomed_2024_2025.csv",  "prescriptions/pca_icb_snomed_2024_2025.csv"),
        ("data/raw/pharmacy_locations.csv",          "pharmacy/pharmacy_locations.csv"),
        ("data/raw/deprivation_index.xlsx",          "deprivation/deprivation_index.xlsx"),
        ("data/raw/population_estimates.xlsx",       "population/population_estimates.xlsx"),
    ]

    for local_path, blob_name in files_to_upload:
        upload_file(local_path, blob_name)