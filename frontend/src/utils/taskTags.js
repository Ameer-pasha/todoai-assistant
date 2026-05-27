export function getTaskTags(task) {
  return String(task?.tag || 'personal')
    .split('|')
    .map((part) => part.trim().toLowerCase())
    .filter(Boolean);
}

export function taskHasTag(task, tag) {
  return getTaskTags(task).includes(String(tag || '').trim().toLowerCase());
}

export function getPrimaryTaskTag(task) {
  const tags = getTaskTags(task);
  return tags[0] || 'personal';
}
