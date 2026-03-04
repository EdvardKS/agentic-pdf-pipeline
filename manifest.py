import json
from datetime import datetime
from pathlib import Path


def mark_duplicates(documents):

    seen = set()

    for doc in documents:

        if doc["sha256"] in seen:
            doc["duplicate"] = True
        else:
            doc["duplicate"] = False
            seen.add(doc["sha256"])

    return documents


def summarize_batch(documents):

    total = len(documents)
    duplicates = sum(1 for d in documents if d.get("duplicate"))
    unique = total - duplicates
    total_size = sum(d["size"] for d in documents)

    summary = {
        "total_files": total,
        "duplicates": duplicates,
        "unique_files": unique,
        "total_size": total_size
    }

    print("\nBatch summary\n")
    print(f"Total documentos: {summary['total_files']}")
    print(f"Duplicados: {summary['duplicates']}")
    print(f"Unicos: {summary['unique_files']}")
    print(f"Tamaño total: {summary['total_size']} bytes")

    return summary


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

    print(f"\nManifest generado: {file_path}\n")

    return file_path