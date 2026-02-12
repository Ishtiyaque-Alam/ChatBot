import { useState } from 'react'
import { PlusIcon, ChatBubbleLeftRightIcon } from './Icons'

function ChevronLeftIcon({ className = 'w-4 h-4' }) {
    return (
        <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
        </svg>
    )
}

function ChevronRightIcon({ className = 'w-4 h-4' }) {
    return (
        <svg className={className} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
        </svg>
    )
}

export default function Sidebar({ sessions, activeSessionId, onNewChat, onSelectSession }) {
    const [collapsed, setCollapsed] = useState(false)

    return (
        <aside
            className={`h-screen flex flex-col bg-[var(--color-surface-light)] border-r border-[var(--color-border)]
                   transition-all duration-300 ease-in-out relative
                   ${collapsed ? 'w-16' : 'w-72'}`}
        >
            {/* Collapse / Expand toggle */}
            <button
                onClick={() => setCollapsed(!collapsed)}
                className="absolute -right-3 top-6 z-20 w-6 h-6 rounded-full
                   bg-[var(--color-surface-lighter)] border border-[var(--color-border)]
                   flex items-center justify-center text-[var(--color-text-muted)]
                   hover:bg-indigo-500/20 hover:border-indigo-500/40 hover:text-[var(--color-text)]
                   transition-all duration-200 cursor-pointer shadow-lg"
                title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
                {collapsed ? <ChevronRightIcon className="w-3 h-3" /> : <ChevronLeftIcon className="w-3 h-3" />}
            </button>

            {/* Header — New Chat button */}
            <div className={`p-3 border-b border-[var(--color-border)] ${collapsed ? 'flex justify-center' : ''}`}>
                <button
                    onClick={onNewChat}
                    className={`flex items-center justify-center gap-2 rounded-xl
                     border border-[var(--color-border)] bg-[var(--color-surface-lighter)]
                     text-[var(--color-text)] text-sm font-medium
                     hover:bg-indigo-500/10 hover:border-indigo-500/30
                     transition-all duration-200 cursor-pointer
                     ${collapsed ? 'w-10 h-10 p-0' : 'w-full px-4 py-3'}`}
                    title="New Chat"
                >
                    <PlusIcon className="w-4 h-4 shrink-0" />
                    {!collapsed && <span>New Chat</span>}
                </button>
            </div>

            {/* Session List */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {sessions.length === 0 ? (
                    !collapsed && (
                        <div className="text-center py-12 text-[var(--color-text-muted)] text-sm">
                            <ChatBubbleLeftRightIcon className="w-8 h-8 mx-auto mb-3 opacity-40" />
                            <p>No conversations yet</p>
                            <p className="text-xs mt-1 opacity-70">Start a new chat!</p>
                        </div>
                    )
                ) : (
                    sessions.map((session) => (
                        <button
                            key={session.id}
                            onClick={() => onSelectSession(session.id)}
                            className={`w-full text-left rounded-xl text-sm transition-all duration-200 cursor-pointer
                ${collapsed ? 'p-2.5 flex justify-center' : 'px-3 py-3'}
                ${activeSessionId === session.id
                                    ? 'bg-indigo-500/15 border border-indigo-500/30 text-[var(--color-text)]'
                                    : 'text-[var(--color-text-muted)] hover:bg-[var(--color-surface-lighter)] border border-transparent'
                                }`}
                            title={collapsed ? (session.title || `Chat ${session.id.slice(0, 8)}`) : undefined}
                        >
                            {collapsed ? (
                                <ChatBubbleLeftRightIcon className="w-4 h-4 shrink-0 opacity-70" />
                            ) : (
                                <div className="flex items-center gap-3">
                                    <ChatBubbleLeftRightIcon className="w-4 h-4 shrink-0 opacity-60" />
                                    <div className="min-w-0 flex-1">
                                        <p className="truncate font-medium">
                                            {session.title || `Chat ${session.id.slice(0, 8)}`}
                                        </p>
                                        <p className="text-xs opacity-60 mt-0.5 truncate">
                                            {session.lastMessage || 'Empty conversation'}
                                        </p>
                                    </div>
                                </div>
                            )}
                        </button>
                    ))
                )}
            </div>

            {/* Footer */}
            <div className={`p-3 border-t border-[var(--color-border)] ${collapsed ? 'flex justify-center' : ''}`}>
                <div className={`flex items-center ${collapsed ? '' : 'gap-3'}`}>
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center text-white text-xs font-bold shrink-0">
                        AI
                    </div>
                    {!collapsed && (
                        <div className="text-xs">
                            <p className="text-[var(--color-text)] font-medium">Voice RAG Bot</p>
                            <p className="text-[var(--color-text-muted)]">v2.0</p>
                        </div>
                    )}
                </div>
            </div>
        </aside>
    )
}
