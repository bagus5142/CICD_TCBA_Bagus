import os
import json
import logging
from datetime import datetime, timezone
import requests
import azure.functions as func
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()

API_BASE_URL = os.getenv("API_BASE_URL", "https://upload-data-hotel.duckdns.org")
STORAGE_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "hotel-reviews-ingested"


def run_ingestion_pipeline() -> dict:
    """Mengambil daftar file dari FastAPI MinIO VPS dan menyimpannya ke Azure Blob Storage."""
    if not STORAGE_CONN_STR:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING belum diatur di Environment Variables.")

    response = requests.get(f"{API_BASE_URL}/api/uploads", timeout=30)
    response.raise_for_status()
    payload = response.json()

    # Menangani respons baik berupa list langsung maupun dict wrapper
    if isinstance(payload, list):
        uploads = payload
    elif isinstance(payload, dict):
        uploads = (
            payload.get("items")
            or payload.get("uploads")
            or payload.get("data")
            or payload.get("results")
            or []
        )
    else:
        uploads = []

    blob_service = BlobServiceClient.from_connection_string(STORAGE_CONN_STR)
    container_client = blob_service.get_container_client(CONTAINER_NAME)
    if not container_client.exists():
        container_client.create_container()

    batch_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    ingested_files = []

    for idx, item in enumerate(uploads):
        if not isinstance(item, dict):
            continue
        upload_id = item.get("id") or item.get("upload_id") or item.get("file_id")
        filename = (
            item.get("filename")
            or item.get("file_name")
            or item.get("name")
            or f"dataset_{upload_id or idx}.csv"
        )

        if upload_id is None:
            raise KeyError(f"Key ID tidak ditemukan pada item JSON: {list(item.keys())}")

        download_url = f"{API_BASE_URL}/api/uploads/{upload_id}/download"
        file_resp = requests.get(download_url, timeout=60)
        file_resp.raise_for_status()

        blob_path = f"batch_{batch_timestamp}/{filename}"
        blob_client = container_client.get_blob_client(blob_path)
        blob_client.upload_blob(file_resp.content, overwrite=True)
        ingested_files.append(blob_path)

    return {
        "status": "success",
        "total_files": len(ingested_files),
        "files": ingested_files,
    }


@app.timer_trigger(schedule="0 0 */6 * * *", arg_name="myTimer", run_on_startup=False)
def hotel_reviews_scheduler(myTimer: func.TimerRequest) -> None:
    logging.info("Memulai pipeline ingestion data Hotel Reviews (Jadwal 6 Jam)...")
    result = run_ingestion_pipeline()
    logging.info(f"Ingestion selesai: {result}")


@app.route(route="trigger-ingestion", auth_level=func.AuthLevel.FUNCTION)
def manual_trigger_ingestion(req: func.HttpRequest) -> func.HttpResponse:
    try:
        result = run_ingestion_pipeline()
        return func.HttpResponse(
            json.dumps(result, indent=2),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as e:
        logging.error(f"Pipeline ingestion gagal: {str(e)}")
        return func.HttpResponse(
            json.dumps({"status": "error", "detail": str(e)}, indent=2),
            mimetype="application/json",
            status_code=500,
        )