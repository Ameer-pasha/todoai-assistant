import React, { useEffect, useMemo, useState } from 'react';
import './DashboardPanel.css';
import { taskHasTag } from '../utils/taskTags';

const NOTES_STORAGE_KEY = 'todoai-private-notes';

function formatDate(date) {
  if (!date) return 'No due date';
  const parsed = new Date(`${date}T00:00:00`);
  return parsed.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
  });
}

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

function getPersonalMessage(pending, dueToday, nextTask) {
  if (pending === 0) {
    return 'You are all caught up right now. This is a nice time to plan your next few tasks.';
  }
  if (dueToday > 0) {
    return `You have ${dueToday} task${dueToday !== 1 ? 's' : ''} due today. Finish those first and keep the rest light.`;
  }
  if (nextTask) {
    return `Your next focus should be "${nextTask.title}". Keep momentum there before switching context.`;
  }
  return `You have ${pending} pending task${pending !== 1 ? 's' : ''}. Start with the highest-impact one first.`;
}

export default function DashboardPanel({
  tasks,
  onFilterChange,
}) {
  const [notes, setNotes] = useState('');
  const [notesStatus, setNotesStatus] = useState('Saved locally');

  useEffect(() => {
    try {
      const savedNotes = window.localStorage.getItem(NOTES_STORAGE_KEY);
      if (savedNotes) {
        setNotes(savedNotes);
      }
    } catch {
      // Ignore local storage issues and keep notes in memory only.
    }
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(NOTES_STORAGE_KEY, notes);
      setNotesStatus(notes.trim() ? 'Saved locally' : 'Empty note');
    } catch {
      setNotesStatus('Local save unavailable');
    }
  }, [notes]);

  const stats = useMemo(() => {
    const today = new Date().toISOString().split('T')[0];
    const pending = tasks.filter((task) => !task.done);
    const completed = tasks.filter((task) => task.done);
    const dueToday = pending.filter((task) => task.due_date === today);
    const work = pending.filter((task) => taskHasTag(task, 'work'));
    const personal = pending.filter((task) => taskHasTag(task, 'personal'));
    const urgent = pending.filter((task) => taskHasTag(task, 'urgent'));
    const nextTask = [...pending]
      .filter((task) => task.due_date)
      .sort((a, b) => a.due_date.localeCompare(b.due_date))[0] || pending[0] || null;

    return {
      total: tasks.length,
      pending: pending.length,
      completed: completed.length,
      dueToday: dueToday.length,
      work: work.length,
      personal: personal.length,
      urgent: urgent.length,
      nextTask,
    };
  }, [tasks]);

  const summaryCards = [
    { key: 'pending', label: 'Pending', value: stats.pending, tone: 'blue' },
    { key: 'done', label: 'Done', value: stats.completed, tone: 'dark' },
    { key: 'today', label: 'Due Today', value: stats.dueToday, tone: 'soft' },
    { key: 'all', label: 'Total', value: stats.total, tone: 'white' },
  ];

  const quickViews = [
    { key: 'work', label: 'Work', value: stats.work },
    { key: 'personal', label: 'Personal', value: stats.personal },
    { key: 'urgent', label: 'Urgent', value: stats.urgent },
  ];

  const personalMessage = getPersonalMessage(stats.pending, stats.dueToday, stats.nextTask);

  const chartItems = [
    { key: 'pending', label: 'Pending', value: stats.pending, color: '#8b77e8' },
    { key: 'done', label: 'Done', value: stats.completed, color: '#63b995' },
    { key: 'today', label: 'Today', value: stats.dueToday, color: '#f4a261' },
    { key: 'urgent', label: 'Urgent', value: stats.urgent, color: '#ee5f8b' },
  ];
  const chartMax = Math.max(...chartItems.map((item) => item.value), 1);

  return (
    <section className="dashboard-panel">
      <div className="dashboard-hero">
        <div>
          <p className="dashboard-eyebrow">{getGreeting()}</p>
          <h1 className="dashboard-title">Your dashboard is connected to live tasks</h1>
        </div>
      </div>

      <div className="dashboard-summary-grid">
        {summaryCards.map((card) => (
          <button
            key={card.key}
            className={`dashboard-summary-card dashboard-summary-${card.tone}`}
            onClick={() => onFilterChange(card.key)}
          >
            <span>{card.label}</span>
            <strong>{card.value}</strong>
          </button>
        ))}
      </div>

      <div className="dashboard-main-grid">
        <div className="dashboard-personal-card">
          <div className="dashboard-card-head">
            <h3>Personal Message</h3>
            <span>Live insight</span>
          </div>
          <p>{personalMessage}</p>

          <div className="dashboard-quick-row">
            {quickViews.map((item) => (
              <button key={item.key} className="dashboard-mini-chip" onClick={() => onFilterChange(item.key)}>
                {item.label}
                <span>{item.value}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="dashboard-next-card">
          <div className="dashboard-card-head">
            <h3>Next Focus</h3>
            <span>Connected</span>
          </div>

          {stats.nextTask ? (
            <div className="dashboard-next-task">
              <strong>{stats.nextTask.title}</strong>
              <p>{stats.nextTask.tag || 'personal'}</p>
              <div className="dashboard-next-meta">
                <span>{formatDate(stats.nextTask.due_date)}</span>
                <button onClick={() => onFilterChange('pending')}>Open pending</button>
              </div>
            </div>
          ) : (
            <div className="dashboard-next-empty">
              <strong>No pending task right now</strong>
              <p>Your next focus card will update automatically when a new task is added.</p>
            </div>
          )}
        </div>
      </div>

      <div className="dashboard-features-card">
        <div className="dashboard-card-head">
          <h3>Productivity Tools</h3>
          <span>Working now</span>
        </div>

        <div className="dashboard-features-grid">
          <div className="dashboard-feature-item">
            <strong>Private Notes</strong>
            <p>Keep a personal message or reflection area attached to your day.</p>
            <textarea
              className="dashboard-notes-input"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Write your thoughts, reminders, or quick reflections here..."
            />
            <div className="dashboard-feature-footer">
              <span>{notesStatus}</span>
              <button onClick={() => setNotes('')}>Clear</button>
            </div>
          </div>

          <div className="dashboard-feature-item">
            <strong>Task Bar Graph</strong>
            <p>A quick visual summary of pending, completed, today, and urgent work.</p>
            <div className="dashboard-bar-chart" aria-label="Task summary bar graph">
              {chartItems.map((item) => (
                <button
                  key={item.key}
                  className="dashboard-chart-row"
                  type="button"
                  onClick={() => onFilterChange(item.key)}
                >
                  <span className="dashboard-chart-label">{item.label}</span>
                  <span className="dashboard-chart-track">
                    <span
                      className="dashboard-chart-fill"
                      style={{
                        width: `${Math.max((item.value / chartMax) * 100, item.value > 0 ? 12 : 3)}%`,
                        background: item.color,
                      }}
                    />
                  </span>
                  <strong>{item.value}</strong>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
