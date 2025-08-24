import type { Route } from "./+types/home";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Lines — Minimal UI" },
    { name: "description", content: "A clean, elegant UI with black lines on white." },
  ];
}

export default function Home() {
  return (
    <main className="min-h-dvh bg-white text-black">
      {/* Header */}
      <header className="border-b border-black">
        <div className="mx-auto max-w-6xl px-6 h-16 flex items-center justify-between">
          <a href="#home" className="text-[15px] tracking-wide font-medium focus-visible:outline-2 focus-visible:outline focus-visible:outline-black">
            LINES
          </a>
          <nav className="flex items-center gap-8 text-sm">
            <a href="#work" className="hover:opacity-70 focus-visible:outline-2 focus-visible:outline focus-visible:outline-black">Work</a>
            <a href="#about" className="hover:opacity-70 focus-visible:outline-2 focus-visible:outline focus-visible:outline-black">About</a>
            <a href="#contact" className="hover:opacity-70 focus-visible:outline-2 focus-visible:outline focus-visible:outline-black">Contact</a>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section aria-labelledby="hero-title" className="border-b border-black">
        <div className="mx-auto max-w-6xl px-6 py-20 md:py-28">
          <h1 id="hero-title" className="text-4xl md:text-6xl leading-tight font-semibold tracking-tight">
            Simple black lines. Effortless elegance.
          </h1>
          <p className="mt-5 max-w-2xl text-base md:text-lg leading-relaxed text-neutral-700">
            A timeless, practical layout built on clarity and restraint. Nothing extra—just structure, rhythm, and space.
          </p>
          <div className="mt-10 flex items-center gap-6">
            <a
              href="#get-started"
              className="inline-flex items-center gap-2 px-3 py-1.5 border border-black hover:bg-black hover:text-white transition-colors focus-visible:outline-2 focus-visible:outline focus-visible:outline-black"
            >
              Get started
              <span aria-hidden>→</span>
            </a>
            <a
              href="#learn-more"
              className="inline-flex items-center gap-2 underline underline-offset-4 decoration-black hover:opacity-70 focus-visible:outline-2 focus-visible:outline focus-visible:outline-black"
            >
              Learn more
            </a>
          </div>
        </div>
      </section>

      {/* Feature Grid with lines */}
      <section aria-labelledby="features-title" className="border-b border-black">
        <h2 id="features-title" className="sr-only">Features</h2>
        <div className="mx-auto max-w-6xl grid md:grid-cols-3 border-t border-black">
          <article className="p-6 border-b md:border-b-0 md:border-r border-black">
            <h3 className="text-lg font-medium">Grids & Rhythm</h3>
            <p className="mt-2 text-neutral-700">Columns, gutters, and consistent spacing create quiet order.</p>
          </article>
          <article className="p-6 border-b md:border-b-0 md:border-r border-black">
            <h3 className="text-lg font-medium">Clear Hierarchy</h3>
            <p className="mt-2 text-neutral-700">Headlines lead; details support. Every element earns its place.</p>
          </article>
          <article className="p-6">
            <h3 className="text-lg font-medium">Accessible By Design</h3>
            <p className="mt-2 text-neutral-700">High contrast, sensible focus states, and semantic markup.</p>
          </article>
        </div>
      </section>

      {/* List section with hairline rows */}
      <section aria-labelledby="list-title">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <h2 id="list-title" className="text-sm font-medium tracking-wide">Latest</h2>
        </div>
        <ul className="mx-auto max-w-6xl border-y border-black">
          {["Structure first, styling second","Interfaces that disappear","Typography that breathes","Details that matter"].map((label, i) => (
            <li key={i} className="flex items-center justify-between px-6 h-14 border-t first:border-t-0 border-black">
              <span className="text-base">{label}</span>
              <span aria-hidden className="text-base">→</span>
            </li>
          ))}
        </ul>
      </section>

      {/* Footer */}
      <footer className="border-t border-black mt-16">
        <div className="mx-auto max-w-6xl px-6 h-16 flex items-center justify-between text-sm">
          <span>© {new Date().getFullYear()} Lines</span>
          <a href="#privacy" className="underline underline-offset-4 decoration-black hover:opacity-70 focus-visible:outline-2 focus-visible:outline focus-visible:outline-black">Privacy</a>
        </div>
      </footer>
    </main>
  );
}
