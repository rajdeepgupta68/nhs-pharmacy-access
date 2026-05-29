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
        data,
        overwrite=True,
        max_concurrency=4
    )
    print(f"Uploaded: {blob_name} → {container}")

def clean_pharmacy_locations():
    print("Reading pharmacy locations from bronze...")
    raw = read_blob("bronze", "pharmacy/pharmacy_locations.csv")
    df = pd.read_csv(io.BytesIO(raw))
    print(f"Raw shape: {df.shape}")

    # Rename columns to snake_case
    df = df.rename(columns={
        "PHARMACY_ODS_CODE_F_CODE"  : "ods_code",
        "HEALTH_AND_WELLBEING_BOARD": "hwb_name",
        "PHARMACY_TRADING_NAME"     : "trading_name",
        "ORGANISATION_NAME"         : "org_name",
        "ADDRESS_FIELD_1"           : "address_1",
        "ADDRESS_FIELD_2"           : "address_2",
        "ADDRESS_FIELD_3"           : "address_3",
        "ADDRESS_FIELD_4"           : "address_4",
        "POST_CODE"                 : "postcode",
        "WEEKLY_TOTAL"              : "weekly_hours",
        "CONTRACT_TYPE"             : "contract_type"
    })

    # Keep only useful columns
    df = df[[
        "ods_code", "trading_name", "org_name",
        "address_1", "address_2", "address_3", "address_4",
        "postcode", "hwb_name", "contract_type", "weekly_hours"
    ]]

    # Clean postcode - uppercase, strip whitespace
    df["postcode"] = df["postcode"].str.upper().str.strip()

    # Clean contract type
    df["contract_type"] = df["contract_type"].str.strip().str.title()

    # Drop rows with no postcode or ODS code
    before = len(df)
    df = df.dropna(subset=["postcode", "ods_code"])
    after = len(df)
    print(f"Dropped {before - after} rows with missing postcode/ODS code")

    # Drop duplicates
    df = df.drop_duplicates(subset=["ods_code"])

    print(f"Clean shape: {df.shape}")
    print(f"Contract types: {df['contract_type'].value_counts().to_dict()}")

    return df

if __name__ == "__main__":
    df = clean_pharmacy_locations()

    # Upload to silver as CSV
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    upload_blob(csv_buffer.read(), "silver", "pharmacy/pharmacy_locations_clean.csv")

    print("Silver pharmacy locations done")