import { useState, useRef, useCallback } from 'react'
import { SendIcon, MicIcon, StopIcon, UploadIcon } from './Icons'

export default function InputBar({ onSendText, onSendAudio, disabled }) {
    const [text, setText] = useState('')
    const [isRecording, setIsRecording] = useState(false)
    const [recordingTime, setRecordingTime] = useState(0)
    const mediaRecorderRef = useRef(null)
    const chunksRef = useRef([])
    const timerRef = useRef(null)
    const fileInputRef = useRef(null)
    const textareaRef = useRef(null)

    // ── Auto-resize textarea ─────────────────────────────────
    const handleTextChange = useCallback((e) => {
        setText(e.target.value)
        const ta = textareaRef.current
        if (ta) {
            ta.style.height = 'auto'
            ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`
        }
    }, [])

    // ── Text Submit ──────────────────────────────────────────
    const handleSubmit = useCallback(
        (e) => {
            e?.preventDefault()
            const msg = text.trim()
            if (!msg || disabled) return
            onSendText(msg)
            setText('')
            if (textareaRef.current) {
                textareaRef.current.style.height = 'auto'
            }
        },
        [text, disabled, onSendText],
    )

    // ── Audio Recording ──────────────────────────────────────
    const startRecording = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
            const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
            mediaRecorderRef.current = mediaRecorder
            chunksRef.current = []

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) chunksRef.current.push(e.data)
            }

            mediaRecorder.onstop = () => {
                const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
                stream.getTracks().forEach((t) => t.stop())
                clearInterval(timerRef.current)
                setRecordingTime(0)
                onSendAudio(blob)
            }

            mediaRecorder.start()
            setIsRecording(true)
            setRecordingTime(0)
            timerRef.current = setInterval(() => setRecordingTime((t) => t + 1), 1000)
        } catch (err) {
            console.error('Microphone access denied:', err)
            alert('Please allow microphone access to record audio.')
        }
    }, [onSendAudio])

    const stopRecording = useCallback(() => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop()
            setIsRecording(false)
        }
    }, [isRecording])

    // ── File Upload ──────────────────────────────────────────
    const handleFileUpload = useCallback(
        (e) => {
            const file = e.target.files?.[0]
            if (!file) return
            onSendAudio(file)
            if (fileInputRef.current) fileInputRef.current.value = ''
        },
        [onSendAudio],
    )

    const formatTime = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

    return (
        <div className="border-t border-[var(--color-border)] bg-[var(--color-surface)]/90 backdrop-blur-xl px-4 md:px-8 py-5">
            <div className="max-w-3xl mx-auto">
                {/* Recording indicator */}
                {isRecording && (
                    <div className="flex items-center gap-3 mb-4 px-5 py-3 rounded-2xl bg-red-500/10 border border-red-500/20 animate-fade-in-up">
                        <div className="w-3 h-3 rounded-full bg-red-500 animate-recording" />
                        <span className="text-sm text-red-400 font-medium">Recording</span>
                        <span className="text-sm text-red-300 font-mono">{formatTime(recordingTime)}</span>
                        <div className="flex-1" />
                        <span className="text-xs text-red-400/60">Click stop when done</span>
                    </div>
                )}

                {/* Main input container */}
                <div className="flex items-end gap-3 p-2 rounded-2xl bg-[var(--color-surface-light)] border border-[var(--color-border)] focus-within:border-indigo-500/40 focus-within:ring-1 focus-within:ring-indigo-500/15 transition-all duration-200">
                    {/* Textarea */}
                    <textarea
                        ref={textareaRef}
                        value={text}
                        onChange={handleTextChange}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault()
                                handleSubmit()
                            }
                        }}
                        placeholder={isRecording ? '🎤 Recording audio...' : 'Type your message... (Shift+Enter for new line)'}
                        disabled={disabled || isRecording}
                        rows={1}
                        className={`flex-1 px-4 py-3 rounded-xl resize-none
                       bg-transparent text-[var(--color-text)]
                       focus:outline-none
                       placeholder:text-[var(--color-text-muted)]/60 placeholder:text-center text-[15px] leading-relaxed
                       disabled:opacity-40 transition-all duration-200
                       ${text ? 'text-left' : 'text-center'}`}
                        style={{ maxHeight: '160px' }}
                    />

                    {/* Action buttons row */}
                    <div className="flex items-center gap-1.5 pb-1 pr-1">
                        {/* Upload .wav */}
                        <button
                            type="button"
                            onClick={() => fileInputRef.current?.click()}
                            disabled={disabled || isRecording}
                            className="flex items-center justify-center w-10 h-10 rounded-xl
                         text-[var(--color-text-muted)] hover:text-[var(--color-text)]
                         hover:bg-[var(--color-surface-lighter)]
                         disabled:opacity-30 transition-all duration-200 cursor-pointer"
                            title="Upload .wav file"
                        >
                            <UploadIcon className="w-[18px] h-[18px]" />
                        </button>
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept=".wav,audio/wav"
                            onChange={handleFileUpload}
                            className="hidden"
                        />

                        {/* Mic */}
                        <button
                            type="button"
                            onClick={isRecording ? stopRecording : startRecording}
                            disabled={disabled}
                            className={`flex items-center justify-center w-10 h-10 rounded-xl
                         transition-all duration-200 cursor-pointer
                         ${isRecording
                                    ? 'bg-red-500 text-white shadow-lg shadow-red-500/30 animate-recording'
                                    : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-lighter)]'
                                }
                         disabled:opacity-30`}
                            title={isRecording ? 'Stop recording' : 'Start recording'}
                        >
                            {isRecording ? <StopIcon className="w-[18px] h-[18px]" /> : <MicIcon className="w-[18px] h-[18px]" />}
                        </button>

                        {/* Send */}
                        <button
                            type="button"
                            onClick={handleSubmit}
                            disabled={disabled || !text.trim() || isRecording}
                            className="flex items-center justify-center w-10 h-10 rounded-xl
                         bg-gradient-to-r from-indigo-500 to-violet-500 text-white
                         hover:shadow-lg hover:shadow-indigo-500/25 hover:scale-105 active:scale-95
                         disabled:opacity-30 disabled:hover:scale-100 disabled:hover:shadow-none
                         transition-all duration-200 cursor-pointer"
                            title="Send message"
                        >
                            <SendIcon className="w-[18px] h-[18px]" />
                        </button>
                    </div>
                </div>

                <p className="text-[11px] text-[var(--color-text-muted)]/50 text-center mt-3">
                    Speak in Hindi · Type in English · Press Enter to send
                </p>
            </div>
        </div>
    )
}
