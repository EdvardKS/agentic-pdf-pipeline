import json
from datetime import datetime
from pathlib import Path


def generate_manifest(documents):

    batch_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    manifest = {
        "batch_id": batch_id,
        "total_files": len(documents),
        "documents": documents
    }

    Path("batches").mkdir(exist_ok=True)

    file_path = f"batches/batch_{batch_id}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)

    return file_path