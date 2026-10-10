"""Extract text from workspace documents and classify it by keyword rules."""

import csv
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from tools.filesystem import safe_path


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
TEXT_EXTENSIONS = {".txt", ".md", ".py", ".json", ".yaml", ".yml", ".csv"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | TEXT_EXTENSIONS | {".pdf"}
REPORT_FIELDS = [
    "source_path",
    "status",
    "category",
    "score",
    "matched_keywords",
    "extracted_text",
    "error",
]


def _missing_dependency(package_name: str, install_hint: str) -> RuntimeError:
    return RuntimeError(
        f"{package_name} is required for this file type. {install_hint}"
    )


def _read_text_file(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")


def _read_image_with_ocr(file_path: Path) -> str:
    try:
        from PIL import Image
    except ImportError as exc:
        raise _missing_dependency(
            "Pillow",
            "Install dependencies with: pip install -r requirements.txt",
        ) from exc

    try:
        import pytesseract
    except ImportError as exc:
        raise _missing_dependency(
            "pytesseract",
            "Install dependencies with: pip install -r requirements.txt",
        ) from exc

    try:
        with Image.open(file_path) as image:
            return pytesseract.image_to_string(image).strip()
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract OCR is not installed or is not available on PATH. "
            "Install Tesseract, then restart the terminal."
        ) from exc


def _read_pdf(file_path: Path) -> str:
    text = ""

    try:
        from pypdf import PdfReader
    except ImportError:
        PdfReader = None

    if PdfReader is not None:
        reader = PdfReader(str(file_path))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(page.strip() for page in pages if page.strip())

    if text.strip():
        return text.strip()

    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError as exc:
        raise _missing_dependency(
            "pypdf or pdf2image with pytesseract",
            "Install dependencies with: pip install -r requirements.txt",
        ) from exc

    extracted_pages = []
    for page_image in convert_from_path(str(file_path)):
        extracted_pages.append(pytesseract.image_to_string(page_image))

    return "\n".join(extracted_pages).strip()


def extract_text(path: str) -> dict:
    """
    Extract text from a workspace file.

    Text files are read directly. Images use OCR. PDFs use embedded text first
    and fall back to OCR when possible.
    """
    try:
        file_path = safe_path(path)
    except PermissionError as exc:
        return {
            "success": False,
            "error": str(exc),
        }

    if not file_path.exists():
        return {
            "success": False,
            "error": f"File does not exist: {path}",
        }

    if not file_path.is_file():
        return {
            "success": False,
            "error": f"Not a file: {path}",
        }

    extension = file_path.suffix.lower()

    try:
        if extension in TEXT_EXTENSIONS:
            text = _read_text_file(file_path)
        elif extension in IMAGE_EXTENSIONS:
            text = _read_image_with_ocr(file_path)
        elif extension == ".pdf":
            text = _read_pdf(file_path)
        else:
            supported_types = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            return {
                "success": False,
                "error": (
                    f"Unsupported file type: {extension or 'unknown'}. "
                    f"Supported types: {supported_types}"
                ),
            }
    except UnicodeDecodeError:
        return {
            "success": False,
            "error": "File is not valid UTF-8 text.",
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }

    return {
        "success": True,
        "path": path,
        "text": text,
        "characters": len(text),
    }


def _keyword_score(text: str, keywords: Iterable[str]) -> int:
    lower_text = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in lower_text)


def classify_text(
    text: str,
    classification_rules: Optional[Dict[str, List[str]]] = None,
    default_category: str = "unclassified",
) -> dict:
    """
    Classify text using user-defined keyword rules.

    Example rules:
    {
        "invoice": ["invoice", "total", "vat"],
        "resume": ["experience", "education", "skills"]
    }
    """
    if not classification_rules:
        return {
            "category": default_category,
            "score": 0,
            "matched_keywords": [],
        }

    best_category = default_category
    best_score = 0
    best_keywords: List[str] = []

    for category, keywords in classification_rules.items():
        if not isinstance(category, str) or not isinstance(keywords, list):
            continue

        valid_keywords = [
            keyword for keyword in keywords if isinstance(keyword, str)
        ]
        score = _keyword_score(text, valid_keywords)
        if score > best_score:
            best_category = category
            best_score = score
            lower_text = text.lower()
            best_keywords = [
                keyword for keyword in valid_keywords
                if keyword.lower() in lower_text
            ]

    return {
        "category": best_category,
        "score": best_score,
        "matched_keywords": best_keywords,
    }


def _classify_document(
    source_path: str,
    classification_rules: Optional[Dict[str, List[str]]],
    default_category: str,
) -> dict:
    """Extract and classify one document without writing an output file."""
    extracted = extract_text(source_path)
    if not extracted["success"]:
        return {
            "success": False,
            "error": extracted["error"],
            "row": {
                "source_path": source_path,
                "status": "failed",
                "category": "",
                "score": "",
                "matched_keywords": "",
                "extracted_text": "",
                "error": extracted["error"],
            },
        }

    text = extracted["text"]
    classification = classify_text(
        text=text,
        classification_rules=classification_rules,
        default_category=default_category,
    )

    return {
        "success": True,
        "classification": classification,
        "characters": len(text),
        "row": {
            "source_path": source_path,
            "status": "success",
            "category": classification["category"],
            "score": classification["score"],
            "matched_keywords": ", ".join(classification["matched_keywords"]),
            "extracted_text": text,
            "error": "",
        },
    }


def _prepare_output_path(relative_path: str, extension: str) -> Path:
    output_path = safe_path(relative_path)

    if output_path.suffix.lower() != extension:
        raise ValueError(f"Output path must end in {extension}.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def _write_csv(output_path: Path, rows: List[dict]) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_xlsx(output_path: Path, rows: List[dict]) -> None:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise _missing_dependency(
            "openpyxl",
            "Install dependencies with: pip install -r requirements.txt",
        ) from exc

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "classified_documents"

    sheet.append(REPORT_FIELDS)

    for row in rows:
        sheet.append([row[header] for header in REPORT_FIELDS])

    workbook.save(output_path)


def extract_and_classify_document(
    source_path: str,
    csv_output_path: str = "classified_documents.csv",
    xlsx_output_path: Optional[str] = None,
    classification_rules: Optional[Dict[str, List[str]]] = None,
    default_category: str = "unclassified",
) -> dict:
    """
    Extract text from a file, classify it, and save the result as CSV/XLSX.
    """
    processed = _classify_document(
        source_path=source_path,
        classification_rules=classification_rules,
        default_category=default_category,
    )
    if not processed["success"]:
        return {
            "success": False,
            "error": processed["error"],
        }

    try:
        csv_path = _prepare_output_path(csv_output_path, ".csv")
        _write_csv(csv_path, [processed["row"]])

        written_files = [csv_path.relative_to(safe_path(".")).as_posix()]

        if xlsx_output_path:
            xlsx_path = _prepare_output_path(xlsx_output_path, ".xlsx")
            _write_xlsx(xlsx_path, [processed["row"]])
            written_files.append(xlsx_path.relative_to(safe_path(".")).as_posix())
    except (OSError, PermissionError, RuntimeError, ValueError) as exc:
        return {
            "success": False,
            "error": str(exc),
        }

    return {
        "success": True,
        "source_path": source_path,
        "category": processed["classification"]["category"],
        "score": processed["classification"]["score"],
        "matched_keywords": processed["classification"]["matched_keywords"],
        "characters": processed["characters"],
        "written_files": written_files,
    }


def extract_and_classify_folder(
    source_directory: str,
    csv_output_path: str = "results/classification_report.csv",
    xlsx_output_path: Optional[str] = None,
    classification_rules: Optional[Dict[str, List[str]]] = None,
    default_category: str = "unclassified",
    recursive: bool = False,
    max_files: int = 50,
) -> dict:
    """Classify supported files in a workspace folder into one report."""
    if max_files < 1:
        return {"success": False, "error": "max_files must be at least 1."}

    try:
        source_folder = safe_path(source_directory)
    except PermissionError as exc:
        return {"success": False, "error": str(exc)}
    if not source_folder.exists():
        return {
            "success": False,
            "error": f"Directory does not exist: {source_directory}",
        }
    if not source_folder.is_dir():
        return {
            "success": False,
            "error": f"Path is not a directory: {source_directory}",
        }

    try:
        csv_path = _prepare_output_path(csv_output_path, ".csv")
        xlsx_path = (
            _prepare_output_path(xlsx_output_path, ".xlsx")
            if xlsx_output_path
            else None
        )
    except (OSError, PermissionError, ValueError) as exc:
        return {"success": False, "error": str(exc)}

    workspace_root = safe_path(".")
    output_paths = {csv_path.resolve()}
    if xlsx_path:
        output_paths.add(xlsx_path.resolve())

    candidates = []
    skipped_files = 0
    iterator = source_folder.rglob("*") if recursive else source_folder.iterdir()
    for file_path in sorted(iterator):
        if not file_path.is_file() or file_path.resolve() in output_paths:
            continue
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            skipped_files += 1
            continue
        if len(candidates) >= max_files:
            skipped_files += 1
            continue
        candidates.append(file_path)

    rows = []
    successful_files = 0
    failed_files = 0
    for file_path in candidates:
        source_path = file_path.relative_to(workspace_root).as_posix()
        processed = _classify_document(
            source_path=source_path,
            classification_rules=classification_rules,
            default_category=default_category,
        )
        rows.append(processed["row"])

        if processed["success"]:
            successful_files += 1
        else:
            failed_files += 1

    try:
        _write_csv(csv_path, rows)
        written_files = [csv_path.relative_to(workspace_root).as_posix()]
        if xlsx_path:
            _write_xlsx(xlsx_path, rows)
            written_files.append(xlsx_path.relative_to(workspace_root).as_posix())
    except (OSError, RuntimeError) as exc:
        return {"success": False, "error": str(exc)}

    return {
        "success": True,
        "source_directory": source_directory,
        "files_processed": len(candidates),
        "successful_files": successful_files,
        "failed_files": failed_files,
        "skipped_files": skipped_files,
        "written_files": written_files,
    }
