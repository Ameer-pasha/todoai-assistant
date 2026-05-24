import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


async def chat_with_ollama(user_message: str, history: list, tasks_summary: str) -> dict:
    """
    Call Ollama API and return structured result.
    Returns: {"type": "action"|"text", "data": parsed_json | string}
    """
    from prompt import build_system_prompt

    system_prompt = build_system_prompt()

    messages = [{"role": "system", "content": system_prompt}]

    # Add last 10 history messages for context
    for msg in history[-10:]:
        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

    # Append current tasks context + user message
    full_message = f"Current tasks in database:\n{tasks_summary}\n\nUser says: {user_message}"
    messages.append({"role": "user", "content": full_message})

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            res = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                },
            )
            res.raise_for_status()

        raw = res.json()["message"]["content"].strip()

        # Try to parse as JSON action
        try:
            clean = raw.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean)
            if "action" in parsed:
                return {"type": "action", "data": parsed}
        except (json.JSONDecodeError, KeyError):
            pass

        return {"type": "text", "data": raw}

    except httpx.ConnectError:
        return {
            "type": "text",
            "data": "⚠️ Cannot connect to Ollama. Is it running? Start with: `ollama serve`",
        }
    except httpx.TimeoutException:
        return {
            "type": "text",
            "data": "⏱️ Ollama timed out. The model might be loading — try again in a moment.",
        }
    except Exception as e:
        return {
            "type": "text",
            "data": f"⚠️ Ollama error: {str(e)}",
        }


async def check_ollama_status() -> dict:
    """Check if Ollama server is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(f"{OLLAMA_URL}/api/tags")
            if res.status_code == 200:
                models = res.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                return {
                    "reachable": True,
                    "model": OLLAMA_MODEL,
                    "available": OLLAMA_MODEL in model_names or any(OLLAMA_MODEL in n for n in model_names),
                    "models": model_names,
                }
    except Exception:
        pass
    return {"reachable": False, "model": OLLAMA_MODEL, "available": False, "models": []}
