import { useState, useCallback, useEffect } from 'react'
import Sidebar from '../components/Sidebar'
import ChatWindow from '../components/ChatWindow'
import InputBar from '../components/InputBar'
import { sendMessage, sendAudio, createSession, listSessions, getSessionHistory } from '../services/api'

/**
 * Main chatbot page with Sidebar + Chat Window + Input Bar.
 *
 * State management:
 * - sessions[]       → list of all chat sessions for the sidebar
 * - activeSessionId  → currently selected session UUID
 * - messages[]       → messages in the current session
 * - uiState          → 'idle' | 'loading' | 'recording'
 */
export default function ChatbotPage() {
    const [sessions, setSessions] = useState([])
    const [activeSessionId, setActiveSessionId] = useState(null)
    const [messages, setMessages] = useState([])
    const [uiState, setUiState] = useState('idle') // idle | loading | recording

    // ── Load sessions from backend on mount ──────────────────
    useEffect(() => {
        listSessions()
            .then((data) => {
                if (data.sessions?.length) {
                    setSessions(data.sessions)
                }
            })
            .catch(() => {
                // Backend not running yet — that's fine
            })
    }, [])

    // ── Helper: add a message locally ────────────────────────
    const appendMessage = useCallback((role, content, meta = null) => {
        setMessages((prev) => [...prev, { role, content, meta }])
    }, [])

    // ── Helper: update session list with last message ────────
    const updateSessionTitle = useCallback(
        (sessionId, lastMessage) => {
            setSessions((prev) =>
                prev.map((s) =>
                    s.id === sessionId
                        ? { ...s, title: s.title || lastMessage.slice(0, 40), lastMessage: lastMessage.slice(0, 60) }
                        : s,
                ),
            )
        },
        [],
    )

    // ── Create or ensure a session exists ────────────────────
    const ensureSession = useCallback(async () => {
        if (activeSessionId) return activeSessionId

        try {
            const { session_id } = await createSession()
            const newSession = { id: session_id, title: '', lastMessage: '' }
            setSessions((prev) => [newSession, ...prev])
            setActiveSessionId(session_id)
            setMessages([])
            return session_id
        } catch {
            // Fallback: create a local-only session for demo purposes
            const localId = crypto.randomUUID()
            const newSession = { id: localId, title: '', lastMessage: '' }
            setSessions((prev) => [newSession, ...prev])
            setActiveSessionId(localId)
            setMessages([])
            return localId
        }
    }, [activeSessionId])

    // ── New Chat ─────────────────────────────────────────────
    const handleNewChat = useCallback(() => {
        setActiveSessionId(null)
        setMessages([])
        setUiState('idle')
    }, [])

    // ── Select Session (loads history from MySQL) ────────────
    const handleSelectSession = useCallback(
        async (sessionId) => {
            setActiveSessionId(sessionId)
            setMessages([])
            setUiState('idle')

            try {
                const data = await getSessionHistory(sessionId)
                if (data.messages?.length) {
                    setMessages(
                        data.messages.map((m) => ({
                            role: m.role,
                            content: m.content,
                            meta: m.metadata || null,
                        })),
                    )
                }
            } catch {
                // If history fetch fails, start fresh
            }
        },
        [],
    )

    // ── Send Text Message ────────────────────────────────────
    const handleSendText = useCallback(
        async (text) => {
            const sessionId = await ensureSession()
            appendMessage('user', text)
            updateSessionTitle(sessionId, text)
            setUiState('loading')

            try {
                const res = await sendMessage(sessionId, text)
                appendMessage('assistant', res.answer, { source: res.source })
            } catch {
                appendMessage('assistant', "I'm having trouble connecting to the server. Please make sure the backend is running.")
            } finally {
                setUiState('idle')
            }
        },
        [ensureSession, appendMessage, updateSessionTitle],
    )

    // ── Send Audio ───────────────────────────────────────────
    const handleSendAudio = useCallback(
        async (audioBlob) => {
            const sessionId = await ensureSession()
            appendMessage('user', '🎤 [Audio message]')
            updateSessionTitle(sessionId, '🎤 Voice message')
            setUiState('loading')

            try {
                const res = await sendAudio(sessionId, audioBlob)
                // Update the user message with transcription + translation
                setMessages((prev) => {
                    const updated = [...prev]
                    const lastUserIdx = updated.findLastIndex((m) => m.role === 'user')
                    if (lastUserIdx >= 0) {
                        updated[lastUserIdx] = {
                            ...updated[lastUserIdx],
                            content: res.translation || res.transcription || '🎤 [Audio]',
                            meta: { transcription: res.transcription },
                        }
                    }
                    return updated
                })
                appendMessage('assistant', res.answer, { source: res.source })
            } catch {
                appendMessage('assistant', "I'm having trouble processing the audio. Ensure the backend is running on port 8000.")
            } finally {
                setUiState('idle')
            }
        },
        [ensureSession, appendMessage, updateSessionTitle],
    )

    return (
        <div className="flex h-screen bg-[var(--color-surface)]">
            {/* Sidebar */}
            <Sidebar
                sessions={sessions}
                activeSessionId={activeSessionId}
                onNewChat={handleNewChat}
                onSelectSession={handleSelectSession}
            />

            {/* Main chat area */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* Header bar */}
                <header className="flex items-center justify-between px-6 py-3 border-b border-[var(--color-border)] bg-[var(--color-surface-light)]/60 backdrop-blur-md">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center">
                            <span className="text-white text-xs font-bold">AI</span>
                        </div>
                        <div>
                            <h2 className="text-sm font-semibold text-[var(--color-text)]">AI Chatbot Assistant</h2>
                            <p className="text-[10px] text-[var(--color-text-muted)]">
                                {uiState === 'loading' ? '⏳ Thinking...' : '🟢 Online'}
                            </p>
                        </div>
                    </div>
                    {activeSessionId && (
                        <span className="text-[10px] text-[var(--color-text-muted)] font-mono">
                            {activeSessionId.slice(0, 8)}
                        </span>
                    )}
                </header>

                {/* Chat window */}
                <ChatWindow
                    messages={messages}
                    isLoading={uiState === 'loading'}
                    isIdle={uiState === 'idle'}
                />

                {/* Input bar */}
                <InputBar
                    onSendText={handleSendText}
                    onSendAudio={handleSendAudio}
                    disabled={uiState === 'loading'}
                />
            </div>
        </div>
    )
}
