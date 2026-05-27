import os
import json
import re
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import init_db, get_db, Task, ChatHistory
from models import TaskCreate, TaskUpdate, TaskOut, ChatRequest, ChatResponse
from ollama_client import chat_with_ollama, check_ollama_status

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI(title="TodoAI Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

PENDING_ACTION_PREFIX = "__pending_action__:"

WORK_KEYWORDS = {
    "office", "project", "submission", "submit", "report", "meeting", "client",
    "deadline", "presentation", "deploy", "deployment", "bug", "code", "review",
    "work", "manager", "email", "invoice", "proposal", "document", "documents",
}

PERSONAL_KEYWORDS = {
    "grocery", "groceries", "movie", "friends", "friend", "jlpt", "maths", "math",
    "study", "lesson", "chapter", "gym", "doctor", "dentist", "home", "family",
    "mom", "dad", "shopping", "buy", "cook", "clean",
}

URGENT_KEYWORDS = {"urgent", "critical", "asap", "immediately", "emergency"}


# ─── HEALTH ───

@app.get("/")
def root():
    return {"name": "TodoAI Backend", "version": "2.0.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ollama-status")
async def ollama_status():
    return await check_ollama_status()


# ─── TASKS CRUD ───

@app.get("/tasks", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    return [_task_to_dict(t) for t in tasks]


@app.post("/tasks", response_model=TaskOut)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    t = Task(
        title=_clean_task_title(task.title, task.due_date),
        tag=_normalize_tag(task.tag),
        due_date=task.due_date,
        priority=task.priority,
        created_at=datetime.now().isoformat(),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _task_to_dict(t)


@app.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, update: TaskUpdate, db: Session = Depends(get_db)):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t:
        raise HTTPException(404, "Task not found")
    if update.title is not None:
        t.title = _clean_task_title(update.title, update.due_date if update.due_date is not None else t.due_date)
    if update.tag is not None:
        t.tag = _normalize_tag(update.tag)
    if update.done is not None:
        t.done = update.done
    if update.due_date is not None:
        t.due_date = update.due_date
    if update.priority is not None:
        t.priority = update.priority
    db.commit()
    db.refresh(t)
    return _task_to_dict(t)


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    t = db.query(Task).filter(Task.id == task_id).first()
    if not t:
        raise HTTPException(404, "Task not found")
    db.delete(t)
    db.commit()
    return {"deleted": True}


@app.delete("/tasks/clear/completed")
def clear_completed(db: Session = Depends(get_db)):
    db.query(Task).filter(Task.done == True).delete()
    db.commit()
    return {"cleared": True}


@app.delete("/tasks/clear/all")
def clear_all(db: Session = Depends(get_db)):
    db.query(Task).delete()
    db.commit()
    return {"cleared_all": True}


@app.get("/tasks/summary")
def task_summary(db: Session = Depends(get_db)):
    tasks = db.query(Task).all()
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "total": len(tasks),
        "pending": len([t for t in tasks if not t.done]),
        "done": len([t for t in tasks if t.done]),
        "urgent": len([t for t in tasks if t.tag == "urgent" and not t.done]),
        "overdue": len([t for t in tasks if t.due_date and t.due_date < today and not t.done]),
        "today_due": len([t for t in tasks if t.due_date == today and not t.done]),
    }


@app.get("/tasks/export/{fmt}")
def export_tasks(fmt: str, db: Session = Depends(get_db)):
    tasks = db.query(Task).all()
    if fmt == "json":
        return [_task_to_dict(t) for t in tasks]
    elif fmt == "csv":
        lines = ["id,title,tag,done,due_date,priority,created_at"]
        for t in tasks:
            done_str = "yes" if t.done else "no"
            lines.append(f'{t.id},"{t.title}",{t.tag},{done_str},{t.due_date or ""},{t.priority},{t.created_at}')
        return {"csv": "\n".join(lines)}
    else:
        raise HTTPException(400, "Format must be 'json' or 'csv'")


# ─── CHAT ───

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    pending_action = _get_pending_action(db)
    if pending_action is not None:
        confirmation_state = _parse_confirmation_reply(req.message)

        if confirmation_state is None and _looks_like_fresh_command(req.message):
            _clear_pending_action(db)
            pending_action = None

    if pending_action is not None:
        if confirmation_state == "confirm":
            user_msg = ChatHistory(role="user", content=req.message, timestamp=datetime.now().isoformat())
            db.add(user_msg)
            final_message, refresh = _execute_pending_action(db, pending_action)
            _clear_pending_action(db)
            ai_msg = ChatHistory(role="assistant", content=final_message, timestamp=datetime.now().isoformat())
            db.add(ai_msg)
            db.commit()
            return ChatResponse(
                type="action",
                action=pending_action.get("action"),
                message=final_message,
                filter=pending_action.get("filter"),
                refresh=refresh,
            )

        if confirmation_state == "cancel":
            user_msg = ChatHistory(role="user", content=req.message, timestamp=datetime.now().isoformat())
            _clear_pending_action(db)
            ai_msg = ChatHistory(
                role="assistant",
                content="Okay, I stopped that delete request. Nothing was removed.",
                timestamp=datetime.now().isoformat(),
            )
            db.add(user_msg)
            db.add(ai_msg)
            db.commit()
            return ChatResponse(
                type="text",
                message="Okay, I stopped that delete request. Nothing was removed.",
                refresh=False,
            )

        user_msg = ChatHistory(role="user", content=req.message, timestamp=datetime.now().isoformat())
        ai_msg = ChatHistory(
            role="assistant",
            content="I’m waiting for your confirmation on the delete request. Reply with yes to continue or no to cancel.",
            timestamp=datetime.now().isoformat(),
        )
        db.add(user_msg)
        db.add(ai_msg)
        db.commit()
        return ChatResponse(
            type="text",
            message="I’m waiting for your confirmation on the delete request. Reply with yes to continue or no to cancel.",
            refresh=False,
        )

    tasks = db.query(Task).all()
    direct_response = _maybe_handle_direct_command(req.message, tasks)
    if direct_response is not None:
        user_msg = ChatHistory(role="user", content=req.message, timestamp=datetime.now().isoformat())
        db.add(user_msg)
        if direct_response["action"] == "add":
            task_payloads = direct_response.get("tasks") or [direct_response.get("task", {})]
            created_tasks = _create_tasks_from_payloads(db, task_payloads)
            direct_response["message"] = _build_add_confirmation_for_tasks(created_tasks)
            ai_msg = ChatHistory(role="assistant", content=direct_response["message"], timestamp=datetime.now().isoformat())
            db.add(ai_msg)
            db.commit()
        elif direct_response.get("needs_confirmation"):
            ai_msg = ChatHistory(role="assistant", content=direct_response["message"], timestamp=datetime.now().isoformat())
            db.add(ai_msg)
            _store_pending_action(db, direct_response["pending_action"])
            db.commit()
        else:
            ai_msg = ChatHistory(role="assistant", content=direct_response["message"], timestamp=datetime.now().isoformat())
            db.add(ai_msg)
            db.commit()
            if direct_response["action"] == "delete":
                if direct_response.get("filter") == "done":
                    db.query(Task).filter(Task.done == True).delete()
                elif direct_response.get("filter") == "all":
                    db.query(Task).delete()
                elif direct_response.get("filter") == "urgent":
                    db.query(Task).filter(Task.tag == "urgent").delete()
                db.commit()
            elif direct_response["action"] == "complete":
                if direct_response.get("filter") in ("all", "pending"):
                    db.query(Task).filter(Task.done == False).update({"done": True})
                elif direct_response.get("filter") in ("work", "personal", "urgent"):
                    db.query(Task).filter(
                        Task.tag == direct_response.get("filter"),
                        Task.done == False,
                    ).update({"done": True})
                db.commit()

        return ChatResponse(
            type="action",
            action=direct_response["action"],
            message=direct_response["message"],
            filter=direct_response.get("filter"),
            refresh=direct_response["action"] in {"add", "delete", "complete"} and not direct_response.get("needs_confirmation", False),
        )

    # Build tasks summary for context
    tasks_summary = json.dumps(
        [{"id": t.id, "title": t.title, "tag": t.tag, "done": t.done,
          "due_date": t.due_date, "priority": t.priority}
         for t in tasks],
        ensure_ascii=False,
    )

    # Get history from DB (last 20)
    history_records = db.query(ChatHistory).order_by(ChatHistory.id.desc()).limit(20).all()
    db_history = [{"role": h.role, "content": h.content} for h in reversed(history_records)]

    # Merge with client-side history (prefer client)
    chat_history = [h.model_dump() for h in req.history] if req.history else db_history

    # Save user message
    user_msg = ChatHistory(role="user", content=req.message, timestamp=datetime.now().isoformat())
    db.add(user_msg)
    db.commit()

    # Call Ollama
    result = await chat_with_ollama(req.message, chat_history, tasks_summary)

    # Process action
    if result["type"] == "action":
        data = result["data"]
        action = data.get("action")
        task_data = data.get("task", {})
        filt = data.get("filter")

        if action == "add" and task_data.get("title"):
            task_payloads = _split_add_payload_if_needed(task_data)
            created_tasks = _create_tasks_from_payloads(db, task_payloads)
            data["message"] = _build_add_confirmation_for_tasks(created_tasks)

        elif action == "complete":
            if filt in ("all", "pending"):
                db.query(Task).filter(Task.done == False).update({"done": True})
            elif filt in ("work", "personal", "urgent"):
                db.query(Task).filter(Task.tag == filt, Task.done == False).update({"done": True})
            else:
                # Complete most recent pending
                t = db.query(Task).filter(Task.done == False).first()
                if t:
                    t.done = True
            db.commit()
            if not data.get("message") or data.get("message", "").strip().lower() in {"confirmation message", "done!", "completed"}:
                data["message"] = _build_complete_confirmation(filt)

        elif action == "delete":
            pending_payload = {
                "action": "delete",
                "filter": filt,
                "task_title": task_data.get("title"),
            }
            _store_pending_action(db, pending_payload)
            data["message"] = _build_delete_confirmation_prompt(filt, task_data.get("title"), tasks)
            ai_msg = ChatHistory(
                role="assistant",
                content=data["message"],
                timestamp=datetime.now().isoformat(),
            )
            db.add(ai_msg)
            db.commit()
            return ChatResponse(
                type="action",
                action="delete",
                message=data["message"],
                filter=filt,
                refresh=False,
            )

        elif action == "edit" and task_data:
            task_id = data.get("task_id")
            if task_id:
                t = db.query(Task).filter(Task.id == task_id).first()
                if t:
                    if task_data.get("title"):
                        t.title = _clean_task_title(task_data["title"], task_data.get("due_date", t.due_date))
                    if task_data.get("tag"):
                        t.tag = _normalize_tag(task_data["tag"])
                    if task_data.get("due_date"):
                        t.due_date = task_data["due_date"]
                    db.commit()

        elif action == "summary":
            counts = {
                "total": db.query(Task).count(),
                "pending": db.query(Task).filter(Task.done == False).count(),
                "done": db.query(Task).filter(Task.done == True).count(),
                "urgent": db.query(Task).filter(Task.tag == "urgent", Task.done == False).count(),
            }
            msg = data.get("message", "").replace("{pending}", str(counts["pending"])) \
                .replace("{done}", str(counts["done"])) \
                .replace("{urgent}", str(counts["urgent"])) \
                .replace("{total}", str(counts["total"]))
            data["message"] = msg

        # Save AI response to history
        ai_msg = ChatHistory(
            role="assistant",
            content=data.get("message", "Done!"),
            timestamp=datetime.now().isoformat(),
        )
        db.add(ai_msg)
        db.commit()

        return ChatResponse(
            type="action",
            action=action,
            message=data.get("message", "Done!"),
            filter=filt if action == "list" else None,
            refresh=action in {"add", "complete", "delete", "edit"},
        )

    # Plain text response
    ai_msg = ChatHistory(
        role="assistant",
        content=result["data"],
        timestamp=datetime.now().isoformat(),
    )
    db.add(ai_msg)
    db.commit()

    return ChatResponse(
        type="text",
        message=result["data"],
        refresh=False,
    )


@app.get("/chat/history")
def get_chat_history(db: Session = Depends(get_db)):
    records = db.query(ChatHistory).order_by(ChatHistory.id.desc()).limit(20).all()
    return [
        {"id": h.id, "role": h.role, "content": h.content, "timestamp": h.timestamp}
        for h in reversed(records)
        if not h.content.startswith(PENDING_ACTION_PREFIX)
    ]


@app.delete("/chat/history")
def clear_chat_history(db: Session = Depends(get_db)):
    db.query(ChatHistory).delete()
    db.commit()
    return {"cleared": True}


# ─── HELPER ───

def _task_to_dict(t: Task) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "tag": t.tag,
        "done": t.done,
        "due_date": t.due_date,
        "priority": t.priority,
        "created_at": t.created_at,
    }


def _maybe_handle_direct_command(message: str, tasks: list[Task]) -> dict | None:
    normalized = " ".join((message or "").strip().lower().split())
    if not normalized:
        return None

    add_payloads = _extract_direct_add_tasks(message)
    if add_payloads is not None:
        return {
            "action": "add",
            "tasks": add_payloads,
        }

    pending_tasks = [t for t in tasks if not t.done]
    done_tasks = [t for t in tasks if t.done]
    urgent_tasks = [t for t in pending_tasks if t.tag == "urgent"]
    today = datetime.now().strftime("%Y-%m-%d")
    today_tasks = [t for t in pending_tasks if t.due_date == today]

    if _matches_any(normalized, [
        "delete all", "delete every", "delete all task", "delete all tasks",
        "delete every task", "delete every tasks", "remove all task", "remove all tasks",
        "clear all task", "clear all tasks",
    ]):
        total = len(tasks)
        return {
            "action": "delete",
            "filter": "all",
            "message": (
                f"Oho, you want to delete all {total} task{'s' if total != 1 else ''}. "
                "Reply yes to confirm or no to cancel."
            ),
            "needs_confirmation": True,
            "pending_action": {"action": "delete", "filter": "all"},
        }

    if _matches_any(normalized, [
        "delete done", "delete completed", "clear done", "clear completed",
        "remove completed", "remove done",
    ]):
        return {
            "action": "delete",
            "filter": "done",
            "message": (
                f"Oho, I can delete {len(done_tasks)} completed task{'s' if len(done_tasks) != 1 else ''}. "
                "Reply yes to confirm or no to cancel."
            ),
            "needs_confirmation": True,
            "pending_action": {"action": "delete", "filter": "done"},
        }

    if _matches_any(normalized, [
        "delete urgent", "remove urgent", "clear urgent",
    ]):
        return {
            "action": "delete",
            "filter": "urgent",
            "message": (
                f"Oho, that will remove {len(urgent_tasks)} urgent task{'s' if len(urgent_tasks) != 1 else ''}. "
                "Reply yes to confirm or no to cancel."
            ),
            "needs_confirmation": True,
            "pending_action": {"action": "delete", "filter": "urgent"},
        }

    specific_delete_title = _extract_direct_delete_target(message)
    if specific_delete_title:
        return {
            "action": "delete",
            "filter": None,
            "message": (
                f'Oho, do you want me to delete the task matching "{specific_delete_title}"? '
                "Reply yes to confirm or no to cancel."
            ),
            "needs_confirmation": True,
            "pending_action": {"action": "delete", "filter": None, "task_title": specific_delete_title},
        }

    if _matches_any(normalized, [
        "mark all done", "mark all tasks done", "complete all", "complete all tasks",
        "finish all", "finish all tasks",
    ]):
        return {
            "action": "complete",
            "filter": "all",
            "message": _build_complete_confirmation("all", len(pending_tasks)),
        }

    if _matches_any(normalized, [
        "mark work done", "complete work", "complete work tasks", "finish work tasks",
    ]):
        work_pending = [t for t in pending_tasks if t.tag == "work"]
        return {
            "action": "complete",
            "filter": "work",
            "message": _build_complete_confirmation("work", len(work_pending)),
        }

    if _matches_any(normalized, [
        "mark personal done", "complete personal", "complete personal tasks", "finish personal tasks",
    ]):
        personal_pending = [t for t in pending_tasks if t.tag == "personal"]
        return {
            "action": "complete",
            "filter": "personal",
            "message": _build_complete_confirmation("personal", len(personal_pending)),
        }

    if _matches_any(normalized, [
        "mark urgent done", "complete urgent", "complete urgent tasks", "finish urgent tasks",
    ]):
        return {
            "action": "complete",
            "filter": "urgent",
            "message": _build_complete_confirmation("urgent", len(urgent_tasks)),
        }

    if _matches_any(normalized, [
        "what is pending", "what's pending", "show pending", "pending tasks", "list pending",
    ]):
        return {
            "action": "list",
            "filter": "pending",
            "message": _build_task_list_message("pending", pending_tasks),
        }

    if _matches_any(normalized, [
        "what is urgent", "what's urgent", "show urgent", "urgent tasks", "list urgent",
    ]):
        return {
            "action": "list",
            "filter": "urgent",
            "message": _build_task_list_message("urgent", urgent_tasks),
        }

    if _matches_any(normalized, [
        "what is completed", "what's completed", "show completed", "completed tasks", "list completed",
        "what is done", "what's done", "show done", "done tasks", "list done",
    ]):
        return {
            "action": "list",
            "filter": "done",
            "message": _build_task_list_message("completed", done_tasks),
        }

    if _matches_any(normalized, [
        "what is due today", "what's due today", "show today", "today tasks", "list today",
    ]):
        return {
            "action": "list",
            "filter": "today",
            "message": _build_task_list_message("due today", today_tasks),
        }

    if _matches_any(normalized, [
        "summary", "task summary", "what is the summary", "what's the summary", "overview",
        "summery", "sumarry", "summary de", "sumarry de", "summery de",
    ]):
        return {
            "action": "summary",
            "message": _build_summary_message(tasks, pending_tasks, done_tasks, urgent_tasks, today_tasks),
        }

    return None


def _matches_any(message: str, phrases: list[str]) -> bool:
    return any(phrase in message for phrase in phrases)


def _build_task_list_message(label: str, tasks: list[Task]) -> str:
    if not tasks:
        return f"Nice, no {label} tasks found right now."
    titles = ", ".join(t.title for t in tasks[:5])
    extra = "" if len(tasks) <= 5 else f" and {len(tasks) - 5} more"
    return f"Okay, you have {len(tasks)} {label} task{'s' if len(tasks) != 1 else ''}: {titles}{extra}."


def _build_add_confirmation(title: str, tag: str, due_date: str | None) -> str:
    parts = [f'Nice, I added "{title}"']
    if tag:
        parts.append(f"under {tag}")
    if due_date:
        parts.append(f"due {due_date}")
    return ", ".join(parts) + "."


def _build_add_confirmation_for_tasks(tasks: list[Task]) -> str:
    if not tasks:
        return "I could not find a clear task to add."
    if len(tasks) == 1:
        task = tasks[0]
        return _build_add_confirmation(task.title, task.tag, task.due_date)

    titles = ", ".join(f'"{task.title}"' for task in tasks)
    shared_due_dates = {task.due_date for task in tasks}
    due_text = ""
    if len(shared_due_dates) == 1:
        due_date = next(iter(shared_due_dates))
        if due_date:
            due_text = f", due {due_date}"
    return f"Nice, I added {len(tasks)} tasks: {titles}{due_text}."


def _create_tasks_from_payloads(db: Session, task_payloads: list[dict]) -> list[Task]:
    created_tasks = []
    for task_data in task_payloads:
        if not task_data or not task_data.get("title"):
            continue
        task = Task(
            title=_clean_task_title(task_data["title"], task_data.get("due_date")),
            tag=_normalize_tag(task_data.get("tag", "personal")),
            due_date=task_data.get("due_date"),
            priority=task_data.get("priority", 3),
            created_at=datetime.now().isoformat(),
        )
        db.add(task)
        created_tasks.append(task)

    db.commit()
    for task in created_tasks:
        db.refresh(task)
    return created_tasks


def _build_complete_confirmation(filter_name: str | None, count: int | None = None) -> str:
    if filter_name == "all":
        if count is not None:
            return f"Done, I marked {count} pending task{'s' if count != 1 else ''} as complete."
        return "Done, I marked all pending tasks as complete."
    if filter_name in {"work", "personal", "urgent"}:
        if count is not None:
            return f"Done, I marked {count} {filter_name} task{'s' if count != 1 else ''} as complete."
        return f"Done, I marked {filter_name} tasks as complete."
    return "Done, the task has been updated."


def _build_delete_confirmation(filter_name: str | None, title: str | None = None) -> str:
    if filter_name == "all":
        return "Okay, all tasks have been deleted."
    if filter_name == "done":
        return "Okay, completed tasks have been deleted."
    if filter_name == "urgent":
        return "Okay, urgent tasks have been deleted."
    if title:
        return f'Okay, I deleted the task matching "{title}".'
    return "Okay, the task has been deleted."


def _build_delete_not_found_message(filter_name: str | None, title: str | None = None) -> str:
    if filter_name == "all":
        return "There were no tasks left to delete."
    if filter_name == "done":
        return "I could not find any completed tasks to delete."
    if filter_name == "urgent":
        return "I could not find any urgent tasks to delete."
    if title:
        return f'I could not find any task matching "{title}".'
    return "I could not find a matching task to delete."


def _build_delete_confirmation_prompt(filter_name: str | None, title: str | None, tasks: list[Task]) -> str:
    if filter_name == "all":
        return (
            f"Oho, this will delete all {len(tasks)} task{'s' if len(tasks) != 1 else ''}. "
            "Reply yes to confirm or no to cancel."
        )
    if filter_name == "done":
        done_count = len([t for t in tasks if t.done])
        return (
            f"Oho, this will delete {done_count} completed task{'s' if done_count != 1 else ''}. "
            "Reply yes to confirm or no to cancel."
        )
    if filter_name == "urgent":
        urgent_count = len([t for t in tasks if t.tag == "urgent"])
        return (
            f"Oho, this will delete {urgent_count} urgent task{'s' if urgent_count != 1 else ''}. "
            "Reply yes to confirm or no to cancel."
        )
    if title:
        return f'Oho, do you want me to delete the task matching "{title}"? Reply yes to confirm or no to cancel.'
    return "Oho, do you want me to continue with delete? Reply yes to confirm or no to cancel."


def _build_summary_message(tasks: list[Task], pending_tasks: list[Task], done_tasks: list[Task], urgent_tasks: list[Task], today_tasks: list[Task]) -> str:
    return (
        f"Here’s the quick picture: total {len(tasks)} tasks, pending {len(pending_tasks)}, "
        f"completed {len(done_tasks)}, urgent {len(urgent_tasks)}, due today {len(today_tasks)}."
    )


def _parse_confirmation_reply(message: str) -> str | None:
    normalized = " ".join((message or "").strip().lower().split())
    if normalized in {
        "yes", "y", "haan", "ha", "han", "yes do it", "confirm", "ok", "okay", "ok do it",
        "kar do", "kardo", "delete it", "yes delete", "proceed",
    }:
        return "confirm"
    if normalized in {
        "no", "n", "nah", "cancel", "stop", "mat karo", "rehne do", "don't", "dont",
    }:
        return "cancel"
    return None


def _looks_like_fresh_command(message: str) -> bool:
    normalized = " ".join((message or "").strip().lower().split())
    return normalized.startswith((
        "add ", "add task", "create ", "make ",
        "delete ", "remove ", "clear ",
        "show ", "list ", "mark ", "complete ",
        "summary", "summery", "sumarry", "what ",
    ))


def _get_pending_action(db: Session) -> dict | None:
    record = (
        db.query(ChatHistory)
        .filter(ChatHistory.content.startswith(PENDING_ACTION_PREFIX))
        .order_by(ChatHistory.id.desc())
        .first()
    )
    if not record:
        return None
    try:
        return json.loads(record.content[len(PENDING_ACTION_PREFIX):])
    except json.JSONDecodeError:
        return None


def _store_pending_action(db: Session, payload: dict) -> None:
    _clear_pending_action(db)
    db.add(ChatHistory(
        role="assistant",
        content=f"{PENDING_ACTION_PREFIX}{json.dumps(payload, ensure_ascii=False)}",
        timestamp=datetime.now().isoformat(),
    ))


def _clear_pending_action(db: Session) -> None:
    db.query(ChatHistory).filter(ChatHistory.content.startswith(PENDING_ACTION_PREFIX)).delete()


def _execute_pending_action(db: Session, payload: dict) -> tuple[str, bool]:
    action = payload.get("action")
    if action != "delete":
        return "I could not finish that action.", False

    filt = payload.get("filter")
    title = payload.get("task_title")
    deleted_count = 0
    if filt == "done":
        deleted_count = db.query(Task).filter(Task.done == True).delete()
    elif filt == "all":
        deleted_count = db.query(Task).delete()
    elif filt == "urgent":
        deleted_count = db.query(Task).filter(Task.tag.ilike("%urgent%")).delete()
    elif title:
        deleted_count = db.query(Task).filter(Task.title.ilike(f"%{title.lower()}%")).delete()
    db.commit()
    if deleted_count == 0:
        return _build_delete_not_found_message(filt, title), False
    return _build_delete_confirmation(filt, title), True


def _extract_direct_delete_target(message: str) -> str | None:
    raw = " ".join((message or "").strip().split())
    normalized = raw.lower()
    if not raw:
        return None

    if not normalized.startswith(("delete ", "remove ")):
        return None

    if any(phrase in normalized for phrase in (
        "delete all", "delete every", "delete done", "delete completed", "delete urgent",
        "remove all", "remove completed", "remove urgent",
    )):
        return None

    title = raw
    title = re.sub(r"^\s*(delete|remove)\s+", "", title, flags=re.IGNORECASE)
    title = re.sub(r"^\s*(one|this|the)\s+", "", title, flags=re.IGNORECASE)
    title = re.sub(r"^\s*task\s+", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s{2,}", " ", title).strip(" ,.-")
    return _normalize_human_title(title) or None


def _clean_task_title(title: str, due_date: str | None) -> str:
    cleaned = " ".join((title or "").strip().split())
    cleaned = _strip_add_title_scaffolding(cleaned)
    if not due_date:
        return _normalize_human_title(cleaned)

    patterns = [
        r"\s*,?\s*for\s+tomm?or?row\s*$",
        r"\s*,?\s*tomm?or?row\s*$",
        r"\s*,?\s*for\s+today\s*$",
        r"\s*,?\s*today\s*$",
        r"\s*,?\s*on\s+\d{1,2}(st|nd|rd|th)?(\s+this\s+month|\s+[a-z]+)?\s*$",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,.-")
    return _normalize_human_title(cleaned or "Untitled Task")


def _extract_direct_add_task(message: str) -> dict | None:
    tasks = _extract_direct_add_tasks(message)
    if not tasks:
        return None
    return tasks[0]


def _extract_direct_add_tasks(message: str) -> list[dict] | None:
    raw = " ".join((message or "").strip().split())
    normalized = raw.lower()
    if not raw:
        return None

    if not (
        normalized.startswith("add ")
        or normalized.startswith("add task")
        or normalized.startswith("create task")
        or normalized.startswith("make task")
    ):
        return None

    global_due_date = _extract_due_date(raw)
    priority = 5 if "urgent" in normalized or "asap" in normalized else 3

    title_text = _extract_add_title_text(raw)
    chunks = _split_task_chunks(title_text)
    if not chunks:
        return None

    tasks = []
    previous_action = None
    for chunk in chunks:
        title = _normalize_human_title(_strip_add_title_scaffolding(chunk))
        if previous_action and re.match(r"^\d+\b", title):
            title = f"{previous_action} {title}"
        if not title:
            continue
        action_match = re.match(r"^(buy|study|read|watch|write|submit|finish|complete|call|go|going)\b", title, flags=re.IGNORECASE)
        if action_match:
            previous_action = action_match.group(1).lower()
        tasks.append({
            "title": title,
            "tag": _infer_task_tag(title, raw),
            "due_date": _extract_due_date(chunk) or (global_due_date if len(chunks) == 1 else None),
            "priority": priority,
        })

    return tasks or None


def _split_add_payload_if_needed(task_data: dict) -> list[dict]:
    chunks = _split_task_chunks(_strip_add_title_scaffolding(task_data.get("title", ""), remove_dates=False))
    if len(chunks) <= 1:
        return [task_data]
    return [
        {
            **task_data,
            "title": _normalize_human_title(_strip_add_title_scaffolding(chunk)),
            "due_date": _extract_due_date(chunk) or task_data.get("due_date"),
        }
        for chunk in chunks
        if _normalize_human_title(_strip_add_title_scaffolding(chunk))
    ]


def _extract_add_title_text(message: str) -> str:
    title = message
    title = re.sub(r"^\s*(add|create|make)\s+(a\s+)?task\b[:, -]*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"^\s*add\b[:, -]*", "", title, flags=re.IGNORECASE)
    return _strip_add_title_scaffolding(title, remove_dates=False)


def _strip_add_title_scaffolding(title: str, remove_dates: bool = True) -> str:
    cleaned = " ".join((title or "").strip().split())
    cleaned = re.sub(
        r"^\s*(this|the|new)?\s*task\s+with\s+start\s+date\s+and\s+end\s+date\s*[:, -]*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^\s*(this|the|new)?\s*task\s*[:, -]*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\b(on|in)\s+(work|personal|urgent)\b[:, -]*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(work|personal|urgent)\s+task\b[:, -]*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*(work|personal|urgent)\s*,", "", cleaned, flags=re.IGNORECASE)
    if remove_dates:
        cleaned = re.sub(r"\bfor\s+(today|tomm?or?row|day after tomorrow)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bon\s+\d{1,2}(st|nd|rd|th)?(\s+this\s+month|\s+[A-Za-z]+)?\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(today|tomm?or?row|day after tomorrow)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(asap|urgent)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[,:]+" if remove_dates else r":+", " ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,.-")
    return cleaned


def _split_task_chunks(title_text: str) -> list[str]:
    cleaned = _strip_add_title_scaffolding(title_text, remove_dates=False)
    if not cleaned:
        return []
    return [
        chunk.strip(" ,.-")
        for chunk in re.split(r"\s*,\s*(?:and\s+)?|\s+\band\b\s+", cleaned, flags=re.IGNORECASE)
        if chunk.strip(" ,.-")
    ]


def _split_task_titles(title_text: str) -> list[str]:
    cleaned = _strip_add_title_scaffolding(title_text)
    if not cleaned:
        return []

    chunks = re.split(r"\s*,\s*(?:and\s+)?|\s+\band\b\s+", cleaned, flags=re.IGNORECASE)
    titles = []
    previous_action = None
    for chunk in chunks:
        title = _normalize_human_title(_strip_add_title_scaffolding(chunk))
        if not title:
            continue
        if previous_action and re.match(r"^\d+\b", title):
            title = f"{previous_action} {title}"
        action_match = re.match(r"^(buy|study|read|watch|write|submit|finish|complete|call|go|going)\b", title, flags=re.IGNORECASE)
        if action_match:
            previous_action = action_match.group(1).lower()
        titles.append(title)

    if not titles:
        fallback = _normalize_human_title(cleaned)
        return [fallback] if fallback else []
    return titles


def _extract_tag(message: str) -> str:
    return _infer_task_tag(message)


def _infer_task_tag(title: str, full_message: str | None = None) -> str:
    title_words = set(re.findall(r"[a-z]+", (title or "").lower()))
    context_words = set(re.findall(r"[a-z]+", (full_message or "").lower()))
    words = title_words | context_words

    if words & URGENT_KEYWORDS:
        if "work" in words or title_words & WORK_KEYWORDS:
            return "work"
        if "personal" in words or title_words & PERSONAL_KEYWORDS:
            return "personal"
        return "urgent"
    if "personal" in context_words and not (title_words & WORK_KEYWORDS):
        return "personal"
    if "work" in context_words and not (title_words & PERSONAL_KEYWORDS):
        return "work"
    if title_words & WORK_KEYWORDS:
        return "work"
    if title_words & PERSONAL_KEYWORDS:
        return "personal"
    return "personal"


def _normalize_tag(tag: str | None) -> str:
    normalized = (tag or "personal").strip().lower()
    if "urgent" in normalized and "work" not in normalized and "personal" not in normalized:
        return "urgent"
    if "work" in normalized:
        return "work"
    if "personal" in normalized:
        return "personal"
    return "personal"


def _extract_due_date(message: str) -> str | None:
    normalized = message.lower()
    today = datetime.now().date()

    this_month_match = re.search(r"\b(?:on\s+)?(\d{1,2})(st|nd|rd|th)?\s+this\s+month\b", normalized)
    if this_month_match:
        day = int(this_month_match.group(1))
        try:
            candidate = datetime(today.year, today.month, day).date()
        except ValueError:
            candidate = None
        if candidate is not None and candidate >= today:
            return candidate.strftime("%Y-%m-%d")

    if "day after tomorrow" in normalized:
        return (today + timedelta(days=2)).strftime("%Y-%m-%d")
    if "tommorow" in normalized or "tomorrow" in normalized:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    if "today" in normalized:
        return today.strftime("%Y-%m-%d")

    match = re.search(r"\b(?:on\s+)?(\d{1,2})(st|nd|rd|th)?(?:\s+([A-Za-z]+))?\b", normalized)
    if match:
      day = int(match.group(1))
      weekday_name = match.group(3)
      candidate = _resolve_day_in_near_future(today, day, weekday_name)
      if candidate is not None:
          return candidate.strftime("%Y-%m-%d")

    return None


def _resolve_day_in_near_future(base_date, day: int, weekday_name: str | None):
    for month_offset in range(0, 3):
        month = base_date.month + month_offset
        year = base_date.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        try:
            candidate = datetime(year, month, day).date()
        except ValueError:
            continue
        if candidate < base_date:
            continue
        if weekday_name:
            weekday_index = _weekday_to_index(weekday_name)
            if weekday_index is None or candidate.weekday() != weekday_index:
                continue
        return candidate
    return None


def _weekday_to_index(name: str | None) -> int | None:
    if not name:
        return None
    lookup = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    return lookup.get((name or "").strip().lower())


def _normalize_human_title(title: str) -> str:
    cleaned = " ".join((title or "").strip().split())
    if not cleaned:
        return ""
    cleaned = re.sub(r"\bsubit\b", "submit", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\breort\b", "report", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bmoie\b", "movie", cleaned, flags=re.IGNORECASE)
    return cleaned.strip(" ,.-")
