from agent.memory_embedding import MemoryEmbeddingModel
from tools.memory import _read_memory


def main():
    embedding_model = MemoryEmbeddingModel()
    memories = _read_memory()

    created = 0
    skipped = 0

    for category, entries in memories.items():
        if not isinstance(entries, dict):
            continue

        for key, memory in entries.items():

            # Check whether an embedding already exists.
            existing = embedding_model.load_embedding(
                category,
                key,
            )

            if existing is not None:
                skipped += 1
                continue

            # Get the memory information.
            if isinstance(memory, dict):
                value = memory.get("value", "")
                tags = memory.get("tags", [])
            else:
                value = str(memory)
                tags = []

            # Build the same text used by save_memory().
            searchable_text = (
                f"{category} {key} {value} "
                f"{' '.join(str(tag) for tag in tags)}"
            )

            # Generate the embedding.
            embedding = embedding_model.encode(searchable_text)

            # Save it.
            embedding_model.save_embedding(
                category,
                key,
                embedding,
            )

            print(
                f"[BACKFILL] Created embedding for "
                f"{category}/{key}"
            )

            created += 1

    print("\n[BACKFILL] Complete")
    print(f"[BACKFILL] Created: {created}")
    print(f"[BACKFILL] Already existed: {skipped}")


if __name__ == "__main__":
    main()