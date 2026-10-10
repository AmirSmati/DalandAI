class TaskScheduler:
    """Dependency-aware task scheduler."""

    def __init__(self):
        self._tasks = {}

    def add_task(self, task: dict) -> dict:
        """Add a structured task."""

        required = ("id", "description", "depends_on")

        #fields check for each task
        if not all(key in task for key in required):
            return {
                "success": False,
                "error": "Task must contain id, description, and depends_on.",
            }

        task_id = task["id"]

        if task_id in self._tasks:
            return {
                "success": False,
                "error": f"Duplicate task ID: {task_id}",
            }

        self._tasks[task_id] = {
            "id": task_id,
            "description": task["description"].strip(),
            "depends_on": task["depends_on"],
            "status": "pending",
            "result": None,
        }

        return {
            "success": True,
            "message": f"Task scheduled: {task_id}",
            "queue_size": len(self._tasks),
        }

    def get_ready_tasks(self) -> list[dict]:
        """Return tasks whose dependencies are completed."""

        ready = []

        for task in self._tasks.values():
            if task["status"] != "pending":
                continue

            dependencies_met = all(
                self._tasks.get(dep_id, {}).get("status") == "completed"
                for dep_id in task["depends_on"]
            )

            if dependencies_met:
                ready.append(task)

        return ready

    def mark_completed(self, task_id: str, result):
        self._tasks[task_id]["status"] = "completed"
        self._tasks[task_id]["result"] = result

    def mark_failed(self, task_id: str, result):
        self._tasks[task_id]["status"] = "failed"
        self._tasks[task_id]["result"] = result

    def has_pending_tasks(self) -> bool:
        return any(
            task["status"] == "pending"
            for task in self._tasks.values()
        )
    
    #Testing Purpose
    #TODO : Cleanup
    def has_tasks(self) -> bool:
        return self.has_pending_tasks()

    def validate_dependencies(self) -> list[str]:
        """Check whether all referenced dependencies exist."""

        errors = []

        for task in self._tasks.values():
            for dependency_id in task["depends_on"]:
                if dependency_id not in self._tasks:
                    errors.append(
                        f"Task '{task['id']}' depends on "
                        f"unknown task '{dependency_id}'"
                    )

        return errors

    def size(self) -> int:
        return sum(
            task["status"] == "pending"
            for task in self._tasks.values()
        )

    def get_task(self, task_id: str) -> dict | None:
        """Return a task by ID."""
        return self._tasks.get(task_id)
    
    def clear(self):
        self._tasks.clear()