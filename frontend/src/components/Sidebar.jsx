import React, { useMemo } from 'react';
import { exportTasks } from '../api';
import { taskHasTag } from '../utils/taskTags';

const TAG_COLORS = {
  work: { bg: '#e9f6f1', color: '#171a45', border: '#63b995' },
  personal: { bg: '#f0ecff', color: '#171a45', border: '#a78bfa' },
  urgent: { bg: '#fff0f5', color: '#171a45', border: '#ee5f8b' },
};

export default function Sidebar({ tasks, activeFilter, onFilterChange, onClearCompleted, onClearAll, ollamaStatus }) {
  const pending = useMemo(() => tasks.filter((t) => !t.done).length, [tasks]);
  const done = useMemo(() => tasks.filter((t) => t.done).length, [tasks]);
  const tagCounts = useMemo(() => {
    const c = { work: 0, personal: 0, urgent: 0 };
    tasks.forEach((t) => {
      if (taskHasTag(t, 'work')) c.work++;
      if (taskHasTag(t, 'personal')) c.personal++;
      if (taskHasTag(t, 'urgent')) c.urgent++;
    });
    return c;
  }, [tasks]);

  const handleExport = async (fmt) => {
    try {
      const data = await exportTasks(fmt);
      const content = fmt === 'csv' ? data.csv : JSON.stringify(data, null, 2);
      const blob = new Blob([content], { type: fmt === 'csv' ? 'text/csv' : 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tasks.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {}
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
          </svg>
        </div>
        <div className="logo-text">
          <span className="logo-name">TodoAI</span>
          <span className="logo-sub">Smart Tasks</span>
        </div>
      </div>

      <div className="stats-box">
        <div className="stat"><div className="stat-label">Pending</div><div className="stat-value stat-value-light">{pending}</div></div>
        <div className="stat-div" />
        <div className="stat"><div className="stat-label">Done</div><div className="stat-value stat-value-blue">{done}</div></div>
        <div className="stat-div" />
        <div className="stat"><div className="stat-label">Total</div><div className="stat-value stat-value-dark">{tasks.length}</div></div>
      </div>

      <div className="sidebar-section">Views</div>
      {[
        { key: 'dashboard', label: 'Dashboard', count: null },
        { key: 'all', label: 'All Tasks', count: tasks.length },
        { key: 'pending', label: 'Pending', count: pending },
        { key: 'done', label: 'Completed', count: done },
      ].map((f) => (
        <button key={f.key} className={`nav-btn ${activeFilter === f.key ? 'nav-btn-active' : ''}`} onClick={() => onFilterChange(f.key)}>
          <span className="nav-icon" />
          <span className="nav-label">{f.label}</span>
          {f.count !== null && <span className="nav-count">{f.count}</span>}
        </button>
      ))}

      <div className="sidebar-section">Tags</div>
      {['work', 'personal', 'urgent'].map((tag) => {
        const c = TAG_COLORS[tag];
        return (
          <button key={tag} className={`nav-btn ${activeFilter === tag ? 'nav-btn-active' : ''}`} onClick={() => onFilterChange(tag)}>
            <span className="tag-dot" style={{ background: c.border }} />
            <span className="nav-label" style={{ textTransform: 'capitalize' }}>{tag}</span>
            <span className="nav-count">{tagCounts[tag]}</span>
          </button>
        );
      })}

      <div style={{ flex: 1 }} />

      <div className="sidebar-section">Export</div>
      <div className="export-row">
        <button className="export-btn" onClick={() => handleExport('json')}>JSON</button>
        <button className="export-btn" onClick={() => handleExport('csv')}>CSV</button>
      </div>

      <div className="sidebar-actions">
        <button className="sidebar-action" onClick={onClearCompleted}>Clear Done</button>
        <button className="sidebar-action sidebar-action-danger" onClick={onClearAll}>Clear All</button>
      </div>

      <div className="sidebar-footer">
        <span className={`status-dot ${ollamaStatus.reachable ? 'status-on' : 'status-off'}`} />
        <span>Model: {ollamaStatus.model}</span>
      </div>
    </aside>
  );
}
