from tools.filesystem import (
    list_files,
    read_file,
    create_folder,
    create_file,
    update_file,
    search_files,
)
from tools.ocr_classifier import (
    extract_and_classify_document,
    extract_and_classify_folder,
)
from tools.memory import (
    save_memory,
    get_memories,
    delete_memory,
)
from tools.ocr_classifier import (
    extract_and_classify_document,
)


TOOL_REGISTRY = {
    "list_files": list_files,
    "read_file": read_file,
    "create_folder": create_folder,
    "create_file": create_file,
    "search_files" : search_files,
    "update_file" : update_file,
    "extract_and_classify_document": extract_and_classify_document,
    "extract_and_classify_folder": extract_and_classify_folder,
    "save_memory": save_memory,
    "get_memories": get_memories,
    "delete_memory": delete_memory,
}
