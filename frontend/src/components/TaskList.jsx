import React, { useState, useMemo } from 'react';
import TaskCard from './TaskCard';
import './TaskList.css';

const FILTER_LABELS = {
  all: 'All Tasks', today: "Today's Tasks", pending: 'Pending Tasks',
  urgent: 'Urgent Tasks', done: 'Completed Tasks', work: 'Work Tasks', personal: 'Personal Tasks',
};

export default function TaskList({ tasks, loading, activeFilter, onToggle, onEdit, onDelete, onStartAddTask }) {
  const [sortBy, setSortBy] = useState('newest');

  const filtered = useMemo(() => {
    const today = new Date().toISOString().split('T')[0];
    switch (activeFilter) {
      case 'pending':  return tasks.filter(t => !t.done);
      case 'done':     return tasks.filter(t => t.done);
      case 'today':    return tasks.filter(t => t.due_date === today);
      case 'work':
      case 'personal':
      case 'urgent':   return tasks.filter(t => t.tag === activeFilter);
      default:         return tasks;
    }
  }, [tasks, activeFilter]);

  const sorted = useMemo(() => {
    const copy = [...filtered];
    switch (sortBy) {
      case 'tag':    return copy.sort((a, b) => a.tag.localeCompare(b.tag));
      case 'date':   return copy.sort((a, b) => (a.due_date || 'z').localeCompare(b.due_date || 'z'));
      case 'alpha':  return copy.sort((a, b) => a.title.localeCompare(b.title));
      case 'prio':   return copy.sort((a, b) => b.priority - a.priority);
      default:       return copy.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));
    }
  }, [filtered, sortBy]);

  const pendingTasks = sorted.filter(t => !t.done);
  const doneTasks = sorted.filter(t => t.done);

  if (loading && tasks.length === 0) {
    return <div className="task-list-container"><div className="task-empty"><div className="task-empty-icon">...</div><h3>Loading tasks...</h3></div></div>;
  }

  return (
    <div className="task-list-container">
      {/* Header */}
      <div className="task-list-header">
        <div className="task-list-title-row">
          <h2 className="task-list-title">{FILTER_LABELS[activeFilter] || 'All Tasks'}</h2>
          <span className="task-list-count">{sorted.length} task{sorted.length !== 1 ? 's' : ''}</span>
        </div>
        <div className="task-list-controls">
          <button className="add-task-btn" onClick={onStartAddTask}>+ Add Task</button>
          <select className="sort-select" value={sortBy} onChange={e => setSortBy(e.target.value)}>
            <option value="newest">Newest First</option>
            <option value="prio">By Priority</option>
            <option value="tag">By Tag</option>
            <option value="date">Due Date</option>
            <option value="alpha">A → Z</option>
          </select>
        </div>
      </div>

      {/* Tasks */}
      <div className="task-list-scroll">
        {sorted.length === 0 && (
          <div className="task-empty fade-in">
            <div className="task-empty-icon">No Tasks</div>
            <h3>No tasks here</h3>
            <p>Use Add Task to draft a request in chat.</p>
          </div>
        )}

        {pendingTasks.length > 0 && (
          <div className="task-group">
            <div className="task-group-label">Pending <span className="group-count">{pendingTasks.length}</span></div>
            {pendingTasks.map(t => <TaskCard key={t.id} task={t} onToggle={onToggle} onEdit={onEdit} onDelete={onDelete} />)}
          </div>
        )}

        {doneTasks.length > 0 && (
          <div className="task-group">
            <div className="task-group-label">Completed <span className="group-count">{doneTasks.length}</span></div>
            {doneTasks.map(t => <TaskCard key={t.id} task={t} onToggle={onToggle} onEdit={onEdit} onDelete={onDelete} />)}
          </div>
        )}
      </div>
    </div>
  );
}
