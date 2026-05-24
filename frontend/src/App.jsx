import { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import TaskList from './components/TaskList';
import ChatPanel from './components/ChatPanel';
import { useTasks } from './hooks/useTasks';
import { useChat } from './hooks/useChat';
import { getOllamaStatus } from './api';

export default function App() {
  const {
    tasks, loading, refresh, toggle, edit, remove, clearDone, clearAll,
  } = useTasks();

  const { messages, loading: chatLoading, send, clear: clearChat } = useChat(refresh);

  const [activeFilter, setActiveFilter] = useState('all');
  const [ollamaStatus, setOllamaStatus] = useState({ reachable: false, model: 'llama3.2' });
  const [chatDraft, setChatDraft] = useState('');
  const [chatDraftRequest, setChatDraftRequest] = useState(0);

  // Check Ollama status periodically
  useEffect(() => {
    const check = async () => {
      try {
        const s = await getOllamaStatus();
        setOllamaStatus(s);
      } catch {
        setOllamaStatus({ reachable: false, model: 'llama3.2' });
      }
    };
    check();
    const iv = setInterval(check, 15000);
    return () => clearInterval(iv);
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e) => {
      // `/` to focus chat input
      if (e.key === '/' && !e.target.closest('input, textarea, select')) {
        e.preventDefault();
        document.getElementById('chat-input')?.focus();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Handle chat send — process filter switching
  const handleChatSend = useCallback(async (text) => {
    const result = await send(text);
    if (result?.type === 'action' && result.filter) {
      setActiveFilter(result.filter);
    }
  }, [send]);

  const openAddTaskInChat = useCallback(() => {
    setChatDraft('Add this task with start date and end date: ');
    setChatDraftRequest((value) => value + 1);
  }, []);

  return (
    <div className="app">
      <Sidebar
        tasks={tasks}
        activeFilter={activeFilter}
        onFilterChange={setActiveFilter}
        onClearCompleted={clearDone}
        onClearAll={clearAll}
        ollamaStatus={ollamaStatus}
      />

      <TaskList
        tasks={tasks}
        loading={loading}
        activeFilter={activeFilter}
        onToggle={toggle}
        onEdit={edit}
        onDelete={remove}
        onStartAddTask={openAddTaskInChat}
      />

      <ChatPanel
        messages={messages}
        loading={chatLoading}
        onSend={handleChatSend}
        onStartAddTask={openAddTaskInChat}
        draftText={chatDraft}
        draftRequest={chatDraftRequest}
        onClear={clearChat}
        model={ollamaStatus.model}
      />
    </div>
  );
}
