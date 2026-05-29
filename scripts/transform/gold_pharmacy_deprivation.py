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
    # Load silver tables
    print("Loading silver tables...")
    df_pharmacy    = read_silver("pharmacy/pharmacy_locations_clean.csv")
    df_deprivation = read_silver("deprivation/deprivation_clean.csv")
    df_population  = read_silver("population/population_clean.csv")

    print(f"Pharmacy: {df_pharmacy.shape}")
    print(f"Deprivation: {df_deprivation.shape}")
    print(f"Population: {df_population.shape}")

    # 1. Extract postcode district from pharmacy postcode
    df_pharmacy["postcode_area"] = df_pharmacy["postcode"].str.split().str[0]

    # 2. Count pharmacies per health and wellbeing board area
    pharmacy_counts = (
        df_pharmacy
        .groupby("hwb_name")
        .agg(
            pharmacy_count=("ods_code", "count"),
            community_pharmacies=("contract_type", lambda x: (x == "Community").sum())
        )
        .reset_index()
    )

    print(f"\nPharmacy counts by HWB area: {pharmacy_counts.shape}")
    print(pharmacy_counts.head())

    # 3. Join deprivation to population on lad_code
    df_dep_pop = pd.merge(
        df_deprivation,
        df_population[["lad_code", "lad_name", "total_population"]],
        on="lad_code",
        how="inner"
    )

    print(f"\nDeprivation + Population joined: {df_dep_pop.shape}")

    # 4. Calculate pharmacies per 100k population
    # Match on area name 
    df_dep_pop["lad_name_clean"] = df_dep_pop["lad_name_x"].str.strip().str.lower()
    pharmacy_counts["hwb_clean"] = pharmacy_counts["hwb_name"].str.strip().str.lower()

    gold = pd.merge(
        df_dep_pop,
        pharmacy_counts,
        left_on="lad_name_clean",
        right_on="hwb_clean",
        how="left"
    )

    # Fill unmatched pharmacy counts with 0
    gold["pharmacy_count"] = gold["pharmacy_count"].fillna(0)

    # Calculate pharmacies per 100,000 population
    gold["pharmacies_per_100k"] = (
        gold["pharmacy_count"] / gold["total_population"] * 100000
    ).round(2)

    # Keep final columns
    gold = gold[[
        "lad_code", "lad_name_x", "total_population",
        "imd_avg_score", "imd_avg_rank",
        "imd_pct_deprived_10", "pharmacy_count",
        "community_pharmacies", "pharmacies_per_100k"
    ]].rename(columns={"lad_name_x": "lad_name"})

    print(f"\nGold table shape: {gold.shape}")
    print(f"\nTop 10 most deprived areas with pharmacy density:")
    print(
        gold.nlargest(10, "imd_avg_score")[
            ["lad_name", "imd_avg_score", "pharmacy_count", "pharmacies_per_100k"]
        ].to_string()
    )

    print(f"\nCorrelation (deprivation vs pharmacy density):")
    corr = gold[["imd_avg_score", "pharmacies_per_100k"]].corr()
    print(corr)

    upload_gold(gold, "pharmacy_deprivation/pharmacy_deprivation.csv")
    print("\nGold pharmacy deprivation done")