import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT")
STORAGE_KEY = os.getenv("AZURE_STORAGE_KEY")

CONNECTION_STRING = (
    f"DefaultEndpointsProtocol=https;"
    f"AccountName={STORAGE_ACCOUNT};"
    f"AccountKey={STORAGE_KEY};"
    f"EndpointSuffix=core.windows.net"
)

def test_connection():
    client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    containers = [c.name for c in client.list_containers()]
    print(f"Connected to: {STORAGE_ACCOUNT}")
    print(f"Containers found: {containers}")

if __name__ == "__main__":
    test_connection()