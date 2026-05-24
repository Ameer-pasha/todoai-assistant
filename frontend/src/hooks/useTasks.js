import { useState, useCallback, useEffect, useRef } from 'react';
import { fetchTasks, createTask, updateTask, deleteTask, clearCompleted, clearAllTasks } from '../api';

export function useTasks() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const refreshRef = useRef(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchTasks();
      setTasks(data);
    } catch (err) {
      console.error('Failed to fetch tasks:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const add = useCallback(async (taskData) => {
    const t = await createTask({
      title: taskData.title,
      tag: taskData.tag || 'personal',
      due_date: taskData.due_date || null,
      priority: taskData.priority || 3,
    });
    await refresh();
    return t;
  }, [refresh]);

  const toggle = useCallback(async (id, done) => {
    await updateTask(id, { done: !done });
    await refresh();
  }, [refresh]);

  const edit = useCallback(async (id, updates) => {
    await updateTask(id, updates);
    await refresh();
  }, [refresh]);

  const remove = useCallback(async (id) => {
    await deleteTask(id);
    await refresh();
  }, [refresh]);

  const clearDone = useCallback(async () => {
    await clearCompleted();
    await refresh();
  }, [refresh]);

  const clearAll = useCallback(async () => {
    await clearAllTasks();
    await refresh();
  }, [refresh]);

  return { tasks, loading, refresh, add, toggle, edit, remove, clearDone, clearAll };
}
