import argparse
import math
from pathlib import Path

import pandas as pd
from pymongo import MongoClient


def clean_records(df: pd.DataFrame) -> list[dict]:
    df = df.where(pd.notnull(df), None)
    return df.to_dict(orient="records")


def load_csv(client, db_name: str, collection_name: str, csv_path: Path, chunk_size: int):
    db = client[db_name]
    collection = db[collection_name]

    total = 0
    for chunk in pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False):
        records = clean_records(chunk)
        if records:
            collection.insert_many(records)
            total += len(records)
    return total


def create_indexes(db, baseline_collection: str, future_collection: str):
    db[baseline_collection].create_index("aqid")
    db[baseline_collection].create_index("string_id")
    db[baseline_collection].create_index("gid_0")
    db[baseline_collection].create_index("gid_1")
    db[baseline_collection].create_index("name_0")
    db[baseline_collection].create_index("name_1")
    db[future_collection].create_index("BasinID")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--db", default="water_stewardship")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--future", required=True)
    parser.add_argument("--baseline-collection", default="wri_baseline_annual")
    parser.add_argument("--future-collection", default="wri_future_projections")
    parser.add_argument("--chunk-size", type=int, default=5000)
    parser.add_argument("--drop", action="store_true")
    args = parser.parse_args()

    client = MongoClient(args.mongo_uri)
    db = client[args.db]

    if args.drop:
        db[args.baseline_collection].drop()
        db[args.future_collection].drop()

    baseline_total = load_csv(
        client,
        args.db,
        args.baseline_collection,
        Path(args.baseline),
        args.chunk_size,
    )
    future_total = load_csv(
        client,
        args.db,
        args.future_collection,
        Path(args.future),
        args.chunk_size,
    )
    create_indexes(db, args.baseline_collection, args.future_collection)

    print(f"Baseline rows loaded: {baseline_total}")
    print(f"Future rows loaded: {future_total}")


if __name__ == "__main__":
    main()
