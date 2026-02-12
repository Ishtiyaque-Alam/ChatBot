import { useNavigate } from 'react-router-dom'
import Orb from '../components/AIOrb2'

export default function Homepage() {
    const navigate = useNavigate()

    return (
        <div className="relative w-full h-screen overflow-hidden">
            {/* Orb — full-screen background */}
            <div className="absolute inset-0 z-0">
                <Orb
                    hoverIntensity={2}
                    rotateOnHover
                    hue={0}
                    forceHoverState={false}
                    backgroundColor="#000000"
                />
            </div>

            {/* Content — overlaid on top of the Orb */}
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center pointer-events-none">
                <div className="text-center px-6 max-w-3xl pointer-events-auto">
                    {/* Badge */}
                    <div className="inline-flex items-center gap-2 px-4 py-1.5 mb-10 rounded-full border border-white/10 bg-black/30 backdrop-blur-md text-sm text-[var(--color-text-muted)] animate-fade-in-up">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                        AI-Powered Voice Assistant
                    </div>

                    {/* Title */}
                    <h1 className="text-6xl md:text-8xl font-bold mb-8 leading-[1.15] animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
                        <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-cyan-400 bg-clip-text text-transparent drop-shadow-lg">
                            AI Chatbot
                        </span>
                        <br />
                        <span className="text-white drop-shadow-lg">Assistant</span>
                    </h1>

                    {/* Subtitle */}
                    <p
                        className="text-lg md:text-2xl text-white/70 mb-14 max-w-2xl mx-auto leading-relaxed animate-fade-in-up"
                        style={{ animationDelay: '0.2s', lineHeight: '1.8' }}
                    >
                        Speak in Hindi, get answers in English.
                        <br />
                        Powered by voice recognition, intelligent retrieval,
                        <br />
                        and conversational memory.
                    </p>

                    {/* CTA Button */}
                    <div className="animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
                        <button
                            onClick={() => navigate('/chat')}
                            className="group relative inline-flex items-center gap-4 px-16 py-6 rounded-2xl text-2xl font-semibold text-white
                                       bg-white/10 border border-white/20 backdrop-blur-md
                                       hover:bg-white/20 hover:shadow-2xl hover:shadow-white/10 hover:scale-[1.04] active:scale-[0.97]
                                       transition-all duration-300 cursor-pointer"
                        >
                            <span>Start Chatting</span>
                            <svg
                                className="w-6 h-6 transition-transform group-hover:translate-x-1.5"
                                fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                            </svg>
                        </button>
                    </div>

                    {/* Feature pills */}
                    <div
                        className="flex flex-wrap justify-center gap-4 mt-20 animate-fade-in-up"
                        style={{ animationDelay: '0.45s' }}
                    >
                        {['🎤 Voice Input', '🌐 Hindi → English', '🧠 Smart Memory', '📚 RAG Pipeline'].map((f) => (
                            <span
                                key={f}
                                className="px-5 py-2.5 rounded-xl text-sm border border-white/10 bg-black/30 backdrop-blur-md
                                           text-white/70 leading-relaxed"
                            >
                                {f}
                            </span>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
}
