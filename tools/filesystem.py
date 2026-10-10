from pathlib import Path

# Only this directory is accessible to the agent.
WORKSPACE = Path(__file__).resolve().parent.parent / "workspace"
WORKSPACE = WORKSPACE.resolve()


def safe_path(relative_path: str) -> Path:
    """
    Convert a user/agent path into an absolute path and make sure
    it remains inside the workspace.
    """
    path = (WORKSPACE / relative_path).resolve()

    try:
        path.relative_to(WORKSPACE)
    except ValueError:
        raise PermissionError(
            "Access denied: path is outside the workspace."
        )

    return path


def list_files(path: str = ".") -> dict:
    """
    List files and directories inside the workspace.
    """
    directory = safe_path(path)

    if not directory.exists():
        return {
            "success": False,
            "error": f"Path does not exist: {path}"
        }

    if not directory.is_dir():
        return {
            "success": False,
            "error": f"Path is not a directory: {path}"
        }

    entries = []

    for item in sorted(directory.iterdir()):
        entries.append({
            "name": item.name,
            "type": "directory" if item.is_dir() else "file"
        })

    return {
        "success": True,
        "path": path,
        "entries": entries
    }


def read_file(path: str) -> dict:
    """
    Read a UTF-8 text file inside the workspace.
    """
    file_path = safe_path(path)

    if not file_path.exists():
        return {
            "success": False,
            "error": f"File does not exist: {path}"
        }

    if not file_path.is_file():
        return {
            "success": False,
            "error": f"Not a file: {path}"
        }

    try:
        content = file_path.read_text(encoding="utf-8")

        return {
            "success": True,
            "path": path,
            "content": content
        }

    except UnicodeDecodeError:
        return {
            "success": False,
            "error": "File is not a UTF-8 text file."
        }

def create_folder(path: str) -> dict:
    """
    Create a folder inside the workspace.
    """
    folder_path = safe_path(path)

    if folder_path.exists():
        return {
            "success": False,
            "error": f"Path already exists: {path}"
        }

    try:
        folder_path.mkdir(parents=True)
        return {
            "success": True,
            "path": path,
            "absolute_path": str(folder_path)
        }

    except OSError as e:
        return {
            "success": False,
            "error": f"Could not create folder: {e}"
        }

def create_file(path: str, content: str = "") -> dict:
    """
    Create a file inside the workspace with the given content.
    Parent directories are created automatically if they do not exist.
    """
    file_path = safe_path(path)

    if file_path.exists():
        return {
            "success": False,
            "error": f"Path already exists: {path}"
        }

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "path": path,
            "absolute_path": str(file_path)
        }

    except OSError as e:
        return {
            "success": False,
            "error": f"Could not create file: {e}"
        }


def update_file(path: str, content: str) -> dict:
    """
    Replace the contents of an existing UTF-8 text file.
    """
    file_path = safe_path(path)

    if not file_path.exists():
        return {
            "success": False,
            "error": f"File does not exist: {path}"
        }

    if not file_path.is_file():
        return {
            "success": False,
            "error": f"Not a file: {path}"
        }

    try:
        file_path.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "path": path,
            "message": "File updated."
        }

    except OSError as exc:
        return {
            "success": False,
            "error": str(exc)
        }

#text inside files 
def search_files(query: str, path: str = ".") -> dict:
    """
    Search for text inside UTF-8 files in the workspace.
    """
    directory = safe_path(path)

    if not query:
        return {
            "success": False,
            "error": "Search query cannot be empty."
        }

    if not directory.exists():
        return {
            "success": False,
            "error": f"Path does not exist: {path}"
        }

    if not directory.is_dir():
        return {
            "success": False,
            "error": f"Path is not a directory: {path}"
        }

    matches = []
    max_matches = 50

    for file_path in sorted(directory.rglob("*")):
        if not file_path.is_file():
            continue

        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()

        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(lines, start=1):
            if query.lower() in line.lower():
                matches.append({
                    "path": str(file_path.relative_to(WORKSPACE)),
                    "line_number": line_number,
                    "line": line
                })

                if len(matches) >= max_matches:
                    return {
                        "success": True,
                        "query": query,
                        "matches": matches,
                        "truncated": True
                    }

    return {
        "success": True,
        "query": query,
        "matches": matches,
        "truncated": False
    }