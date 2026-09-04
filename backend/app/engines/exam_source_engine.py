import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


BASE_DIR = Path(__file__).resolve().parents[2]
EXAM_DIR = BASE_DIR / "data" / "exams"
SOURCE_FILE = EXAM_DIR / "sources.json"


def _load_json(path: Path, default: Any):
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def load_sources() -> Dict[str, Any]:
    return _load_json(SOURCE_FILE, {"sources": []})


def get_source(exam_id: str) -> Optional[Dict[str, Any]]:
    exam_id = exam_id.strip().upper()

    for source in load_sources().get("sources", []):
        if source.get("exam_id", "").upper() == exam_id:
            return source

    return None


def _canonical_profile(profile: Dict[str, Any]) -> str:
    comparable = {
        "id": profile.get("id"),
        "name": profile.get("name"),
        "version": profile.get("version"),
        "effective_from": profile.get("effective_from"),
        "syllabus": profile.get("syllabus", {}),
        "assessment": profile.get("assessment", {}),
        "question_rules": profile.get("question_rules", {})
    }

    return json.dumps(
        comparable,
        sort_keys=True,
        separators=(",", ":")
    )


def profile_fingerprint(profile: Dict[str, Any]) -> str:
    payload = _canonical_profile(profile).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def list_versions(exam_id: str):
    exam_id = exam_id.strip().upper()

    versions = []

    for path in EXAM_DIR.glob(f"{exam_id}__*.json"):
        profile = _load_json(path, {})
        if profile:
            versions.append({
                "version": profile.get("version"),
                "file": path.name,
                "fingerprint": profile_fingerprint(profile),
                "effective_from": profile.get("effective_from")
            })

    versions.sort(key=lambda x: str(x.get("version", "")))

    return versions


def latest_version(exam_id: str):
    versions = list_versions(exam_id)
    return versions[-1] if versions else None


def compare_with_latest(profile: Dict[str, Any]):
    exam_id = str(profile.get("id", "")).strip().upper()

    if not exam_id:
        raise ValueError("Exam profile requires an id")

    latest = latest_version(exam_id)

    if not latest:
        return {
            "status": "new_exam",
            "exam_id": exam_id,
            "changed": True,
            "latest_version": None,
            "new_fingerprint": profile_fingerprint(profile)
        }

    latest_path = EXAM_DIR / latest["file"]
    latest_profile = _load_json(latest_path, {})

    old_fp = profile_fingerprint(latest_profile)
    new_fp = profile_fingerprint(profile)

    return {
        "status": "changed" if old_fp != new_fp else "unchanged",
        "exam_id": exam_id,
        "changed": old_fp != new_fp,
        "latest_version": latest_profile.get("version"),
        "new_version": profile.get("version"),
        "old_fingerprint": old_fp,
        "new_fingerprint": new_fp
    }


def register_versioned_profile(
    profile: Dict[str, Any],
    source_metadata: Optional[Dict[str, Any]] = None
):
    exam_id = str(profile.get("id", "")).strip().upper()

    if not exam_id:
        raise ValueError("Exam profile requires an id")

    version = str(profile.get("version", "")).strip()

    if not version:
        raise ValueError("Exam profile requires a version")

    profile = dict(profile)

    profile["id"] = exam_id
    profile.setdefault(
        "retrieved_at",
        datetime.utcnow().isoformat(timespec="seconds") + "Z"
    )

    if source_metadata:
        profile["source"] = source_metadata

    comparison = compare_with_latest(profile)

    filename = f"{exam_id}__{version}.json"
    path = EXAM_DIR / filename

    path.write_text(
        json.dumps(profile, indent=2, ensure_ascii=False)
    )

    return {
        "status": "registered",
        "changed": comparison["changed"],
        "exam_id": exam_id,
        "version": version,
        "file": filename,
        "fingerprint": profile_fingerprint(profile),
        "comparison": comparison
    }
