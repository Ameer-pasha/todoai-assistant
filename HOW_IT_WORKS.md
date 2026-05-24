# TodoAI Kaise Kaam Karta Hai

Yeh file simple Hinglish mein explain karti hai ki app ke andar kya kaise chal raha hai.

## 1. Project Structure

Project ke 2 main parts hain:

- `frontend/`
  React app jo UI dikhata hai
- `backend/`
  FastAPI server jo tasks, chat, AI aur database handle karta hai

## 2. Frontend Ka Role

Frontend files:

- `frontend/src/App.jsx`
- `frontend/src/hooks/useTasks.js`
- `frontend/src/hooks/useChat.js`
- `frontend/src/api.js`
- `frontend/src/components/*`

Frontend ka kaam:

- tasks dikhana
- filters lagana
- chat input lena
- backend ko API call bhejna
- backend se aaya result screen par dikhana

## 3. Backend Ka Role

Backend files:

- `backend/main.py`
- `backend/database.py`
- `backend/models.py`
- `backend/ollama_client.py`
- `backend/prompt.py`

Backend ka kaam:

- tasks ko database mein save karna
- edit/delete/complete handle karna
- chat messages store karna
- AI ko call karna
- AI ke response ko action mein convert karna

## 4. Database Mein Kya Save Hota Hai

Database SQLite hai.

`backend/database.py` mein 2 tables defined hain:

### `tasks`

- `id`
- `title`
- `tag`
- `done`
- `due_date`
- `priority`
- `created_at`

### `chat_history`

- `id`
- `role`
- `content`
- `timestamp`

## 5. App Start Hone Par Kya Hota Hai

Frontend `frontend/src/main.jsx` se start hota hai.

Wahan `App` load hota hai.

`App.jsx` page ko 3 sections mein todta hai:

- `Sidebar`
- `TaskList`
- `ChatPanel`

Uske baad:

- `useTasks()` backend se tasks fetch karta hai
- `useChat()` old chat history fetch karta hai
- `getOllamaStatus()` model available hai ya nahi check karta hai

## 6. Frontend API Calls Kaise Hoti Hain

`frontend/src/api.js` mein axios instance bana hua hai.

Sab calls `/api/...` route par jaati hain.

Important APIs:

- `GET /tasks`
- `POST /tasks`
- `PATCH /tasks/{id}`
- `DELETE /tasks/{id}`
- `POST /chat`
- `GET /chat/history`
- `DELETE /chat/history`
- `GET /ollama-status`

## 7. Normal Task Add Kaise Hota Hai

Task add ke 2 conceptual tareeke hain:

### A. Direct API add

`useTasks.js` ka `add()` function:

1. `createTask()` call karta hai
2. backend `POST /tasks` hit hota hai
3. backend task ko DB mein save karta hai
4. frontend `refresh()` karke updated list laata hai

### B. Chat/AI ke through add

Ab app ka main flow yahi hai.

`+ Add Task` dabane par direct task create nahi hota.

Uske bajay:

1. `App.jsx` ka `openAddTaskInChat()` run hota hai
2. chat input mein draft text aata hai:
   `Add this task with start date and end date: `
3. user khud apna message likhta hai
4. user send karta hai

## 8. Chat Se Add Kaise Hota Hai

Example:

`add task on work, office report submission tomorrow`

Flow:

1. `ChatPanel.jsx` input leta hai
2. `useChat.js` ka `send()` function run hota hai
3. frontend temporary user message screen par dikhata hai
4. `sendChat(message, history)` backend ko call karta hai
5. backend `POST /chat` receive karta hai

## 9. Backend Chat Endpoint Kya Karta Hai

`backend/main.py` ka `/chat` endpoint:

### Step 1

Database se current tasks load karta hai

### Step 2

Kuch common queries direct backend khud answer karta hai:

- `What is pending?`
- `Show urgent`
- `Show completed`
- `Show today`
- `summary`

Iske liye helper function use hota hai:

- `_maybe_answer_from_tasks()`

Yeh AI ko call kiye bina direct response bana deta hai.

### Step 3

Agar query direct handle nahi ho sakti, tab backend AI ko call karta hai.

## 10. AI Ko Kya Bheja Jaata Hai

AI call `backend/ollama_client.py` mein hota hai.

Backend Ollama ko 3 cheezein bhejta hai:

1. system prompt
2. recent chat history
3. current task list

Phir current user message bhi bhejta hai.

Yaani AI ko context milta hai:

- abhi kaunsa task list mein hai
- user ne pehle kya bola
- abhi kya bola

## 11. AI Ka System Prompt Kya Bolta Hai

`backend/prompt.py` AI ko instruct karta hai:

- agar user action bol raha hai to raw JSON return karo
- due date ko `YYYY-MM-DD` mein convert karo
- tag infer karo
- priority infer karo
- plain baat ho to short normal text do

Example AI JSON:

```json
{"action":"add","task":{"title":"Office report submission","tag":"work","due_date":"2026-05-25","priority":3},"message":"Task added successfully"}
```

## 12. AI Response Ke Baad Kya Hota Hai

Backend `ollama_client.py` se AI response paata hai.

Agar response JSON action hai:

- `add`
- `complete`
- `delete`
- `edit`
- `list`
- `summary`

to backend usko parse karta hai aur actual DB operation khud karta hai.

Important:

AI khud database mein kuch save nahi karta.

AI sirf bolta hai kya karna hai.

Actual save/delete/edit backend karta hai.

## 13. Add Action Ka Exact Flow

Jab AI `action = add` return karta hai:

1. backend title, due date, tag, priority padhta hai
2. `_clean_task_title()` title ko sanitize karta hai
3. new `Task(...)` object banta hai
4. SQLite DB mein save hota hai
5. response frontend ko wapas jaata hai
6. frontend `refresh()` call karke nayi list fetch karta hai

## 14. Title Clean Kyu Kiya Jaata Hai

`_clean_task_title()` ka use isliye hai:

agar AI title mein `tomorrow`, `tommorow`, `today` jaise words chhod de,
aur due date already proper field mein save ho rahi ho,
to title se woh extra word hata diya jaata hai.

Example:

- input: `Office Report Submission for Tomorrow`
- saved title: `Office Report Submission`
- due_date alag field mein save hoti hai

## 15. Pending / Summary Reply Kaise Aata Hai

Ab kuch replies AI guess se nahi aate.

Backend direct DB dekh kar banata hai.

Example:

### `What is pending?`

Backend pending tasks count aur titles nikalta hai.

Example response:

`3 pending tasks: Buy groceries, Buy milk, Submit report.`

### `summary`

Backend counts nikalta hai:

- total
- pending
- completed
- urgent
- due today

## 16. Chat History Kaise Save Hoti Hai

Har chat exchange DB mein save hota hai:

- user message
- assistant message

Yeh `chat_history` table mein store hota hai.

Frontend `useChat.js` mount par history load karta hai.

Kuch old canned messages intentionally hide kiye gaye hain taaki UI clean lage.

## 17. Task List Screen Par Kaise Banti Hai

`TaskList.jsx`:

- active filter ke hisaab se tasks filter karta hai
- sort option apply karta hai
- pending aur completed groups alag dikhata hai

`TaskCard.jsx`:

- title dikhata hai
- tag dikhata hai
- due date relative form mein dikhata hai
- priority dots dikhata hai
- checkbox aur delete handle karta hai

## 18. Sidebar Ka Kaam

`Sidebar.jsx`:

- pending / done / total counts
- filters
- tag-based filter
- export JSON / CSV
- clear done / clear all
- model status

## 19. Ollama Status Kaise Check Hota Hai

Frontend `App.jsx` har 15 second mein backend se `GET /ollama-status` call karta hai.

Backend `ollama_client.py` ke through check karta hai:

- server reachable hai ya nahi
- requested model available hai ya nahi

## 20. Error Case Mein Kya Hota Hai

Agar frontend backend se connect nahi kar paata:

- `useChat.js` error message show karta hai

Agar backend Ollama se connect nahi kar paata:

- `ollama_client.py` fallback error text return karta hai

## 21. Short End-to-End Example

User message:

`add task on work, office report submission tomorrow`

End-to-end:

1. user chat mein message likhta hai
2. frontend backend ko bhejta hai
3. backend tasks + history + prompt ke saath AI ko call karta hai
4. AI JSON action return karta hai
5. backend action parse karta hai
6. backend task DB mein save karta hai
7. backend confirmation bhejta hai
8. frontend task list refresh karta hai
9. new task UI mein dikh jaata hai

## 22. Sabse Important Baat

AI se task add hone ka matlab:

- AI instruction samajhta hai
- backend us instruction ko validate/process karta hai
- DB mein actual save backend karta hai

Matlab:

- frontend = screen aur user interaction
- backend = logic aur saving
- Ollama AI = natural language ko structured action mein badalna
- SQLite = permanent storage

