import { useState, useCallback, useEffect } from 'react';
import { sendChat, getChatHistory, clearChatHistory } from '../api';

const HIDDEN_HISTORY_MESSAGES = new Set([
  'Add a new task',
  'Task added successfully',
  'Add a task:',
  'Add a task: ',
]);

export function useChat(onRefresh) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  // Load history from DB on mount
  useEffect(() => {
    (async () => {
      try {
        const history = await getChatHistory();
        const visibleHistory = history.filter(h => !HIDDEN_HISTORY_MESSAGES.has((h.content || '').trim()));
        if (visibleHistory.length > 0) {
          setMessages(visibleHistory.map(h => ({
            id: h.id,
            role: h.role === 'assistant' ? 'ai' : 'user',
            from: h.role === 'assistant' ? 'ai' : 'user',
            text: h.content,
            ts: h.timestamp ? new Date(h.timestamp).getTime() : Date.now(),
          })));
        } else {
          setMessages([welcomeMsg()]);
        }
      } catch {
        setMessages([welcomeMsg()]);
      }
    })();
  }, []);

  const send = useCallback(async (text) => {
    const msg = text.trim();
    if (!msg) return null;

    const userMsg = {
      id: `u-${Date.now()}`,
      from: 'user',
      role: 'user',
      text: msg,
      ts: Date.now(),
    };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      // Build history for API
      const history = messages.slice(-10).map(m => ({
        role: m.from === 'user' ? 'user' : 'assistant',
        content: m.text,
      }));

      const result = await sendChat(msg, history);

      // If backend performed an action, refresh tasks
      if (result.refresh) {
        onRefresh();
      }

      const aiMsg = {
        id: `a-${Date.now()}`,
        from: 'ai',
        role: 'assistant',
        text: result.message,
        ts: Date.now(),
      };
      setMessages(prev => [...prev, aiMsg]);

      return result;
    } catch (err) {
      const errMsg = {
        id: `e-${Date.now()}`,
        from: 'ai',
        role: 'assistant',
        text: 'Backend se connect nahi ho paya. FastAPI running hai? (uvicorn main:app --reload --port 8000)',
        ts: Date.now(),
      };
      setMessages(prev => [...prev, errMsg]);
      return null;
    } finally {
      setLoading(false);
    }
  }, [messages, onRefresh]);

  const clear = useCallback(async () => {
    try { await clearChatHistory(); } catch {}
    setMessages([welcomeMsg()]);
  }, []);

  return { messages, loading, send, clear };
}

function welcomeMsg() {
  return {
    id: 'welcome',
    from: 'ai',
    role: 'assistant',
    text: 'TodoAI task assistant is ready.\n\nTry:\n"Add submit report by Friday urgent"\n"Show urgent tasks"\n"Mark all work tasks done"\n"What is pending?"',
    ts: Date.now(),
  };
}
