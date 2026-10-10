import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.filesystem import safe_path

from agent.memory_embedding import MemoryEmbeddingModel

MEMORY_FILE_PATH = "organizer/memory.json"

DEFAULT_MEMORY_STRUCTURE: Dict[str, Any] = {
    "user_profile": {},
    "preferences": {},
    "project_context": {},
    "learned_facts": {},
}

embedding_model = MemoryEmbeddingModel()

def _get_memory_file() -> Path:
    """Ensure the memory file exists and return its safe path."""
    path = safe_path(MEMORY_FILE_PATH)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(DEFAULT_MEMORY_STRUCTURE, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _read_memory() -> Dict[str, Any]:
    """Read the persistent memory JSON file."""
    file_path = _get_memory_file()
    try:
        content = file_path.read_text(encoding="utf-8")
        data = json.loads(content) # json -> Py dict
        if not isinstance(data, dict):
            return DEFAULT_MEMORY_STRUCTURE.copy()
        return data
    except (json.JSONDecodeError, OSError):
        return DEFAULT_MEMORY_STRUCTURE.copy()


def _write_memory(data: Dict[str, Any]) -> None:
    """Write data to the persistent memory JSON file."""
    file_path = _get_memory_file()
    file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def save_memory(
    category: str,
    key: str,
    value: str,
    tags: Optional[List[str]] = None,
) -> dict:
    """
    Save or update a persistent long-term memory entry.

    Categories typically include:
    - 'user_profile' (e.g. name, role, location, timezone)
    - 'preferences' (e.g. currency, formatting style, favorite tools)
    - 'project_context' (e.g. project goals, tech stack, conventions)
    - 'learned_facts' (e.g. specific user notes or constraints)
    """
    if not category or not key or value is None:
        return {
            "success": False,
            "error": "category, key, and value must be non-empty strings.",
        }

    category = category.strip().lower()
    key = key.strip()

    data = _read_memory()
    if category not in data or not isinstance(data[category], dict):
        data[category] = {}

    entry = {
        "value": value,
        "tags": tags or [],
        "updated_at": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
    }

    data[category][key] = entry
    _write_memory(data)

    searchable_text = (
        f"{category} {key} {value} "
        f"{' '.join(str(tag) for tag in (tags or []))}"
    )

    embedding = embedding_model.encode(searchable_text)

    embedding_model.save_embedding(
        category,
        key,
        embedding,
    )

    return {
        "success": True,
        "message": f"Successfully saved memory under category '{category}' with key '{key}'.",
        "entry": entry,
    }


def get_memories(
    category: Optional[str] = None,
    query: Optional[str] = None,
) -> dict:
    """
    Retrieve persistent memories, optionally filtered by category or keyword search.
    """
    data = _read_memory()

    if category:
        category_clean = category.strip().lower()
        if category_clean not in data:
            return {
                "success": True,
                "category": category,
                "memories": {},
                "message": f"No category named '{category}' found.",
            }
        filtered = {category_clean: data[category_clean]}
    else:
        filtered = data

    if query:
        query_lower = query.strip().lower()
        search_results = {}
        for cat, entries in filtered.items():
            if not isinstance(entries, dict):
                continue
            matched = {}
            for k, val in entries.items():
                val_text = str(val.get("value", val) if isinstance(val, dict) else val)
                tags = val.get("tags", []) if isinstance(val, dict) else []
                if (
                    query_lower in k.lower()
                    or query_lower in val_text.lower()
                    or any(query_lower in str(t).lower() for t in tags)
                ):
                    matched[k] = val
            if matched:
                search_results[cat] = matched
        return {
            "success": True,
            "query": query,
            "memories": search_results,
        }

    return {
        "success": True,
        "memories": filtered,
    }


def delete_memory(category: str, key: str) -> dict:
    """
    Delete a specific memory entry from long-term memory.
    """
    if not category or not key:
        return {
            "success": False,
            "error": "category and key are required.",
        }

    category_clean = category.strip().lower()
    key_clean = key.strip()

    data = _read_memory()
    if category_clean not in data or not isinstance(data[category_clean], dict):
        return {
            "success": False,
            "error": f"Category '{category}' does not exist.",
        }

    if key_clean not in data[category_clean]:
        return {
            "success": False,
            "error": f"Key '{key}' not found in category '{category}'.",
        }

    del data[category_clean][key_clean]
    _write_memory(data)

    return {
        "success": True,
        "message": f"Successfully deleted memory '{key}' from category '{category}'.",
    }


def load_all_memories_formatted() -> str:
    """
    Format all existing non-empty memories into a concise text block for system prompt injection.
    """
    data = _read_memory()
    lines = []

    for category, entries in data.items():
        if not isinstance(entries, dict) or not entries:
            continue

        cat_title = category.replace("_", " ").title()
        lines.append(f"[{cat_title}]")
        for key, entry in entries.items():
            if isinstance(entry, dict) and "value" in entry:
                lines.append(f"- {key}: {entry['value']}")
            else:
                lines.append(f"- {key}: {entry}")

    if not lines:
        return ""

    return "\n".join(lines)
