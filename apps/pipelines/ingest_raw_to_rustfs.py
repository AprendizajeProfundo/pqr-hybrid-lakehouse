from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_ENDPOINT_URL = "http://localhost:9000"
DEFAULT_BUCKET = "pqr-hybrid-lakehouse-datalake"


def _build_object_key(run_id: str, day: str, source: str = "mixed") -> str:
    return f"raw/pqrs/source={source}/day={day}/run_id={run_id}/events.jsonl"


def run_ingest_raw_to_rustfs(
    input_path: Path,
    run_id: str,
    day: str,
    bucket: str = DEFAULT_BUCKET,
    endpoint_url: str = DEFAULT_ENDPOINT_URL,
    object_key: str | None = None,
    create_bucket: bool = True,
) -> dict[str, Any]:
    try:
        import boto3  # type: ignore
        from botocore.exceptions import ClientError  # type: ignore
    except Exception as exc:
        raise RuntimeError("No se encontro boto3. Instala dependencia para subir a RustFS/S3.") from exc

    if not input_path.exists():
        raise FileNotFoundError(f"No existe archivo de entrada: {input_path}")

    access_key = os.getenv("RUSTFS_ACCESS_KEY", "rustfsadmin")
    secret_key = os.getenv("RUSTFS_SECRET_KEY", "rustfsadmin")

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
    )

    if create_bucket:
        try:
            s3.head_bucket(Bucket=bucket)
        except ClientError:
            s3.create_bucket(Bucket=bucket)

    key = object_key or _build_object_key(run_id=run_id, day=day)
    s3.upload_file(str(input_path), bucket, key)

    return {
        "bucket": bucket,
        "object_key": key,
        "endpoint_url": endpoint_url,
        "input_path": str(input_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload local raw JSONL to RustFS (S3-compatible raw layer).")
    parser.add_argument("--input", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--day", required=True, help="Fecha de carga del lote (YYYY-MM-DD)")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--endpoint-url", default=DEFAULT_ENDPOINT_URL)
    parser.add_argument("--object-key", default=None)
    parser.add_argument("--no-create-bucket", action="store_true")
    args = parser.parse_args()

    result = run_ingest_raw_to_rustfs(
        input_path=Path(args.input),
        run_id=args.run_id,
        day=args.day,
        bucket=args.bucket,
        endpoint_url=args.endpoint_url,
        object_key=args.object_key,
        create_bucket=not args.no_create_bucket,
    )
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
