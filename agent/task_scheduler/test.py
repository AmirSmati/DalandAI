from scheduler import TaskScheduler


scheduler = TaskScheduler()

print(scheduler.add_task("Task A"))
print(scheduler.add_task("Task B"))
print(scheduler.add_task("Task C"))

print("Queue size:", scheduler.size())

print("Next:", scheduler.get_next_task())
print("Next:", scheduler.get_next_task())
print("Next:", scheduler.get_next_task())
print("Next:", scheduler.get_next_task())

print("Has tasks:", scheduler.has_tasks())