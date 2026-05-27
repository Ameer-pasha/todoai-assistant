import React, { useState, useRef, useEffect } from 'react';
import './ChatPanel.css';

const SUGGESTIONS = [
  'Add submit report tomorrow urgent',
  'Show my pending tasks',
  'Mark work tasks done',
  'Delete every task',
  'What should I do today?',
];

const CAPABILITIES = [
  {
    title: 'Add Tasks',
    text: 'Create tasks from natural language with title, tag, due date, and priority.',
  },
  {
    title: 'Track Progress',
    text: 'Show pending, urgent, completed, or today tasks in simple language.',
  },
  {
    title: 'Update Tasks',
    text: 'Mark tasks done, edit them, or help you clean up your list faster.',
  },
  {
    title: 'Delete Safely',
    text: 'Understand commands like delete all, clear completed, or remove urgent tasks.',
  },
];

export default function ChatPanel({ messages, loading, draftText, draftRequest, onSend, onClear, onStartAddTask, model }) {
  const [input, setInput] = useState('');
  const endRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  useEffect(() => {
    if (!draftRequest) return;
    setInput(draftText || '');
    requestAnimationFrame(() => {
      inputRef.current?.focus();
      const length = (draftText || '').length;
      inputRef.current?.setSelectionRange(length, length);
    });
  }, [draftRequest, draftText]);

  const handleSend = () => {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput('');
    onSend(msg);
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const fillSuggestion = (text) => {
    setInput(text);
    requestAnimationFrame(() => inputRef.current?.focus());
  };

  const showGuide = messages.length <= 2;

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <div className="chat-ai-icon">AI</div>
        <div>
          <div className="chat-header-title">TodoAI Assistant</div>
          <div className="chat-header-sub">Smart task help with {model || 'llama3.2'}</div>
        </div>
        <button className="chat-clear-btn" onClick={onClear} title="Clear chat">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="1 4 1 10 7 10" /><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" /></svg>
        </button>
      </div>

      <div className="chat-messages">
        {showGuide && (
          <div className="assistant-guide fade-in">
            <div className="assistant-guide-top">
              <div>
                <h3>Make the assistant work for you</h3>
                <p>Type naturally. I can understand task requests, summaries, and status changes.</p>
              </div>
              <button className="assistant-guide-action" onClick={onStartAddTask}>Start Add Flow</button>
            </div>

            <div className="assistant-capabilities">
              {CAPABILITIES.map((item) => (
                <div key={item.title} className="assistant-capability-card">
                  <strong>{item.title}</strong>
                  <span>{item.text}</span>
                </div>
              ))}
            </div>

            <div className="assistant-suggestion-block">
              <div className="assistant-suggestion-label">Try asking</div>
              <div className="assistant-suggestion-list">
                {SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    className="assistant-suggestion-chip"
                    onClick={() => fillSuggestion(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>

            <div className="assistant-flow-card">
              <strong>How it works</strong>
              <p>
                You type something like <code>Add submit report tomorrow urgent</code>, the assistant reads it,
                backend converts it into a task action, saves it, and your task list refreshes.
              </p>
            </div>
          </div>
        )}

        {messages.map((m) => (
          <div key={m.id} className={`chat-msg ${m.from === 'user' ? 'chat-msg-user' : 'chat-msg-ai'}`}>
            <div className={`chat-bubble ${m.from === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'}`}>
              {m.text}
            </div>
            <div className="chat-ts">{formatTime(m.ts)}</div>
          </div>
        ))}

        {loading && (
          <div className="chat-msg chat-msg-ai">
            <div className="chat-bubble chat-bubble-ai">
              <span className="dot" /><span className="dot" /><span className="dot" />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="chat-input-row">
        <textarea
          id="chat-input"
          ref={inputRef}
          className="chat-textarea"
          placeholder="Ask to add, show, update, or summarize tasks"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          rows={2}
          disabled={loading}
        />
        <button className="chat-send" onClick={handleSend} disabled={!input.trim() || loading}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
        </button>
      </div>
    </div>
  );
}

function formatTime(ts) {
  if (!ts) return '';
  const d = typeof ts === 'number' ? new Date(ts) : new Date(ts);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
