const SESSION_STORAGE_KEY = "build4galileo-session-id";

/** One id per browser conversation, kept in sessionStorage so a refresh
 * survives but a new tab starts fresh — matches "one browser conversation
 * = one Galileo session" on the backend (see b4g_core.agents.session). */
export function getOrCreateSessionId(): string {
  const existing = sessionStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) {
    return existing;
  }
  const created = crypto.randomUUID();
  sessionStorage.setItem(SESSION_STORAGE_KEY, created);
  return created;
}
