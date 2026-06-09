const STORAGE_KEY = 'a2a-legal-chat-sessions'
const ACTIVE_KEY = 'a2a-legal-active-session'
const MAX_SESSIONS = 30

export function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

function readSessions() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function writeSessions(sessions) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions.slice(0, MAX_SESSIONS)))
}

export function loadActiveSessionId() {
  return localStorage.getItem(ACTIVE_KEY) || null
}

export function saveActiveSessionId(contextId) {
  localStorage.setItem(ACTIVE_KEY, contextId)
}

export function getSession(contextId) {
  return readSessions().find((s) => s.contextId === contextId) || null
}

export function upsertSession(session) {
  const sessions = readSessions().filter((s) => s.contextId !== session.contextId)
  sessions.unshift({
    ...session,
    updatedAt: new Date().toISOString(),
  })
  writeSessions(sessions)
}

export function deleteSession(contextId) {
  writeSessions(readSessions().filter((s) => s.contextId !== contextId))
  if (loadActiveSessionId() === contextId) {
    localStorage.removeItem(ACTIVE_KEY)
  }
}

export function listSessions() {
  return readSessions().sort(
    (a, b) => new Date(b.updatedAt) - new Date(a.updatedAt)
  )
}

export function sessionTitleFromMessages(messages) {
  const firstUser = messages.find((m) => m.role === 'user')
  if (!firstUser?.text) return 'Cuộc hội thoại mới'
  const text = firstUser.text.trim()
  return text.length > 42 ? `${text.slice(0, 42)}…` : text
}

export function createEmptySession() {
  return {
    contextId: generateUUID(),
    messages: [],
    title: 'Cuộc hội thoại mới',
    updatedAt: new Date().toISOString(),
  }
}
