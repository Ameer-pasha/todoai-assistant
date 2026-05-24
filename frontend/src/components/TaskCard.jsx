import React, { useState } from 'react';

const TAG_COLORS = {
  work:     { bg: '#DCEEFF', color: '#0D3B66', border: '#8DC0F7' },
  personal: { bg: '#EEF5FF', color: '#204E7A', border: '#BDD7F5' },
  urgent:   { bg: '#E7F1FF', color: '#123A62', border: '#7DAFE8' },
};

const PRIORITY_CONFIG = {
  5: { label: 'Critical', color: '#EF4444', dots: 5 },
  4: { label: 'High',     color: '#F97316', dots: 4 },
  3: { label: 'Medium',   color: '#F59E0B', dots: 3 },
  2: { label: 'Low',      color: '#22C55E', dots: 2 },
  1: { label: 'Minimal',  color: '#6B7280', dots: 1 },
};

function formatDueDate(date) {
  if (!date) return null;
  const d = new Date(date + 'T00:00:00');
  const today = new Date(); today.setHours(0,0,0,0);
  const diff = Math.round((d - today) / 86400000);
  if (diff === 0) return 'Today';
  if (diff === 1) return 'Tomorrow';
  if (diff === -1) return 'Yesterday';
  if (diff < -1) return `${Math.abs(diff)}d overdue`;
  if (diff <= 7) return `${diff}d left`;
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

function isOverdue(date) {
  if (!date) return false;
  const d = new Date(date + 'T00:00:00');
  const today = new Date(); today.setHours(0,0,0,0);
  return d < today;
}

export default function TaskCard({ task, onToggle, onEdit, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(task.title);
  const tagColor = TAG_COLORS[task.tag] || TAG_COLORS.personal;
  const prio = PRIORITY_CONFIG[task.priority] || PRIORITY_CONFIG[3];
  const overdue = isOverdue(task.due_date) && !task.done;

  const handleSave = () => {
    if (editTitle.trim() && editTitle !== task.title) {
      onEdit(task.id, { title: editTitle.trim() });
    }
    setEditing(false);
  };

  return (
    <div className={`task-card fade-in ${task.done ? 'task-card-done' : ''} ${overdue ? 'task-card-overdue' : ''}`}>
      {/* Checkbox */}
      <button className={`task-check ${task.done ? 'task-check-done' : ''}`} onClick={() => onToggle(task.id, task.done)}>
        {task.done && <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>}
      </button>

      {/* Content */}
      <div className="task-card-body" onDoubleClick={() => { setEditing(true); setEditTitle(task.title); }}>
        {editing ? (
          <input className="task-edit-input" value={editTitle} onChange={e => setEditTitle(e.target.value)} onBlur={handleSave} onKeyDown={e => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') setEditing(false); }} autoFocus />
        ) : (
          <span className={`task-title ${task.done ? 'task-title-done' : ''}`}>{task.title}</span>
        )}

        <div className="task-meta">
          <span className="task-tag" style={{ background: tagColor.bg, color: tagColor.color, borderColor: tagColor.border }}>{task.tag}</span>

          {task.due_date && (
            <span className={`task-due ${overdue ? 'task-due-overdue' : ''}`}>
              Due {formatDueDate(task.due_date)}
            </span>
          )}

          {/* Priority dots */}
          <span className="task-priority" title={prio.label}>
            {Array.from({ length: prio.dots }).map((_, i) => (
              <span key={i} style={{ width: 5, height: 5, borderRadius: '50%', background: prio.color, display: 'inline-block', marginRight: 1 }} />
            ))}
          </span>
        </div>
      </div>

      {/* Delete */}
      <button className="task-delete-btn" onClick={() => onDelete(task.id)} title="Delete" aria-label="Delete task">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M18 6 6 18" />
          <path d="M6 6 18 18" />
        </svg>
      </button>
    </div>
  );
}
