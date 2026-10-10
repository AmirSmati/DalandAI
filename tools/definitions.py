TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "List files and directories inside the allowed workspace. "
                "Use this to navigate the workspace."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Relative directory path inside the workspace. "
                            "Use '.' for the workspace root."
                        ),
                    }
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the contents of a UTF-8 text file inside the workspace."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Relative file path inside the workspace."
                        ),
                    }
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": "Create a folder inside the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path of the folder to create, relative to the workspace."
                    }
                },
                "required": ["path"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create a file inside the workspace with the given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path of the file to create, relative to the workspace."
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write into the file. If omitted, the file will be empty."
                    }
                },
                "required": ["path"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_file",
            "description": "Replace the contents of an existing UTF-8 text file inside the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path of the existing file to update, relative to the workspace."
                    },
                    "content": {
                        "type": "string",
                        "description": "The new content that will completely replace the existing file contents."
                    }
                },
                "required": ["path", "content"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for text inside UTF-8 files in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The text to search for inside files. The search is case-insensitive."
                    },
                    "path": {
                        "type": "string",
                        "description": "The directory to search in, relative to the workspace. Defaults to the workspace root."
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_and_classify_document",
            "description": (
                "Extract text from a workspace text file, image, or PDF; classify it "
                "using keyword rules; and save the result as CSV, with optional XLSX."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source_path": {
                        "type": "string",
                        "description": "Relative workspace path of the source document."
                    },
                    "csv_output_path": {
                        "type": "string",
                        "description": "Relative .csv output path. Defaults to classified_documents.csv."
                    },
                    "xlsx_output_path": {
                        "type": "string",
                        "description": "Optional relative .xlsx output path."
                    },
                    "classification_rules": {
                        "type": "object",
                        "description": "Categories mapped to keyword lists, for example {\"invoice\": [\"invoice\", \"total\"]}.",
                        "additionalProperties": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "default_category": {
                        "type": "string",
                        "description": "Category to use when no keywords match. Defaults to unclassified."
                    }
                },
                "required": ["source_path"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_and_classify_folder",
            "description": (
                "Classify every supported document in one workspace folder and "
                "write a single CSV report, with optional XLSX output. Unsupported "
                "files and individual failures do not stop the batch."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source_directory": {
                        "type": "string",
                        "description": "Relative workspace folder containing documents to classify."
                    },
                    "csv_output_path": {
                        "type": "string",
                        "description": "Relative .csv report path. Defaults to results/classification_report.csv."
                    },
                    "xlsx_output_path": {
                        "type": "string",
                        "description": "Optional relative .xlsx report path."
                    },
                    "classification_rules": {
                        "type": "object",
                        "description": "Categories mapped to keyword lists.",
                        "additionalProperties": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "default_category": {
                        "type": "string",
                        "description": "Category used when no keywords match. Defaults to unclassified."
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Also process documents in subfolders. Defaults to false."
                    },
                    "max_files": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Maximum supported files to process. Defaults to 50."
                    }
                },
                "required": ["source_directory"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": (
                "Save or update a persistent long-term memory entry (e.g. user preferences, "
                "profile details, recurring constraints, or project context) stored across sessions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": (
                            "Memory category, e.g. 'user_profile', 'preferences', "
                            "'project_context', or 'learned_facts'."
                        ),
                    },
                    "key": {
                        "type": "string",
                        "description": "Unique key or topic for this memory entry (e.g. 'currency', 'preferred_format')."
                    },
                    "value": {
                        "type": "string",
                        "description": "The specific information or fact to remember."
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of tags or keywords for easier search."
                    }
                },
                "required": ["category", "key", "value"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_memories",
            "description": "Retrieve stored persistent long-term memories, with optional category or query filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional category filter (e.g. 'preferences', 'user_profile')."
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional search term to find specific memories."
                    }
                },
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_memory",
            "description": "Delete an obsolete or incorrect persistent long-term memory entry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category containing the memory to delete."
                    },
                    "key": {
                        "type": "string",
                        "description": "Key of the memory entry to delete."
                    }
                },
                "required": ["category", "key"],
                "additionalProperties": False
            }
        }
    }
]

    #ScheduelerTool - Agent Deeper Think
SCHEDULE_FOLLOWUP_TOOL = {
    "type": "function",
    "function": {
        "name": "schedule_followup",
        "description": (
            "Schedule another agent task to be executed after the current "
            "task. Use this when additional work should be performed later "
            "as a separate task."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task that should be executed later.",
                }
            },
            "required": ["task"],
        },
    },
}


# Sub agents
DELEGATE_TO_SUBAGENT_TOOL = {
    "type": "function",
    "function": {
        "name": "delegate_to_subagent",
        "description": (
            "Delegate a task to a specialized sub-agent. "
            "Use this tool when the task matches one of the delegation "
            "rules defined in the system instructions, such as web research, "
            "document processing, code/project analysis, or organization "
            "and task management. For requests involving multiple independent "
            "task categories, delegate each applicable category to the "
            "corresponding specialist. The sub-agent executes through the "
            "same Harness and returns its result to the main agent, which "
            "must incorporate the result into the final response."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The specific task the sub-agent should perform.",
                },
                "role": {
                    "type": "string",
                    "description": (
                        "The specialized role of the sub-agent, "
                        "for example 'Web research specialist'."
                    ),
                },
                "instructions": {
                    "type": "string",
                    "description": (
                        "Specific instructions and constraints for the sub-agent."
                    ),
                },
                "context": {
                    "type": "string",
                    "description": (
                        "Relevant context the sub-agent needs to complete the task."
                    ),
                },
                "max_tool_calls": {
                    "type": "integer",
                    "minimum": 1,
                    "description": (
                        "Maximum number of tool calls the sub-agent may perform."
                    ),
                },
            },
            "required": [
                "task",
                "role",
                "instructions",
            ],
            "additionalProperties": False,
        },
    },
}