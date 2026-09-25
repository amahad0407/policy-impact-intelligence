import Link from 'next/link';
import { Shield, ArrowRight, ChevronRight } from 'lucide-react';

function RetroGrid() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-x-0 bottom-0 z-0 h-[65%] overflow-hidden"
    >
      {/* Animated perspective grid */}
      <div
        className="animate-retro-grid absolute inset-0"
        style={{
          backgroundImage: [
            'linear-gradient(rgba(139,92,246,0.18) 1px, transparent 1px)',
            'linear-gradient(90deg, rgba(139,92,246,0.18) 1px, transparent 1px)',
          ].join(', '),
          backgroundSize: '60px 60px',
          transform: 'perspective(600px) rotateX(58deg)',
          transformOrigin: 'top center',
        }}
      />
      {/* Fade: conceal horizon, reveal near ground */}
      <div
        className="absolute inset-0"
        style={{
          maskImage: 'linear-gradient(to bottom, transparent 0%, black 55%)',
          WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, black 55%)',
        }}
      />
      {/* Fade into page bg at very bottom */}
      <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-background to-transparent" />
      {/* Side fades */}
      <div className="absolute inset-y-0 left-0 w-24 bg-gradient-to-r from-background to-transparent" />
      <div className="absolute inset-y-0 right-0 w-24 bg-gradient-to-l from-background to-transparent" />
    </div>
  );
}

export function HeroSectionDark() {
  return (
    <section className="relative flex min-h-[88vh] flex-col items-center justify-center overflow-hidden px-4 py-24 sm:px-6">
      {/* Radial glow behind content */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 z-0"
        style={{
          background:
            'radial-gradient(ellipse 80% 50% at 50% 30%, rgba(124,58,237,0.12) 0%, transparent 70%)',
        }}
      />

      <RetroGrid />

      {/* Content */}
      <div className="relative z-10 mx-auto max-w-4xl text-center">
        {/* Badge */}
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-4 py-1.5 text-xs font-medium text-violet-300">
          <Shield className="h-3.5 w-3.5" />
          Policy Impact Intelligence
        </div>

        {/* Heading */}
        <h1 className="mb-6 text-5xl font-bold tracking-tight text-white sm:text-6xl lg:text-7xl">
          Understand{' '}
          <span className="bg-gradient-to-r from-violet-400 via-purple-400 to-indigo-400 bg-clip-text text-transparent">
            policy impact
          </span>{' '}
          before it becomes reality.
        </h1>

        {/* Description */}
        <p className="mx-auto mb-10 max-w-2xl text-lg leading-relaxed text-zinc-400 sm:text-xl">
          Analyze policy language, public feedback, news coverage, and stakeholder
          impacts in one place. Evidence-grounded. Source-attributed. Built for analysts.
        </p>

        {/* CTA buttons */}
        <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <Link
            href="/analyze"
            className="group inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-violet-500/25 transition-all hover:from-violet-500 hover:to-indigo-500 hover:shadow-violet-500/40"
          >
            Analyze a Policy
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
          <Link
            href="/overview"
            className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-6 py-3 text-sm font-medium text-zinc-300 transition-colors hover:border-white/20 hover:text-white"
          >
            Explore Current Policy
            <ChevronRight className="h-4 w-4" />
          </Link>
        </div>

        {/* Trust line */}
        <p className="mt-8 text-xs text-zinc-600">
          AI-generated analysis · Human review required · Not for use in official guidance without verification
        </p>
      </div>
    </section>
  );
}
