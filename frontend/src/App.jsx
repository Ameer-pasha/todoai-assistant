import { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import DashboardPanel from './components/DashboardPanel';
import TaskList from './components/TaskList';
import ChatPanel from './components/ChatPanel';
import { useTasks } from './hooks/useTasks';
import { useChat } from './hooks/useChat';
import { getOllamaStatus } from './api';

export default function App() {
  const {
    tasks, loading, refresh, add, toggle, edit, remove, clearDone, clearAll,
  } = useTasks();

  const { messages, loading: chatLoading, send, clear: clearChat } = useChat(refresh);

  const [activeFilter, setActiveFilter] = useState('dashboard');
  const [ollamaStatus, setOllamaStatus] = useState({ reachable: false, model: 'llama3.2' });
  const [chatDraft, setChatDraft] = useState('');
  const [chatDraftRequest, setChatDraftRequest] = useState(0);
  const [manualAddOpen, setManualAddOpen] = useState(false);

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

  useEffect(() => {
    const handler = (e) => {
      if (e.key === '/' && !e.target.closest('input, textarea, select')) {
        e.preventDefault();
        document.getElementById('chat-input')?.focus();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

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

  const openManualAddTask = useCallback(() => {
    setManualAddOpen(true);
  }, []);

  const closeManualAddTask = useCallback(() => {
    setManualAddOpen(false);
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

      <div className="main-panel">
        {activeFilter === 'dashboard' ? (
          <DashboardPanel
            tasks={tasks}
            onFilterChange={setActiveFilter}
          />
        ) : (
          <TaskList
            tasks={tasks}
            loading={loading}
            activeFilter={activeFilter}
            onToggle={toggle}
            onEdit={edit}
            onDelete={remove}
            onStartAddTask={openManualAddTask}
            onAddTask={add}
            addTaskOpen={manualAddOpen}
            onCloseAddTask={closeManualAddTask}
          />
        )}
      </div>

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
