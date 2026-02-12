export default function AIOrb({ visible = true }) {
    if (!visible) return null

    return (
        <div className="flex flex-col items-center justify-center py-16 animate-fade-in-up select-none">
            {/* Outer glow container */}
            <div className="relative w-40 h-40 flex items-center justify-center animate-float">
                {/* Outermost ring */}
                <div className="absolute inset-0 rounded-full border border-indigo-500/20 animate-orb-ring" />

                {/* Middle ring (reverse) */}
                <div
                    className="absolute inset-3 rounded-full border border-violet-400/15"
                    style={{ animation: 'orb-ring 12s linear infinite reverse' }}
                />

                {/* Core orb */}
                <div className="relative w-24 h-24 rounded-full animate-orb-pulse animate-orb-glow">
                    {/* Gradient sphere */}
                    <div className="absolute inset-0 rounded-full bg-gradient-to-br from-indigo-500 via-violet-500 to-cyan-500 opacity-90" />

                    {/* Inner highlight */}
                    <div className="absolute inset-2 rounded-full bg-gradient-to-br from-white/20 to-transparent" />

                    {/* Center dot */}
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-3 h-3 rounded-full bg-white/60 blur-[2px]" />
                    </div>
                </div>

                {/* Particle dots */}
                {[0, 60, 120, 180, 240, 300].map((deg) => (
                    <div
                        key={deg}
                        className="absolute w-1.5 h-1.5 rounded-full bg-indigo-400/50"
                        style={{
                            top: `${50 + 45 * Math.sin((deg * Math.PI) / 180)}%`,
                            left: `${50 + 45 * Math.cos((deg * Math.PI) / 180)}%`,
                            animation: `orb-pulse ${2 + (deg % 3)}s ease-in-out infinite`,
                            animationDelay: `${deg * 10}ms`,
                        }}
                    />
                ))}
            </div>

            {/* Label */}
            <p className="mt-6 text-sm text-[var(--color-text-muted)] tracking-wide">
                Ask me anything — type or speak
            </p>
        </div>
    )
}
