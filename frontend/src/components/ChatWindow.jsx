import { useEffect, useRef } from 'react'
import AIOrb from './AIOrb'
import { SpinnerIcon } from './Icons'

export default function ChatWindow({ messages, isLoading, isIdle }) {
    const bottomRef = useRef(null)

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, isLoading])

    return (
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 flex flex-col">
            <div className="max-w-3xl w-full mx-auto space-y-4 flex-1 flex flex-col justify-center">
                {/* AI Orb — shown only when idle with no messages or after response */}
                {isIdle && messages.length === 0 && <AIOrb visible={true} />}

                {/* Messages */}
                {messages.map((msg, i) => (
                    <div
                        key={i}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in-up`}
                        style={{ animationDelay: `${Math.min(i * 50, 200)}ms` }}
                    >
                        <div
                            className={`max-w-[80%] md:max-w-[70%] px-5 py-3.5 rounded-2xl text-sm leading-relaxed
                ${msg.role === 'user'
                                    ? 'bg-[var(--color-user-bubble)] text-white rounded-br-md'
                                    : 'bg-[var(--color-ai-bubble)] text-[var(--color-text)] border border-[var(--color-border)] rounded-bl-md'
                                }`}
                        >
                            {/* Role label */}
                            <p className={`text-[10px] font-semibold tracking-wider uppercase mb-1.5
                ${msg.role === 'user' ? 'text-indigo-200' : 'text-[var(--color-text-muted)]'}`}>
                                {msg.role === 'user' ? 'You' : 'AI Assistant'}
                            </p>

                            {/* Message content */}
                            <p className="whitespace-pre-wrap">{msg.content}</p>

                            {/* Metadata badges */}
                            {msg.meta && (
                                <div className="flex flex-wrap gap-2 mt-2 pt-2 border-t border-white/10">
                                    {msg.meta.source && (
                                        <span className={`text-[10px] px-2 py-0.5 rounded-full
                      ${msg.meta.source === 'history'
                                                ? 'bg-emerald-500/20 text-emerald-300'
                                                : 'bg-cyan-500/20 text-cyan-300'}`}>
                                            {msg.meta.source === 'history' ? '💬 From Memory' : '📚 VectorDB'}
                                        </span>
                                    )}
                                    {msg.meta.transcription && (
                                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300">
                                            🎤 {msg.meta.transcription}
                                        </span>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {/* Loading indicator */}
                {isLoading && (
                    <div className="flex justify-start animate-fade-in-up">
                        <div className="px-5 py-4 rounded-2xl rounded-bl-md bg-[var(--color-ai-bubble)] border border-[var(--color-border)]">
                            <div className="flex items-center gap-3">
                                <SpinnerIcon className="w-4 h-4 text-indigo-400" />
                                <div className="flex gap-1">
                                    {[0, 1, 2].map((i) => (
                                        <div
                                            key={i}
                                            className="w-2 h-2 rounded-full bg-indigo-400/60 animate-pulse"
                                            style={{ animationDelay: `${i * 200}ms` }}
                                        />
                                    ))}
                                </div>
                                <span className="text-xs text-[var(--color-text-muted)]">Thinking...</span>
                            </div>
                        </div>
                    </div>
                )}

                <div ref={bottomRef} />
            </div>
        </div>
    )
}
