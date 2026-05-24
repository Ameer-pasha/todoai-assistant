import os
import json
import re
from datetime import datetime
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
        tag=task.tag,
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
        t.tag = update.tag
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
    tasks = db.query(Task).all()
    direct_response = _maybe_answer_from_tasks(req.message, tasks)
    if direct_response is not None:
        user_msg = ChatHistory(role="user", content=req.message, timestamp=datetime.now().isoformat())
        ai_msg = ChatHistory(role="assistant", content=direct_response["message"], timestamp=datetime.now().isoformat())
        db.add(user_msg)
        db.add(ai_msg)
        db.commit()
        return ChatResponse(
            type="action",
            action=direct_response["action"],
            message=direct_response["message"],
            filter=direct_response.get("filter"),
            refresh=False,
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
            t = Task(
                title=_clean_task_title(task_data["title"], task_data.get("due_date")),
                tag=task_data.get("tag", "personal"),
                due_date=task_data.get("due_date"),
                priority=task_data.get("priority", 3),
                created_at=datetime.now().isoformat(),
            )
            db.add(t)
            db.commit()

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

        elif action == "delete":
            if filt == "done":
                db.query(Task).filter(Task.done == True).delete()
            elif filt == "all":
                db.query(Task).delete()
            elif filt == "urgent":
                db.query(Task).filter(Task.tag == "urgent").delete()
            elif task_data.get("title"):
                title = task_data["title"].lower()
                db.query(Task).filter(Task.title.ilike(f"%{title}%")).delete()
            db.commit()

        elif action == "edit" and task_data:
            task_id = data.get("task_id")
            if task_id:
                t = db.query(Task).filter(Task.id == task_id).first()
                if t:
                    if task_data.get("title"):
                        t.title = _clean_task_title(task_data["title"], task_data.get("due_date", t.due_date))
                    if task_data.get("tag"):
                        t.tag = task_data["tag"]
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


def _maybe_answer_from_tasks(message: str, tasks: list[Task]) -> dict | None:
    normalized = " ".join((message or "").strip().lower().split())
    if not normalized:
        return None

    pending_tasks = [t for t in tasks if not t.done]
    done_tasks = [t for t in tasks if t.done]
    urgent_tasks = [t for t in pending_tasks if t.tag == "urgent"]
    today = datetime.now().strftime("%Y-%m-%d")
    today_tasks = [t for t in pending_tasks if t.due_date == today]

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
    ]):
        return {
            "action": "summary",
            "message": (
                f"Total {len(tasks)} tasks. "
                f"Pending {len(pending_tasks)}, completed {len(done_tasks)}, urgent {len(urgent_tasks)}, "
                f"due today {len(today_tasks)}."
            ),
        }

    return None


def _matches_any(message: str, phrases: list[str]) -> bool:
    return any(phrase in message for phrase in phrases)


def _build_task_list_message(label: str, tasks: list[Task]) -> str:
    if not tasks:
        return f"No {label} tasks found."
    titles = ", ".join(t.title for t in tasks[:5])
    extra = "" if len(tasks) <= 5 else f" and {len(tasks) - 5} more"
    return f"{len(tasks)} {label} task{'s' if len(tasks) != 1 else ''}: {titles}{extra}."


def _clean_task_title(title: str, due_date: str | None) -> str:
    cleaned = " ".join((title or "").strip().split())
    if not due_date:
        return cleaned

    patterns = [
        r"\s*,?\s*for\s+tomm?or?row\s*$",
        r"\s*,?\s*tomm?or?row\s*$",
        r"\s*,?\s*for\s+today\s*$",
        r"\s*,?\s*today\s*$",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,.-")
    return cleaned or "Untitled Task"
