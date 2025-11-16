#!/usr/bin/env python3
"""
Terminal Task Manager (OOP)
Save as task_manager.py and run: python task_manager.py
"""
import json
from datetime import datetime, date, timedelta
from typing import List, Optional


DATE_FORMAT = "%Y-%m-%d"  # ISO format for due dates


class Task:
    VALID_PRIORITIES = ("Low", "Medium", "High")
    VALID_STATUSES = ("Pending", "Completed")

    def __init__(self, id: int, title: str, priority: str, due_date: date, status: str = "Pending"):
        self.id = id
        self.title = title.strip()
        self.priority = priority
        self.due_date = due_date
        self.status = status

    def to_dict(self) -> dict:
        """Convert Task to JSON-serializable dict."""
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority,
            "due_date": self.due_date.strftime(DATE_FORMAT),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create Task instance from dict loaded from JSON."""
        due_date = datetime.strptime(data["due_date"], DATE_FORMAT).date()
        return cls(
            id=int(data["id"]),
            title=data["title"],
            priority=data["priority"],
            due_date=due_date,
            status=data.get("status", "Pending"),
        )

    def __repr__(self):
        return f"<Task {self.id}: {self.title} ({self.priority}) due {self.due_date} [{self.status}]>"


class TaskManager:
    def __init__(self, filename: str = "tasks.json"):
        self.task_list: List[Task] = []
        self.filename = filename
        self._next_id = 1
        self.load_from_file()

    # ---------- ID handling ----------
    def _generate_id(self) -> int:
        id_ = self._next_id
        self._next_id += 1
        return id_

    def _recompute_next_id(self):
        if not self.task_list:
            self._next_id = 1
        else:
            self._next_id = max(task.id for task in self.task_list) + 1

    # ---------- CRUD ----------
    def add_task(self, title: str, priority: str, due_date: date) -> Task:
        priority = priority.title()
        if priority not in Task.VALID_PRIORITIES:
            raise ValueError(f"Priority must be one of {Task.VALID_PRIORITIES}")
        new_task = Task(self._generate_id(), title, priority, due_date)
        self.task_list.append(new_task)
        self.save_to_file()
        return new_task

    def view_tasks(self, tasks: Optional[List[Task]] = None):
        """Display tasks in a formatted table. If tasks is None, display all."""
        tasks_to_show = tasks if tasks is not None else list(self.task_list)
        if not tasks_to_show:
            print("\nNo tasks to show.\n")
            return

        # Sort by due date then priority then id
        def sort_key(t: Task):
            prio_map = {"High": 0, "Medium": 1, "Low": 2}
            return (t.due_date, prio_map.get(t.priority, 3), t.id)

        tasks_to_show = sorted(tasks_to_show, key=sort_key)

        # Prepare table
        headers = ["ID", "Title", "Priority", "Due Date", "Status"]
        col_widths = [4, 40, 8, 12, 10]  # approximate widths

        line = "-" * (sum(col_widths) + len(col_widths) * 3)
        print(line)
        print(
            f"| {headers[0]:<{col_widths[0]}} | {headers[1]:<{col_widths[1]}} | "
            f"{headers[2]:<{col_widths[2]}} | {headers[3]:<{col_widths[3]}} | {headers[4]:<{col_widths[4]}} |"
        )
        print(line)
        for t in tasks_to_show:
            title = (t.title[: (col_widths[1] - 3)] + "...") if len(t.title) > col_widths[1] else t.title
            print(
                f"| {t.id:<{col_widths[0]}} | {title:<{col_widths[1]}} | "
                f"{t.priority:<{col_widths[2]}} | {t.due_date.strftime(DATE_FORMAT):<{col_widths[3]}} | "
                f"{t.status:<{col_widths[4]}} |"
            )
        print(line)
        print()

    def find_task_by_id(self, task_id: int) -> Optional[Task]:
        for t in self.task_list:
            if t.id == task_id:
                return t
        return None

    def update_task(self, task_id: int, title: Optional[str] = None, priority: Optional[str] = None,
                    due_date: Optional[date] = None, status: Optional[str] = None) -> bool:
        task = self.find_task_by_id(task_id)
        if not task:
            return False
        if title is not None:
            task.title = title.strip()
        if priority is not None:
            priority = priority.title()
            if priority not in Task.VALID_PRIORITIES:
                raise ValueError(f"Priority must be one of {Task.VALID_PRIORITIES}")
            task.priority = priority
        if due_date is not None:
            task.due_date = due_date
        if status is not None:
            status = status.title()
            if status not in Task.VALID_STATUSES:
                raise ValueError(f"Status must be one of {Task.VALID_STATUSES}")
            task.status = status
        self.save_to_file()
        return True

    def mark_complete(self, task_id: int) -> bool:
        return self.update_task(task_id, status="Completed")

    def delete_task(self, task_id: int) -> bool:
        task = self.find_task_by_id(task_id)
        if not task:
            return False
        self.task_list.remove(task)
        self.save_to_file()
        self._recompute_next_id()
        return True

    # ---------- Filtering ----------
    def filter_tasks(self, by: str = "status", value: Optional[str] = None) -> List[Task]:
        """
        by: 'status' or 'due_date'
        If by == 'status', value should be 'Pending' or 'Completed' (case-insensitive).
        If by == 'due_date', value should be 'today' or 'week' (case-insensitive).
        """
        by = by.lower()
        if by == "status":
            if not value:
                return []
            val = value.title()
            return [t for t in self.task_list if t.status == val]
        elif by == "due_date":
            if not value:
                return []
            val = value.lower()
            today = date.today()
            if val == "today":
                return [t for t in self.task_list if t.due_date == today]
            elif val == "week":
                week_end = today + timedelta(days=7)
                return [t for t in self.task_list if today <= t.due_date <= week_end]
            else:
                # support filtering by specific date string YYYY-MM-DD
                try:
                    specific = datetime.strptime(value, DATE_FORMAT).date()
                    return [t for t in self.task_list if t.due_date == specific]
                except Exception:
                    return []
        else:
            return []

    # ---------- File I/O ----------
    def save_to_file(self):
        try:
            data = [t.to_dict() for t in self.task_list]
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving tasks: {e}")

    def load_from_file(self):
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.task_list = [Task.from_dict(item) for item in data]
            self._recompute_next_id()
        except FileNotFoundError:
            # no file yet; start empty
            self.task_list = []
            self._next_id = 1
        except json.JSONDecodeError:
            print("Warning: tasks.json is corrupted. Starting with an empty task list.")
            self.task_list = []
            self._next_id = 1
        except Exception as e:
            print(f"Error loading tasks: {e}")
            self.task_list = []
            self._next_id = 1


# ---------- Helper functions for CLI ----------
def parse_date_input(s: str) -> Optional[date]:
    s = s.strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, DATE_FORMAT).date()
    except ValueError:
        print(f"Invalid date format. Please use {DATE_FORMAT} (e.g. 2025-11-14).")
        return None


def input_non_empty(prompt: str) -> str:
    while True:
        val = input(prompt).strip()
        if val:
            return val
        print("Input cannot be empty.")


def choose_priority(prompt: str = "Priority (Low/Medium/High): ") -> str:
    while True:
        p = input(prompt).strip().title()
        if p in Task.VALID_PRIORITIES:
            return p
        print("Invalid priority. Choose from Low, Medium, High.")


def input_date(prompt: str = f"Due date ({DATE_FORMAT}): ") -> date:
    while True:
        s = input(prompt).strip()
        d = parse_date_input(s)
        if d is not None:
            return d


def input_int(prompt: str) -> int:
    while True:
        s = input(prompt).strip()
        if s.isdigit():
            return int(s)
        print("Please enter a valid integer.")


def main_menu():
    print("=== Terminal Task Manager ===")
    print("1) Add Task")
    print("2) View Tasks")
    print("3) Update Task")
    print("4) Mark Task as Complete")
    print("5) Delete Task")
    print("6) Save Tasks")
    print("7) Load Tasks")
    print("0) Exit")
    print("============================")


def view_menu():
    print("View options:")
    print("1) View All")
    print("2) Filter by Status (Pending/Completed)")
    print("3) Filter by Due Date (Today / This Week / Specific Date)")
    print("0) Back")


def run_cli():
    tm = TaskManager()
    while True:
        main_menu()
        choice = input("Choose an option: ").strip()
        if choice == "1":
            print("\n--- Add Task ---")
            title = input_non_empty("Title: ")
            priority = choose_priority()
            due = input_date()
            task = tm.add_task(title, priority, due)
            print(f"Task added: {task}\n")

        elif choice == "2":
            print("\n--- View Tasks ---")
            view_menu()
            sub = input("Choose view option: ").strip()
            if sub == "1":
                tm.view_tasks()
            elif sub == "2":
                status = input("Enter status (Pending/Completed): ").strip().title()
                tasks = tm.filter_tasks(by="status", value=status)
                tm.view_tasks(tasks)
            elif sub == "3":
                print("a) Today\nb) This Week\nc) Specific Date (YYYY-MM-DD)")
                opt = input("Choose: ").strip().lower()
                if opt == "a":
                    tasks = tm.filter_tasks(by="due_date", value="today")
                    tm.view_tasks(tasks)
                elif opt == "b":
                    tasks = tm.filter_tasks(by="due_date", value="week")
                    tm.view_tasks(tasks)
                elif opt == "c":
                    s = input("Enter date (YYYY-MM-DD): ").strip()
                    tasks = tm.filter_tasks(by="due_date", value=s)
                    tm.view_tasks(tasks)
                else:
                    print("Unknown option.\n")
            elif sub == "0":
                pass
            else:
                print("Unknown option.\n")

        elif choice == "3":
            print("\n--- Update Task ---")
            tid = input_int("Enter task ID to update: ")
            task = tm.find_task_by_id(tid)
            if not task:
                print("Task not found.\n")
                continue
            print("Leave a field empty to keep current value.")
            print(f"Current title: {task.title}")
            new_title = input("New title: ").strip()
            print(f"Current priority: {task.priority}")
            new_priority = input("New priority (Low/Medium/High): ").strip()
            print(f"Current due date: {task.due_date.strftime(DATE_FORMAT)}")
            new_due = input("New due date (YYYY-MM-DD): ").strip()
            print(f"Current status: {task.status}")
            new_status = input("New status (Pending/Completed): ").strip()

            kwargs = {}
            if new_title:
                kwargs["title"] = new_title
            if new_priority:
                kwargs["priority"] = new_priority
            if new_due:
                parsed = parse_date_input(new_due)
                if parsed is None:
                    print("Aborting update due to invalid date.\n")
                    continue
                kwargs["due_date"] = parsed
            if new_status:
                kwargs["status"] = new_status

            try:
                updated = tm.update_task(tid, **kwargs)
                if updated:
                    print("Task updated.\n")
                else:
                    print("Failed to update task.\n")
            except ValueError as e:
                print(f"Update error: {e}\n")

        elif choice == "4":
            print("\n--- Mark Task as Complete ---")
            tid = input_int("Enter task ID to mark complete: ")
            if tm.mark_complete(tid):
                print("Task marked as Completed.\n")
            else:
                print("Task not found.\n")

        elif choice == "5":
            print("\n--- Delete Task ---")
            tid = input_int("Enter task ID to delete: ")
            task = tm.find_task_by_id(tid)
            if not task:
                print("Task not found.\n")
                continue
            confirm = input(f"Are you sure you want to delete task {tid} ('{task.title}')? (y/N): ").strip().lower()
            if confirm == "y":
                if tm.delete_task(tid):
                    print("Task deleted.\n")
                else:
                    print("Could not delete task.\n")
            else:
                print("Delete cancelled.\n")

        elif choice == "6":
            tm.save_to_file()
            print("Saved to file.\n")

        elif choice == "7":
            tm.load_from_file()
            print("Loaded tasks from file.\n")

        elif choice == "0":
            print("Exiting. Goodbye!")
            break

        else:
            print("Invalid option. Choose again.\n")


if __name__ == "__main__":
    run_cli()
