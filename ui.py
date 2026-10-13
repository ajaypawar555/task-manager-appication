"""Simple Tkinter desktop client for the Task Manager REST API."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class TaskManagerUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Task Manager")
        self.root.geometry("1000x700")
        self.root.minsize(800, 560)

        self.base_url = tk.StringVar(value="http://127.0.0.1:8000")
        self.api_token = tk.StringVar()
        self.title_value = tk.StringVar()
        self.status_value = tk.StringVar(value="pending")
        self.priority_value = tk.StringVar(value="medium")
        self.due_date_value = tk.StringVar()
        self.filter_status = tk.StringVar(value="All")
        self.filter_priority = tk.StringVar(value="All")
        self.search_value = tk.StringVar()
        self.selected_task_id: int | None = None

        self._build_layout()
        self.refresh_tasks()

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Task Manager", font=("Segoe UI", 20, "bold")).pack(
            anchor="w", pady=(0, 10)
        )

        connection = ttk.LabelFrame(outer, text="API connection", padding=10)
        connection.pack(fill="x", pady=(0, 10))
        ttk.Label(connection, text="Base URL").grid(row=0, column=0, sticky="w")
        ttk.Entry(connection, textvariable=self.base_url, width=38).grid(
            row=0, column=1, padx=(6, 14), sticky="ew"
        )
        ttk.Label(connection, text="Bearer token (leave blank for local tokenless testing)").grid(
            row=0, column=2, sticky="w"
        )
        ttk.Entry(connection, textvariable=self.api_token, show="•", width=34).grid(
            row=0, column=3, padx=(6, 10), sticky="ew"
        )
        ttk.Button(connection, text="Refresh", command=self.refresh_tasks).grid(row=0, column=4)
        connection.columnconfigure(1, weight=1)
        connection.columnconfigure(3, weight=1)

        filters = ttk.LabelFrame(outer, text="Find tasks", padding=10)
        filters.pack(fill="x", pady=(0, 10))
        ttk.Label(filters, text="Status").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            filters,
            textvariable=self.filter_status,
            values=("All", "pending", "in_progress", "completed"),
            state="readonly",
            width=16,
        ).grid(row=0, column=1, padx=(6, 14))
        ttk.Label(filters, text="Priority").grid(row=0, column=2, sticky="w")
        ttk.Combobox(
            filters,
            textvariable=self.filter_priority,
            values=("All", "low", "medium", "high"),
            state="readonly",
            width=12,
        ).grid(row=0, column=3, padx=(6, 14))
        ttk.Label(filters, text="Title search").grid(row=0, column=4, sticky="w")
        ttk.Entry(filters, textvariable=self.search_value, width=24).grid(
            row=0, column=5, padx=(6, 8), sticky="ew"
        )
        ttk.Button(filters, text="Apply", command=self.refresh_tasks).grid(row=0, column=6)
        filters.columnconfigure(5, weight=1)

        table_frame = ttk.Frame(outer)
        table_frame.pack(fill="both", expand=True)
        columns = ("id", "title", "status", "priority", "due_date")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        headings = {
            "id": ("ID", 65),
            "title": ("Title", 350),
            "status": ("Status", 130),
            "priority": ("Priority", 100),
            "due_date": ("Due date", 190),
        }
        for key, (label, width) in headings.items():
            self.table.heading(key, text=label)
            self.table.column(key, width=width, anchor="w")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.table.bind("<<TreeviewSelect>>", self._select_task)

        editor = ttk.LabelFrame(outer, text="Task details", padding=10)
        editor.pack(fill="x", pady=(10, 0))
        ttk.Label(editor, text="Title*").grid(row=0, column=0, sticky="w")
        ttk.Entry(editor, textvariable=self.title_value).grid(
            row=0, column=1, columnspan=3, padx=(6, 14), sticky="ew"
        )
        ttk.Label(editor, text="Status").grid(row=0, column=4, sticky="w")
        ttk.Combobox(
            editor,
            textvariable=self.status_value,
            values=("pending", "in_progress", "completed"),
            state="readonly",
            width=16,
        ).grid(row=0, column=5, padx=(6, 14))
        ttk.Label(editor, text="Priority").grid(row=0, column=6, sticky="w")
        ttk.Combobox(
            editor,
            textvariable=self.priority_value,
            values=("low", "medium", "high"),
            state="readonly",
            width=12,
        ).grid(row=0, column=7, padx=(6, 0))

        ttk.Label(editor, text="Description").grid(row=1, column=0, sticky="nw", pady=(8, 0))
        self.description_box = tk.Text(editor, height=3, wrap="word")
        self.description_box.grid(
            row=1, column=1, columnspan=5, padx=(6, 14), pady=(8, 0), sticky="ew"
        )
        ttk.Label(editor, text="Due date\n(ISO 8601)").grid(
            row=1, column=6, sticky="nw", pady=(8, 0)
        )
        ttk.Entry(editor, textvariable=self.due_date_value, width=24).grid(
            row=1, column=7, padx=(6, 0), pady=(8, 0), sticky="ew"
        )

        actions = ttk.Frame(editor)
        actions.grid(row=2, column=0, columnspan=8, sticky="w", pady=(10, 0))
        ttk.Button(actions, text="Create task", command=self.create_task).pack(side="left")
        ttk.Button(actions, text="Update selected", command=self.update_task).pack(
            side="left", padx=8
        )
        ttk.Button(actions, text="Delete selected", command=self.delete_task).pack(side="left")
        ttk.Button(actions, text="Clear form", command=self.clear_form).pack(side="left", padx=8)

        editor.columnconfigure(1, weight=1)
        editor.columnconfigure(3, weight=1)
        editor.columnconfigure(5, weight=1)
        self.status_message = ttk.Label(outer, text="Ready", anchor="w")
        self.status_message.pack(fill="x", pady=(8, 0))

    def _request(self, method: str, path: str, payload: dict | None = None) -> object:
        url = self.base_url.get().strip().rstrip("/") + path
        headers = {"Accept": "application/json"}
        token = self.api_token.get().strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=15) as response:
                body = response.read()
                return json.loads(body.decode("utf-8")) if body else None
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(body).get("detail", body)
            except (json.JSONDecodeError, AttributeError):
                detail = body or error.reason
            raise RuntimeError(f"API returned {error.code}: {detail}") from error
        except URLError as error:
            raise RuntimeError(
                "Could not reach the API. Start it with 'uvicorn app.main:app --reload'."
            ) from error

    def refresh_tasks(self) -> None:
        params: dict[str, str] = {"limit": "100", "offset": "0"}
        if self.filter_status.get() != "All":
            params["status"] = self.filter_status.get()
        if self.filter_priority.get() != "All":
            params["priority"] = self.filter_priority.get()
        if self.search_value.get().strip():
            params["search"] = self.search_value.get().strip()
        try:
            tasks = self._request("GET", "/api/v1/tasks?" + urlencode(params))
        except RuntimeError as error:
            self._show_error(str(error))
            return
        for item in self.table.get_children():
            self.table.delete(item)
        for task in tasks:
            self.table.insert(
                "",
                "end",
                iid=str(task["id"]),
                values=(
                    task["id"],
                    task["title"],
                    task["status"],
                    task["priority"],
                    task.get("due_date") or "",
                ),
            )
        self.status_message.configure(text=f"Loaded {len(tasks)} task(s)")

    def _select_task(self, _event: tk.Event) -> None:
        selected = self.table.selection()
        if not selected:
            return
        task_id = int(selected[0])
        try:
            task = self._request("GET", f"/api/v1/tasks/{task_id}")
        except RuntimeError as error:
            self._show_error(str(error))
            return
        self.selected_task_id = task_id
        self.title_value.set(task["title"])
        self.status_value.set(task["status"])
        self.priority_value.set(task["priority"])
        self.due_date_value.set(task.get("due_date") or "")
        self.description_box.delete("1.0", "end")
        self.description_box.insert("1.0", task.get("description") or "")
        self.status_message.configure(text=f"Selected task {task_id}")

    def _form_payload(self) -> dict:
        title = self.title_value.get().strip()
        if not title:
            raise ValueError("Enter a task title.")
        description = self.description_box.get("1.0", "end").strip()
        due_date = self.due_date_value.get().strip()
        return {
            "title": title,
            "description": description or None,
            "status": self.status_value.get(),
            "priority": self.priority_value.get(),
            "due_date": due_date or None,
        }

    def create_task(self) -> None:
        try:
            task = self._request("POST", "/api/v1/tasks", self._form_payload())
        except (RuntimeError, ValueError) as error:
            self._show_error(str(error))
            return
        self.clear_form()
        self.refresh_tasks()
        self.status_message.configure(text=f"Created task {task['id']}")

    def update_task(self) -> None:
        if self.selected_task_id is None:
            self._show_error("Select a task in the list before updating it.")
            return
        try:
            task = self._request(
                "PATCH",
                f"/api/v1/tasks/{self.selected_task_id}",
                self._form_payload(),
            )
        except (RuntimeError, ValueError) as error:
            self._show_error(str(error))
            return
        self.refresh_tasks()
        self.status_message.configure(text=f"Updated task {task['id']}")

    def delete_task(self) -> None:
        if self.selected_task_id is None:
            self._show_error("Select a task in the list before deleting it.")
            return
        task_id = self.selected_task_id
        if not messagebox.askyesno("Delete task", f"Delete task {task_id}?", parent=self.root):
            return
        try:
            self._request("DELETE", f"/api/v1/tasks/{task_id}")
        except RuntimeError as error:
            self._show_error(str(error))
            return
        self.clear_form()
        self.refresh_tasks()
        self.status_message.configure(text=f"Deleted task {task_id}")

    def clear_form(self) -> None:
        self.selected_task_id = None
        self.table.selection_remove(self.table.selection())
        self.title_value.set("")
        self.status_value.set("pending")
        self.priority_value.set("medium")
        self.due_date_value.set("")
        self.description_box.delete("1.0", "end")

    def _show_error(self, detail: str) -> None:
        self.status_message.configure(text=detail)
        messagebox.showerror("Task Manager", detail, parent=self.root)


def main() -> None:
    root = tk.Tk()
    TaskManagerUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
