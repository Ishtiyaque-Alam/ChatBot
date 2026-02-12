/**
 * API service layer for the chatbot backend.
 *
 * All backend calls are centralized here for easy maintenance.
 * The Vite dev server proxies /api → http://localhost:8000.
 */

const API_BASE = '/api'

/**
 * Create a new chat session.
 * @returns {Promise<{session_id: string}>}
 */
export async function createSession() {
    const res = await fetch(`${API_BASE}/session`, { method: 'POST' })
    if (!res.ok) throw new Error('Failed to create session')
    return res.json()
}

/**
 * Send a text message to the chatbot.
 * @param {string} sessionId
 * @param {string} message
 * @returns {Promise<{answer: string, source: string}>}
 */
export async function sendMessage(sessionId, message) {
    const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message }),
    })
    if (!res.ok) throw new Error('Failed to send message')
    return res.json()
}

/**
 * Send an audio file (recorded or uploaded) to the chatbot.
 * @param {string} sessionId
 * @param {Blob} audioBlob
 * @param {string} language - BCP-47 language code
 * @returns {Promise<{transcription: string, translation: string, answer: string, source: string}>}
 */
export async function sendAudio(sessionId, audioBlob, language = 'hi-IN') {
    const formData = new FormData()
    formData.append('file', audioBlob, 'recording.webm')
    formData.append('session_id', sessionId)
    formData.append('language', language)

    const res = await fetch(`${API_BASE}/chat/audio`, {
        method: 'POST',
        body: formData,
    })
    if (!res.ok) throw new Error('Failed to process audio')
    return res.json()
}

/**
 * Get chat history for a session.
 * @param {string} sessionId
 * @returns {Promise<{messages: Array}>}
 */
export async function getSessionHistory(sessionId) {
    const res = await fetch(`${API_BASE}/session/${sessionId}/history`)
    if (!res.ok) throw new Error('Failed to fetch history')
    return res.json()
}

/**
 * List all sessions.
 * @returns {Promise<{sessions: Array}>}
 */
export async function listSessions() {
    const res = await fetch(`${API_BASE}/sessions`)
    if (!res.ok) throw new Error('Failed to list sessions')
    return res.json()
}
