import React, { useState, useEffect, useRef } from 'react';
import './AddTaskForm.css';

export default function AddTaskForm({ onAdd, onClose, initialTag = 'personal' }) {
  const [title, setTitle] = useState('');
  const [tag, setTag] = useState(initialTag);
  const [priority, setPriority] = useState(3);
  const [dueDate, setDueDate] = useState('');
  const inputRef = useRef(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    onAdd({
      title: title.trim(),
      tag,
      priority,
      due_date: dueDate || null,
    });
    setTitle(''); setTag(initialTag); setPriority(3); setDueDate('');
    onClose();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') onClose();
  };

  return (
    <form className="add-form slide-up" onSubmit={handleSubmit} onKeyDown={handleKeyDown}>
      <input ref={inputRef} className="add-form-input" placeholder="What do you need to do?" value={title} onChange={e => setTitle(e.target.value)} />

      <div className="add-form-row">
        {['personal', 'work', 'urgent'].map(t => (
          <button type="button" key={t} className={`add-tag-btn ${tag === t ? 'add-tag-active' : ''}`} onClick={() => setTag(t)} data-tag={t}>
            {t}
          </button>
        ))}

        <span className="add-form-sep" />

        <select className="add-priority-select" value={priority} onChange={e => setPriority(Number(e.target.value))}>
          <option value={1}>1 – Minimal</option>
          <option value={2}>2 – Low</option>
          <option value={3}>3 – Medium</option>
          <option value={4}>4 – High</option>
          <option value={5}>5 – Critical</option>
        </select>

        <input className="add-date-input" type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} />

        <span className="add-form-sep" />

        <button type="button" className="add-cancel-btn" onClick={onClose}>Cancel</button>
        <button type="submit" className="add-submit-btn">Add</button>
      </div>
    </form>
  );
}
