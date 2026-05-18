import os
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

load_dotenv(override=True)

try:
    import firebase_admin
    from firebase_admin import credentials, firestore, storage
except ImportError:  # pragma: no cover
    firebase_admin = None
    credentials = None
    firestore = None
    storage = None

_firestore_client = None


def _load_service_account() -> dict[str, Any] | None:
    raw_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw_json:
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            return None

    path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()
    if not path:
        return None

    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def get_firestore_client():
    global _firestore_client
    if _firestore_client is not None:
        return _firestore_client

    if firebase_admin is None:
        return None

    service_account = _load_service_account()
    if service_account is None:
        return None

    try:
        cred = credentials.Certificate(service_account)
        try:
            app = firebase_admin.get_app()
        except ValueError:
            app = firebase_admin.initialize_app(cred)
        _firestore_client = firestore.client(app)
        return _firestore_client
    except Exception:
        return None


def is_firebase_enabled() -> bool:
    return get_firestore_client() is not None


def is_firebase_storage_enabled() -> bool:
    return get_storage_bucket() is not None


def _user_collection(name: str):
    client = get_firestore_client()
    if client is None:
        raise RuntimeError("Firebase yapılandırılmamış")

    prefix = os.getenv("FIREBASE_COLLECTION_PREFIX", "finans_asistani")
    return client.collection(prefix).document("default_user").collection(name)


def _format_date(value):
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else value


def _get_field(source, field, default=None):
    if isinstance(source, dict):
        return source.get(field, default)
    return getattr(source, field, default)


def _parse_date(value):
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except Exception:
        try:
            return datetime.fromisoformat(value).date()
        except Exception:
            return None


def _get_collection_docs(name: str):
    client = get_firestore_client()
    if client is None:
        return []
    coll = _user_collection(name)
    try:
        return list(coll.stream())
    except Exception:
        return []


def _parse_doc_id(doc_id: str):
    try:
        return int(doc_id)
    except Exception:
        return doc_id


def get_storage_bucket():
    if storage is None:
        return None

    client = get_firestore_client()
    if client is None:
        return None

    bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "").strip()
    try:
        return storage.bucket(bucket_name) if bucket_name else storage.bucket()
    except Exception:
        return None


def upload_csv_file(filepath: str, destination: str | None = None) -> bool:
    bucket = get_storage_bucket()
    if bucket is None:
        return False

    destination = destination or f"csv_uploads/{Path(filepath).name}"
    try:
        blob = bucket.blob(destination)
        blob.upload_from_filename(filepath, content_type="text/csv")
        return True
    except Exception:
        return False


def upload_csv_bytes(contents: bytes, destination: str) -> bool:
    bucket = get_storage_bucket()
    if bucket is None:
        return False

    try:
        blob = bucket.blob(destination)
        blob.upload_from_string(contents, content_type="text/csv")
        return True
    except Exception:
        return False


def get_firestore_transactions() -> list[dict]:
    docs = _get_collection_docs("transactions")
    results = []
    for doc in docs:
        data = doc.to_dict() or {}
        results.append({
            "id": _parse_doc_id(doc.id),
            "date": _parse_date(data.get("date")),
            "amount": float(data.get("amount", 0) or 0),
            "category": data.get("category", ""),
            "description": data.get("description", ""),
            "type": data.get("type", ""),
            "source": data.get("source", ""),
        })
    return results


def get_firestore_budget_plans() -> list[dict]:
    docs = _get_collection_docs("budget_plans")
    results = []
    for doc in docs:
        data = doc.to_dict() or {}
        results.append({
            "id": _parse_doc_id(doc.id),
            "year": int(data.get("year", 0) or 0),
            "month": int(data.get("month", 0) or 0),
            "category": data.get("category", ""),
            "limit_amount": float(data.get("limit_amount", 0) or 0),
        })
    return results


def get_firestore_savings_goals() -> list[dict]:
    docs = _get_collection_docs("savings_goals")
    results = []
    for doc in docs:
        data = doc.to_dict() or {}
        results.append({
            "id": _parse_doc_id(doc.id),
            "name": data.get("name", ""),
            "target_amount": float(data.get("target_amount", 0) or 0),
            "current_amount": float(data.get("current_amount", 0) or 0),
            "target_date": _parse_date(data.get("target_date")),
            "is_completed": bool(data.get("is_completed", False)),
        })
    return results


def sync_transaction(tx) -> bool:
    try:
        doc = {
            "date": _format_date(_get_field(tx, "date")),
            "amount": float(_get_field(tx, "amount", 0) or 0),
            "category": _get_field(tx, "category", ""),
            "description": _get_field(tx, "description", "") or "",
            "type": _get_field(tx, "type", ""),
            "source": _get_field(tx, "source", ""),
        }
        _user_collection("transactions").document(str(_get_field(tx, "id", ""))).set(doc)
        return True
    except Exception:
        return False


def delete_transaction(tx_id: int) -> bool:
    try:
        _user_collection("transactions").document(str(tx_id)).delete()
        return True
    except Exception:
        return False


def delete_budget_plan(plan_id) -> bool:
    try:
        _user_collection("budget_plans").document(str(plan_id)).delete()
        return True
    except Exception:
        return False


def delete_savings_goal(goal_id) -> bool:
    try:
        _user_collection("savings_goals").document(str(goal_id)).delete()
        return True
    except Exception:
        return False


def sync_budget_plan(plan) -> bool:
    try:
        doc = {
            "year": int(_get_field(plan, "year", 0) or 0),
            "month": int(_get_field(plan, "month", 0) or 0),
            "category": _get_field(plan, "category", ""),
            "limit_amount": float(_get_field(plan, "limit_amount", 0) or 0),
        }
        _user_collection("budget_plans").document(str(_get_field(plan, "id", ""))).set(doc)
        return True
    except Exception:
        return False


def sync_savings_goal(goal) -> bool:
    try:
        doc = {
            "name": _get_field(goal, "name", ""),
            "target_amount": float(_get_field(goal, "target_amount", 0) or 0),
            "current_amount": float(_get_field(goal, "current_amount", 0) or 0),
            "target_date": _format_date(_get_field(goal, "target_date")),
            "is_completed": bool(_get_field(goal, "is_completed", False)),
        }
        _user_collection("savings_goals").document(str(_get_field(goal, "id", ""))).set(doc)
        return True
    except Exception:
        return False
