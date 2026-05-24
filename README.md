# TodoAI

TodoAI is a full-stack AI-powered todo app built with React, FastAPI, SQLite, and Ollama.

You can:

- add tasks manually or through chat
- ask the AI to create, complete, delete, or summarize tasks
- filter tasks by status or tag
- export tasks as JSON or CSV
- keep chat history saved in the local database

## Tech Stack

- Frontend: React + Vite + Axios
- Backend: FastAPI + SQLAlchemy
- Database: SQLite
- AI: Ollama (`llama3.2` by default)

## Project Structure

```text
todo-ai/
  frontend/    # React app
  backend/     # FastAPI app
  HOW_IT_WORKS.md
  README.md
```

## Features

- AI chat for task creation and task actions
- Pending, completed, urgent, work, and personal filters
- Relative due date display like `Today`, `Tomorrow`, `3d left`
- Local chat history storage
- Ollama model status check
- Task export in `JSON` and `CSV`

## How It Works

High-level flow:

1. Frontend sends task and chat requests to the backend using `/api/...`
2. Backend stores tasks and chat history in SQLite
3. For common queries like pending/summary, backend answers directly from the database
4. For natural-language task actions, backend sends context to Ollama
5. Ollama returns structured output
6. Backend converts that into real database actions
7. Frontend refreshes and shows the updated task list

Detailed explanation is available in [HOW_IT_WORKS.md](./HOW_IT_WORKS.md).

## Prerequisites

Make sure these are installed:

- Node.js
- Python 3.10+
- Ollama

## Environment Variables

Current `.env` values used by the app:

```env
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
DATABASE_URL=sqlite:///./todos.db
CORS_ORIGIN=http://localhost:5173
```

## Backend Setup

Open a terminal in `todo-ai/backend` and run:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend will run on:

```text
http://localhost:8000
```

## Frontend Setup

Open another terminal in `todo-ai/frontend` and run:

```powershell
npm install
npm run dev
```

Frontend will run on:

```text
http://localhost:5173
```

## Ollama Setup

Start Ollama:

```powershell
ollama serve
```

Pull the model if needed:

```powershell
ollama pull llama3.2
```

## Usage Examples

You can type messages like:

```text
Add submit report by Friday urgent
Show urgent tasks
Mark all work tasks done
What is pending?
summary
```

## API Endpoints

Tasks:

- `GET /tasks`
- `POST /tasks`
- `PATCH /tasks/{task_id}`
- `DELETE /tasks/{task_id}`
- `DELETE /tasks/clear/completed`
- `DELETE /tasks/clear/all`
- `GET /tasks/summary`
- `GET /tasks/export/{fmt}`

Chat:

- `POST /chat`
- `GET /chat/history`
- `DELETE /chat/history`

System:

- `GET /`
- `GET /health`
- `GET /ollama-status`

## Build Frontend

```powershell
cd frontend
npm run build
```

## Push To GitHub

If this is a new repo:

```powershell
cd g:\todo-ai-app\todo-ai-app\todo-ai
git init
git add .
git commit -m "Initial TodoAI project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

If git is already initialized and remote already exists:

```powershell
cd g:\todo-ai-app\todo-ai-app\todo-ai
git add .
git commit -m "Update README and project docs"
git push
```

## Notes

- The app uses a local SQLite database: `backend/todos.db`
- Ollama runs locally, so AI requests stay on your machine
- Chat-based task actions are executed by the backend, not directly by the frontend

