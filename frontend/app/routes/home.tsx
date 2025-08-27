import type { Route } from "./+types/home";
import { useEffect, useMemo, useRef, useState } from "react";

type XmlAttr = { id: string; name: string; value: string };
type Block = {
  id: string;
  tag: string;
  content: string;
  attrs: XmlAttr[];
  collapsed?: boolean;
};

type Template = { id: string; name: string; blocks: Block[]; createdAt: number; updatedAt: number };
type HistoryEntry = { id: string; title: string; blocks: Block[]; createdAt: number };

const PALETTE = [
  { label: "system", tag: "system" },
  { label: "context", tag: "context" },
  { label: "instruction", tag: "instruction" },
  { label: "note", tag: "note" },
  { label: "input", tag: "input" },
  { label: "output", tag: "output_format" },
  { label: "style", tag: "style" },
  { label: "example", tag: "example" },
  { label: "language", tag: "language" },
  { label: "custom", tag: "custom" },
];

const STORAGE_KEY = "xml-block-builder:v2";
const TEMPLATES_KEY = "xml-block-builder:templates.v1";
const HISTORY_KEY = "xml-block-builder:history.v1";
const MAX_HISTORY = 100;

function uid(prefix = "id") {
  return `${prefix}_${Math.random().toString(36).slice(2, 8)}${Date.now().toString(36).slice(-4)}`;
}

function escapeXml(text: string) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function escapeXmlContent(text: string) {
  // Only escape & to prevent XML entity conflicts
  // Don't escape < and > to allow XML/HTML examples in content
  return text.replaceAll("&", "&amp;");
}

function buildXml(blocks: Block[], opts: { indent?: number }) {
  const indentSize = Math.max(0, Math.min(8, opts.indent ?? 2));
  const lines: string[] = [];
  const indent = (level: number) => " ".repeat(level * indentSize);
  const renderAttrs = (attrs: XmlAttr[]) =>
    attrs
      .filter((a) => a.name.trim())
      .map((a) => `${a.name}="${escapeXml(a.value)}"`)
      .join(" ");

  const renderBlock = (b: Block, level: number) => {
    const attrsStr = renderAttrs(b.attrs);
    const hasContent = b.content.trim().length > 0;
    const open = attrsStr ? `<${b.tag} ${attrsStr}>` : `<${b.tag}>`;
    lines.push(indent(level) + open);
    if (hasContent) {
      // multiline preserved
      b.content.split("\n").forEach((ln) => {
        lines.push(indent(level + 1) + escapeXmlContent(ln));
      });
    }
    lines.push(indent(level) + `</${b.tag}>`);
  };

  blocks.forEach((b) => renderBlock(b, 0));
  return lines.join("\n");
}


export function meta({}: Route.MetaArgs) {
  return [
    { title: "Prompt Blocks — Organize your intelligence" },
    { name: "description", content: "Assemble XML prompt blocks interactively and export instantly." },
  ];
}

function ToolbarButton(props: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const { className = "", ...rest } = props;
  return (
    <button
      {...rest}
      className={`px-2 h-8 border border-black hover:bg-black hover:text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-black ${className}`}
    />
  );
}



export default function Home() {
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [indent, setIndent] = useState<number>(2);
  const [justAddedId, setJustAddedId] = useState<string | null>(null);
  const [bumped, setBumped] = useState<{ id: string; dir: -1 | 1 } | null>(null);
  const [removing, setRemoving] = useState<Set<string>>(new Set());
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState<{ id: string; pos: "before" | "after" } | null>(null);
  const [pointerDrag, setPointerDrag] = useState(false);
  const pointerIdRef = useRef<number | null>(null);
  const itemRefs = useRef(new Map<string, HTMLLIElement | null>());
  const [templates, setTemplates] = useState<Template[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [templateName, setTemplateName] = useState<string>("");
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [historyTitle, setHistoryTitle] = useState<string>("");
  const importHistoryRef = useRef<HTMLInputElement>(null);
  const lastSnapshotRef = useRef<{ xml: string; at: number } | null>(null);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && Array.isArray(parsed.blocks)) {
          setBlocks(parsed.blocks);
          setIndent(parsed.indent ?? 2);
        }
      } else {
        // Seed with a helpful template (no root/declaration by default)
        setBlocks([
          { id: uid("blk"), tag: "system", content: "You are a helpful assistant.", attrs: [] },
          { id: uid("blk"), tag: "instruction", content: "Follow the steps carefully.", attrs: [] },
          { id: uid("blk"), tag: "input", content: "{user_input}", attrs: [{ id: uid("attr"), name: "format", value: "text" }] },
          { id: uid("blk"), tag: "output_format", content: "JSON with fields: { \"answer\": \"string\", \"reasoning\": \"string\" }", attrs: [] },
        ]);
      }

      // Load templates and history
      const rawT = localStorage.getItem(TEMPLATES_KEY);
      if (rawT) {
        const parsedT = JSON.parse(rawT);
        if (Array.isArray(parsedT)) setTemplates(parsedT);
      }
      const rawH = localStorage.getItem(HISTORY_KEY);
      if (rawH) {
        const parsedH = JSON.parse(rawH);
        if (Array.isArray(parsedH)) setHistory(parsedH);
      }
    } catch {}
  }, []);

  // Persist to localStorage (debounced)
  useEffect(() => {
    const t = setTimeout(() => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ blocks, indent }));
      } catch {}
    }, 200);
    return () => clearTimeout(t);
  }, [blocks, indent]);

  const xml = useMemo(() => buildXml(blocks, { indent }), [blocks, indent]);

  function saveCurrentAsTemplate(name?: string) {
    const nm = (name || templateName || "Untitled").trim();
    const now = Date.now();
    const tpl: Template = {
      id: uid("tpl"),
      name: nm,
      blocks: blocks.map((b) => ({ ...b, id: uid("blk"), attrs: b.attrs.map((a) => ({ ...a, id: uid("attr") })) })),
      createdAt: now,
      updatedAt: now,
    };
    setTemplates((prev) => {
      const next = [tpl, ...prev];
      try {
        localStorage.setItem(TEMPLATES_KEY, JSON.stringify(next));
      } catch {}
      return next;
    });
    setTemplateName("");
  }

  function handleTemplateSelect(val: string) {
    if (!val) return;
    if (val.startsWith("builtin:")) {
      loadTemplate(val.slice(8));
    } else if (val.startsWith("custom:")) {
      const id = val.slice(7);
      const tpl = templates.find((t) => t.id === id);
      if (tpl) {
        setBlocks(tpl.blocks.map((b) => ({ ...b, id: uid("blk"), attrs: b.attrs.map((a) => ({ ...a, id: uid("attr") })) })));
      }
    }
  }

  function snapshotNow(title?: string) {
    const currentXml = xml;
    const last = lastSnapshotRef.current;
    if (last && last.xml === currentXml) return; // avoid duplicates
    const entry: HistoryEntry = {
      id: uid("his"),
      title: title?.trim() || `Auto — ${new Date().toLocaleString()}`,
      blocks: blocks.map((b) => ({ ...b, id: uid("blk"), attrs: b.attrs.map((a) => ({ ...a, id: uid("attr") })) })),
      createdAt: Date.now(),
    };
    setHistory((prev) => {
      const next = [entry, ...prev].slice(0, MAX_HISTORY);
      try { localStorage.setItem(HISTORY_KEY, JSON.stringify(next)); } catch {}
      return next;
    });
    lastSnapshotRef.current = { xml: currentXml, at: Date.now() };
  }

  // Auto-snapshot after inactivity
  useEffect(() => {
    const t = setTimeout(() => snapshotNow(), 15000);
    return () => clearTimeout(t);
  }, [xml]);

  function addBlock(tag: string) {
    const id = uid("blk");
    let content = "";
    let attrs: XmlAttr[] = [];
    
    // Add default content for specific blocks
    if (tag === "system") {
      content = "Act as ";
      attrs = [];
    } else if (tag === "output_format") {
      content = "Specify the desired output format and structure";
      attrs = [];
    } else if (tag === "style") {
      content = "Professional and clear";
      attrs = [];
    } else if (tag === "language") {
      content = "Answer in Korean";
      attrs = [];
    }
    
    setBlocks((prev) => [
      ...prev,
      { id, tag, content, attrs },
    ]);
    setJustAddedId(id);
    setTimeout(() => setJustAddedId((v) => (v === id ? null : v)), 280);
  }

  function duplicateBlock(id: string) {
    setBlocks((prev) => {
      const idx = prev.findIndex((b) => b.id === id);
      if (idx === -1) return prev;
      const b = prev[idx];
      const clone: Block = {
        ...b,
        id: uid("blk"),
        attrs: b.attrs.map((a) => ({ ...a, id: uid("attr") })),
      };
      const next = prev.slice();
      next.splice(idx + 1, 0, clone);
      setJustAddedId(clone.id);
      setTimeout(() => setJustAddedId((v) => (v === clone.id ? null : v)), 280);
      return next;
    });
  }

  function removeBlock(id: string) {
    setRemoving((prev) => new Set(prev).add(id));
    setTimeout(() => {
      setBlocks((prev) => prev.filter((b) => b.id !== id));
      setRemoving((prev) => {
        const n = new Set(prev);
        n.delete(id);
        return n;
      });
    }, 160);
  }

  function moveBlock(id: string, dir: -1 | 1) {
    setBlocks((prev) => {
      const idx = prev.findIndex((b) => b.id === id);
      if (idx === -1) return prev;
      const to = idx + dir;
      if (to < 0 || to >= prev.length) return prev;
      const next = prev.slice();
      const [item] = next.splice(idx, 1);
      next.splice(to, 0, item);
      setBumped({ id, dir });
      setTimeout(() => setBumped((v) => (v?.id === id ? null : v)), 220);
      return next;
    });
  }

  // Drag & Drop
  function handleDragStart(e: React.DragEvent, id: string) {
    e.dataTransfer.setData("text/plain", id);
    e.dataTransfer.effectAllowed = "move";
    setDraggingId(id);
  }

  function handleDragOver(e: React.DragEvent, overId: string) {
    if (!draggingId || draggingId === overId) return;
    e.preventDefault();
    const el = e.currentTarget as HTMLElement;
    const rect = el.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const pos: "before" | "after" = y < rect.height / 2 ? "before" : "after";
    setDragOver((prev) => (prev?.id === overId && prev.pos === pos ? prev : { id: overId, pos }));
    e.dataTransfer.dropEffect = "move";
  }

  function handleDrop(e: React.DragEvent, overId: string) {
    e.preventDefault();
    const fromId = e.dataTransfer.getData("text/plain") || draggingId;
    if (!fromId || fromId === overId) {
      setDraggingId(null);
      setDragOver(null);
      return;
    }
    const pos = dragOver?.id === overId ? dragOver.pos : "after";
    setBlocks((prev) => {
      const fromIndex = prev.findIndex((b) => b.id === fromId);
      const overIndex = prev.findIndex((b) => b.id === overId);
      if (fromIndex === -1 || overIndex === -1) return prev;
      const beforeIndex = pos === "before" ? overIndex : overIndex + 1;
      const next = prev.slice();
      const [item] = next.splice(fromIndex, 1);
      const insertAt = fromIndex < beforeIndex ? beforeIndex - 1 : beforeIndex;
      next.splice(insertAt, 0, item);
      return next;
    });
    setBumped({ id: overId, dir: dragOver?.pos === "before" ? -1 : 1 });
    setTimeout(() => setBumped((v) => (v?.id === overId ? null : v)), 220);
    setDraggingId(null);
    setDragOver(null);
  }

  function handleDragEnd() {
    setDraggingId(null);
    setDragOver(null);
  }

  // Pointer-based drag for touch (and pen). Starts from drag handle only.
  function computeDropTarget(clientY: number, excludeId: string | null): { id: string; pos: "before" | "after" } | null {
    const entries: Array<{ id: string; top: number; height: number }> = [];
    itemRefs.current.forEach((el, id) => {
      if (!el || id === excludeId) return;
      const r = el.getBoundingClientRect();
      entries.push({ id, top: r.top, height: r.height });
    });
    if (entries.length === 0) return null;
    entries.sort((a, b) => a.top - b.top);
    for (const e of entries) {
      const mid = e.top + e.height / 2;
      if (clientY < mid) return { id: e.id, pos: "before" };
    }
    return { id: entries[entries.length - 1].id, pos: "after" };
  }

  function onHandlePointerDown(e: React.PointerEvent, id: string) {
    if (e.pointerType !== "touch" && e.pointerType !== "pen") return; // keep HTML5 DnD for mouse
    try { (e.currentTarget as Element).setPointerCapture(e.pointerId); } catch {}
    e.preventDefault();
    pointerIdRef.current = e.pointerId;
    setDraggingId(id);
    setPointerDrag(true);
    setDragOver(null);

    const onMove = (ev: PointerEvent) => {
      if (pointerIdRef.current !== ev.pointerId) return;
      ev.preventDefault();
      const tgt = computeDropTarget(ev.clientY, id);
      setDragOver((prev) => (tgt && (prev?.id !== tgt.id || prev.pos !== tgt.pos) ? tgt : tgt || null));
    };

    const onUp = (ev: PointerEvent) => {
      if (pointerIdRef.current !== ev.pointerId) return;
      ev.preventDefault();
      const tgt = dragOver;
      if (tgt && draggingId) {
        // reorder similar to drop
        setBlocks((prev) => {
          const fromIndex = prev.findIndex((b) => b.id === draggingId);
          const overIndex = prev.findIndex((b) => b.id === tgt.id);
          if (fromIndex === -1 || overIndex === -1) return prev;
          const beforeIndex = tgt.pos === "before" ? overIndex : overIndex + 1;
          const next = prev.slice();
          const [item] = next.splice(fromIndex, 1);
          const insertAt = fromIndex < beforeIndex ? beforeIndex - 1 : beforeIndex;
          next.splice(insertAt, 0, item);
          return next;
        });
        setBumped({ id: tgt.id, dir: tgt.pos === "before" ? -1 : 1 });
        setTimeout(() => setBumped((v) => (v?.id === tgt.id ? null : v)), 220);
      }
      cleanup();
    };

    const cleanup = () => {
      try { (e.currentTarget as Element).releasePointerCapture(e.pointerId); } catch {}
      pointerIdRef.current = null;
      setDraggingId(null);
      setDragOver(null);
      setPointerDrag(false);
      window.removeEventListener("pointermove", onMove, { capture: true } as any);
      window.removeEventListener("pointerup", onUp, { capture: true } as any);
      window.removeEventListener("pointercancel", onUp, { capture: true } as any);
    };

    window.addEventListener("pointermove", onMove, { capture: true } as any);
    window.addEventListener("pointerup", onUp, { capture: true } as any);
    window.addEventListener("pointercancel", onUp, { capture: true } as any);
  }

  function updateBlock(id: string, patch: Partial<Block>) {
    setBlocks((prev) => prev.map((b) => (b.id === id ? { ...b, ...patch } : b)));
  }

  function addAttr(blockId: string) {
    setBlocks((prev) =>
      prev.map((b) =>
        b.id === blockId ? { ...b, attrs: [...b.attrs, { id: uid("attr"), name: "", value: "" }] } : b
      )
    );
  }

  function updateAttr(blockId: string, attrId: string, patch: Partial<XmlAttr>) {
    setBlocks((prev) =>
      prev.map((b) =>
        b.id === blockId
          ? { ...b, attrs: b.attrs.map((a) => (a.id === attrId ? { ...a, ...patch } : a)) }
          : b
      )
    );
  }

  function removeAttr(blockId: string, attrId: string) {
    setBlocks((prev) =>
      prev.map((b) => (b.id === blockId ? { ...b, attrs: b.attrs.filter((a) => a.id !== attrId) } : b))
    );
  }

  function handleCopy() {
    navigator.clipboard.writeText(xml).then(() => snapshotNow("Copied")).catch(() => snapshotNow("Copied"));
  }

  function handleDownload() {
    const blob = new Blob([xml], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Prompt.txt`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    snapshotNow("Downloaded");
  }

  // TXT Import removed from header as requested

  function handleNew() {
    setBlocks([]);
    setIndent(2);
  }

  function loadTemplate(kind: string) {
    if (kind === "blank") {
      setBlocks([]);
    } else if (kind === "qa") {
      setBlocks([
        { id: uid("blk"), tag: "system", content: "You answer questions concisely.", attrs: [] },
        { id: uid("blk"), tag: "context", content: "Use only the provided context.", attrs: [] },
        { id: uid("blk"), tag: "input", content: "{question}", attrs: [{ id: uid("attr"), name: "role", value: "user" }] },
        { id: uid("blk"), tag: "output_format", content: "Plain text response", attrs: [] },
      ]);
    } else if (kind === "cot") {
      setBlocks([
        { id: uid("blk"), tag: "system", content: "Reason step-by-step before final answer.", attrs: [] },
        { id: uid("blk"), tag: "instruction", content: "Think briefly, then answer.", attrs: [] },
        { id: uid("blk"), tag: "input", content: "{problem}", attrs: [] },
        { id: uid("blk"), tag: "output_format", content: "JSON with fields: { \"reasoning\": \"string\", \"answer\": \"string\" }", attrs: [] },
      ]);
    } else {
      setBlocks([
        { id: uid("blk"), tag: "system", content: "You are a helpful assistant.", attrs: [] },
        { id: uid("blk"), tag: "instruction", content: "Follow the steps carefully.", attrs: [] },
      ]);
    }
    // no root management
  }

  return (
    <main className="min-h-dvh bg-white text-black">
      {/* Header */}
      <header className="border-b border-black">
        <div className="mx-auto max-w-7xl px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <a href="#" className="text-[15px] tracking-wide font-medium focus-visible:outline-2 focus-visible:outline focus-visible:outline-black">
              PROMPT BLOCKS
            </a>
            <div className="hidden md:flex items-center gap-2 text-sm">
              <ToolbarButton onClick={handleNew} aria-label="New">New</ToolbarButton>
              <ToolbarButton onClick={handleCopy} aria-label="Copy XML">Copy</ToolbarButton>
              <ToolbarButton onClick={handleDownload} aria-label="Download TXT">Download</ToolbarButton>
              {/* Import removed from header as requested */}
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <ToolbarButton onClick={() => setIsHistoryOpen(true)} aria-label="Open History">History</ToolbarButton>
            <a
              href="https://www.buymeacoffee.com/jinwoolee"
              target="_blank"
              rel="noopener noreferrer"
              className="h-8 flex items-center gap-2 px-2 bg-yellow-300 hover:bg-yellow-400 border border-black transition-colors text-black font-medium"
              style={{ fontFamily: 'Cookie, cursive' }}
            >
              <span>☕</span>
              <span>Buy me a coffee</span>
            </a>
          </div>
        </div>
      </header>

      {/* Main layout: left editor, right preview */}
      <section className="mx-auto max-w-7xl px-6 py-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Editor */}
        <div aria-labelledby="editor-title" className="border border-black">
          <h2 id="editor-title" className="px-3 h-12 border-b border-black flex items-center text-sm tracking-wide">
            Blocks
          </h2>

          {/* Palette */}
          <div className="p-3 border-b border-black flex flex-wrap gap-2">
            {PALETTE.map((p) => (
              <button
                key={p.tag}
                className="h-8 px-2 border border-black hover:bg-black hover:text-white text-xs sm:text-sm min-w-0 shrink-0"
                onClick={() => addBlock(p.tag)}
              >
                + {p.label}
              </button>
            ))}
          </div>

          {/* Blocks list */}
          <ul className="divide-y divide-black">
            {blocks.length === 0 && (
              <li className="p-6 text-sm text-neutral-700">No blocks yet. Add from the palette above.</li>
            )}
            {blocks.map((b, i) => {
              const isRemoving = removing.has(b.id);
              const isAdded = justAddedId === b.id;
              const isBumped = bumped?.id === b.id ? (bumped.dir === -1 ? "bump-up" : "bump-down") : "";
              const dropIndicator = dragOver?.id === b.id ? (dragOver.pos === "before" ? "drag-over-before" : "drag-over-after") : "";
              const dragging = draggingId === b.id ? (pointerDrag ? "dragging-strong" : "dragging") : "";
              const animClass = isRemoving ? "anim-pop-out" : isAdded ? "anim-pop-in flash-bg" : isBumped;
              return (
              <li
                key={b.id}
                className={`p-3 ${animClass} ${dropIndicator} ${dragging}`}
                draggable
                onDragStart={(e) => handleDragStart(e, b.id)}
                onDragOver={(e) => handleDragOver(e, b.id)}
                onDrop={(e) => handleDrop(e, b.id)}
                onDragEnd={handleDragEnd}
                ref={(el) => {
                  itemRefs.current.set(b.id, el);
                  if (el === null) itemRefs.current.delete(b.id);
                }}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className="drag-handle h-8 w-8 border border-black flex items-center justify-center"
                      title="Drag"
                      aria-label="Drag"
                      onPointerDown={(e) => onHandlePointerDown(e, b.id)}
                    >
                      ≡
                    </button>
                    <input
                      type="text"
                      className="h-8 w-28 sm:w-36 px-2 border border-black text-xs sm:text-sm"
                      value={b.tag}
                      onChange={(e) => updateBlock(b.id, { tag: e.target.value.replace(/\s+/g, "") })}
                      placeholder="tag"
                    />
                  </div>
                  <div className="flex items-center gap-1">
                    <button className="h-8 w-8 border border-black" title="Move up" onClick={() => moveBlock(b.id, -1)} disabled={i === 0}>
                      ↑
                    </button>
                    <button className="h-8 w-8 border border-black" title="Move down" onClick={() => moveBlock(b.id, 1)} disabled={i === blocks.length - 1}>
                      ↓
                    </button>
                    <button className="h-8 w-8 border border-black" title="Duplicate" onClick={() => duplicateBlock(b.id)}>
                      ⎘
                    </button>
                    <button className="h-8 w-8 border border-black" title="Remove" onClick={() => removeBlock(b.id)}>
                      ✕
                    </button>
                  </div>
                </div>

                {/* Attributes */}
                <div className="mt-3 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Attributes</span>
                    <button className="h-8 px-2 border border-black text-sm" onClick={() => addAttr(b.id)}>
                      + add attribute
                    </button>
                  </div>
                  {b.attrs.length === 0 && (
                    <div className="text-sm text-neutral-600">No attributes</div>
                  )}
                  {b.attrs.map((a) => (
                    <div key={a.id} className="flex items-center gap-2">
                      <input
                        type="text"
                        className="h-8 w-32 sm:w-40 px-2 border border-black text-xs sm:text-sm"
                        placeholder="name"
                        value={a.name}
                        onChange={(e) => updateAttr(b.id, a.id, { name: e.target.value.replace(/\s+/g, "") })}
                      />
                      <input
                        type="text"
                        className="h-8 flex-1 px-2 border border-black"
                        placeholder="value"
                        value={a.value}
                        onChange={(e) => updateAttr(b.id, a.id, { value: e.target.value })}
                      />
                      <button className="h-8 w-8 border border-black" title="Remove attribute" onClick={() => removeAttr(b.id, a.id)}>
                        −
                      </button>
                    </div>
                  ))}
                </div>

                {/* Content */}
                <div className="mt-3">
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Content</span>
                    </div>
                    <textarea
                      className="min-h-24 p-2 border border-black focus-visible:outline focus-visible:outline-2 focus-visible:outline-black"
                      placeholder="Type your prompt"
                      value={b.content}
                      onChange={(e) => updateBlock(b.id, { content: e.target.value })}
                    />
                    {/* Format quick selectors for output_format blocks */}
                    {b.tag === "output_format" && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        <button
                          className="px-2 py-1 text-xs border border-black hover:bg-black hover:text-white"
                          onClick={() => {
                            const content = `{
  "answer": "Your response here",
  "reasoning": "Explanation if needed"
}`;
                            const attrs = b.attrs.filter(a => a.name !== "format").concat([{ id: uid("attr"), name: "format", value: "json" }]);
                            updateBlock(b.id, { content, attrs });
                          }}
                          title="Simple JSON object"
                        >
                          JSON
                        </button>
                        <button
                          className="px-2 py-1 text-xs border border-black hover:bg-black hover:text-white"
                          onClick={() => {
                            const content = `{
  "result": {
    "summary": "Brief overview",
    "details": {
      "key1": "value1",
      "key2": "value2"
    },
    "metadata": {
      "confidence": 0.95,
      "timestamp": "ISO-8601"
    }
  }
}`;
                            const attrs = b.attrs.filter(a => a.name !== "format").concat([{ id: uid("attr"), name: "format", value: "json" }]);
                            updateBlock(b.id, { content, attrs });
                          }}
                          title="Nested JSON object"
                        >
                          JSON Nested
                        </button>
                        <button
                          className="px-2 py-1 text-xs border border-black hover:bg-black hover:text-white"
                          onClick={() => {
                            const content = `[
  {
    "id": 1,
    "name": "Item 1",
    "description": "Details here"
  },
  {
    "id": 2,
    "name": "Item 2",
    "description": "Details here"
  }
]`;
                            const attrs = b.attrs.filter(a => a.name !== "format").concat([{ id: uid("attr"), name: "format", value: "json" }]);
                            updateBlock(b.id, { content, attrs });
                          }}
                          title="JSON array"
                        >
                          JSON Array
                        </button>
                        <button
                          className="px-2 py-1 text-xs border border-black hover:bg-black hover:text-white"
                          onClick={() => {
                            const content = `<response>
  <answer>Your response here</answer>
  <reasoning>Explanation if needed</reasoning>
</response>`;
                            const attrs = b.attrs.filter(a => a.name !== "format").concat([{ id: uid("attr"), name: "format", value: "xml" }]);
                            updateBlock(b.id, { content, attrs });
                          }}
                          title="XML template"
                        >
                          XML
                        </button>
                        <button
                          className="px-2 py-1 text-xs border border-black hover:bg-black hover:text-white"
                          onClick={() => {
                            const content = `Plain text response`;
                            const attrs = b.attrs.filter(a => a.name !== "format").concat([{ id: uid("attr"), name: "format", value: "text" }]);
                            updateBlock(b.id, { content, attrs });
                          }}
                          title="Plain text template"
                        >
                          Plain
                        </button>
                        <button
                          className="px-2 py-1 text-xs border border-black hover:bg-black hover:text-white"
                          onClick={() => {
                            const content = `## Response

- Key points in bullet form
- Clear structure

**Important:** Highlight key information`;
                            const attrs = b.attrs.filter(a => a.name !== "format").concat([{ id: uid("attr"), name: "format", value: "markdown" }]);
                            updateBlock(b.id, { content, attrs });
                          }}
                          title="Markdown template"
                        >
                          Markdown
                        </button>
                      </div>
                    )}
                    {/* Style quick selectors for style blocks */}
                    {b.tag === "style" && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        <button
                          className="px-2 py-1 text-xs border border-black hover:bg-black hover:text-white"
                          onClick={() => updateBlock(b.id, { content: "Professional and clear" })}
                          title="Professional style"
                        >
                          Professional
                        </button>
                        <button
                          className="px-2 py-1 text-xs border border-black hover:bg-black hover:text-white"
                          onClick={() => updateBlock(b.id, { content: "Friendly and conversational" })}
                          title="Friendly style"
                        >
                          Friendly
                        </button>
                        <button
                          className="px-2 py-1 text-xs border border-black hover:bg-black hover:text-white"
                          onClick={() => updateBlock(b.id, { content: "Concise and direct" })}
                          title="Concise style"
                        >
                          Concise
                        </button>
                        <button
                          className="px-2 py-1 text-xs border border-black hover:bg-black hover:text-white"
                          onClick={() => updateBlock(b.id, { content: "Academic and formal" })}
                          title="Academic style"
                        >
                          Academic
                        </button>
                        <button
                          className="px-2 py-1 text-xs border border-black hover:bg-black hover:text-white"
                          onClick={() => updateBlock(b.id, { content: "Technical and precise" })}
                          title="Technical style"
                        >
                          Technical
                        </button>
                        <button
                          className="px-2 py-1 text-xs border border-black hover:bg-black hover:text-white"
                          onClick={() => updateBlock(b.id, { content: "Creative and engaging" })}
                          title="Creative style"
                        >
                          Creative
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </li>
            );})}
          </ul>

          {/* moved library to preview panel */}
        </div>

        {/* Preview */}
        <div aria-labelledby="preview-title" className="border border-black flex flex-col">
          <h2 id="preview-title" className="px-3 h-12 border-b border-black flex items-center justify-between text-sm tracking-wide">
            <div className="flex items-center gap-2">
              <span>Preview</span>
              <input
                type="number"
                min={0}
                max={8}
                className="ml-4 h-8 w-16 px-2 border border-black"
                value={indent}
                onChange={(e) => setIndent(Number(e.target.value) || 0)}
                title="Indent spaces"
              />
            </div>
            <div className="flex items-center gap-2">
              <ToolbarButton onClick={handleCopy}>Copy</ToolbarButton>
              <ToolbarButton onClick={handleDownload}>Download</ToolbarButton>
            </div>
          </h2>
          {/* Templates mini bar above preview */}
          <div className="px-3 py-2 border-b border-black flex items-center gap-2 text-sm flex-wrap sm:flex-nowrap">
            <select
              className="h-8 px-2 border border-black min-w-0 flex-shrink-0 text-xs sm:text-sm"
              onChange={(e) => handleTemplateSelect(e.target.value)}
              defaultValue=""
              title="Load a template"
            >
              <option value="" disabled>Templates</option>
              <optgroup label="Built-in">
                <option value="builtin:blank">Blank</option>
                <option value="builtin:starter">Starter</option>
                <option value="builtin:qa">Q&A</option>
                <option value="builtin:cot">Chain-of-thought</option>
              </optgroup>
              {templates.length > 0 && (
                <optgroup label="Custom">
                  {templates.map((t) => (
                    <option key={t.id} value={`custom:${t.id}`}>{t.name}</option>
                  ))}
                </optgroup>
              )}
            </select>
            <input
              type="text"
              className="h-8 w-32 sm:w-44 px-2 border border-black"
              placeholder="Template name"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') saveCurrentAsTemplate(); }}
              title="Template name"
            />
            <button
              className="h-8 px-2 border border-black"
              title="Save current as template"
              onClick={() => saveCurrentAsTemplate()}
            >
              + Save
            </button>
          </div>
          <div className="p-3 flex-1 overflow-auto">
            <pre className="text-sm leading-6 overflow-x-auto">
              <code>{xml}</code>
            </pre>
          </div>
          {/* Removed lower Templates & History UI; managed via header and sidebar */}
        </div>
      </section>

      {/* History Sidebar Drawer */}
      {isHistoryOpen && <div className="drawer-backdrop" onClick={() => setIsHistoryOpen(false)} />}
      <aside className={`drawer ${isHistoryOpen ? 'open' : ''} flex flex-col`} aria-label="History">
        <div className="h-16 px-4 border-b border-black flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm tracking-wide">History</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              className="h-8 px-2 border border-black text-sm"
              onClick={() => setIsHistoryOpen(false)}
              aria-label="Close History"
            >Close</button>
          </div>
        </div>
        <div className="px-3 pr-4 py-3 border-b border-black flex items-center gap-2 flex-wrap">
          <input
            type="text"
            className="h-8 w-40 px-2 border border-black"
            placeholder="Title"
            value={historyTitle}
            onChange={(e) => setHistoryTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                const title = (historyTitle || 'Untitled').trim();
                const entry: HistoryEntry = { id: uid('his'), title, blocks: blocks.map((b) => ({ ...b, id: uid('blk'), attrs: b.attrs.map((a) => ({ ...a, id: uid('attr') })) })), createdAt: Date.now() };
                setHistory((prev) => {
                  const next = [entry, ...prev].slice(0, MAX_HISTORY);
                  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(next)); } catch {}
                  return next;
                });
                setHistoryTitle('');
              }
            }}
          />
          <button
            className="h-8 px-2 border border-black text-sm"
            onClick={() => {
              const title = (historyTitle || 'Untitled').trim();
              const entry: HistoryEntry = { id: uid('his'), title, blocks: blocks.map((b) => ({ ...b, id: uid('blk'), attrs: b.attrs.map((a) => ({ ...a, id: uid('attr') })) })), createdAt: Date.now() };
              setHistory((prev) => {
                const next = [entry, ...prev].slice(0, MAX_HISTORY);
                try { localStorage.setItem(HISTORY_KEY, JSON.stringify(next)); } catch {}
                return next;
              });
              setHistoryTitle('');
            }}
          >Snapshot</button>
          <button
            className="h-8 px-2 border border-black text-sm"
            onClick={() => {
              const blob = new Blob([JSON.stringify(history, null, 2)], { type: 'application/json;charset=utf-8' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = 'PromptHistory.json';
              document.body.appendChild(a);
              a.click();
              a.remove();
              URL.revokeObjectURL(url);
            }}
          >Export</button>
          <button
            className="h-8 px-2 border border-black text-sm"
            onClick={() => importHistoryRef.current?.click()}
          >Import</button>
          <button
            className="h-8 px-2 border border-black text-sm"
            title="Clear all history"
            onClick={() => {
              setHistory(() => {
                try { localStorage.setItem(HISTORY_KEY, JSON.stringify([])); } catch {}
                return [];
              });
            }}
          >Clear</button>
          <input
            ref={importHistoryRef}
            type="file"
            accept=".json,application/json,text/plain"
            className="hidden"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              try {
                const text = await file.text();
                const list = JSON.parse(text);
                if (Array.isArray(list)) {
                  const remapped: HistoryEntry[] = list.map((h: any) => ({
                    id: uid('his'),
                    title: String(h.title || 'Imported'),
                    blocks: Array.isArray(h.blocks) ? h.blocks.map((b: any) => ({
                      id: uid('blk'),
                      tag: String(b.tag || 'custom'),
                      content: String(b.content || ''),
                      attrs: Array.isArray(b.attrs) ? b.attrs.map((a: any) => ({ id: uid('attr'), name: String(a.name || ''), value: String(a.value || '') })) : [],
                    })) : [],
                    createdAt: Date.now(),
                  }));
                  setHistory((prev) => {
                    const next = [...remapped, ...prev].slice(0, MAX_HISTORY);
                    try { localStorage.setItem(HISTORY_KEY, JSON.stringify(next)); } catch {}
                    return next;
                  });
                }
              } catch {}
              e.currentTarget.value = '';
            }}
          />
          <span className="text-sm text-neutral-500 w-full">All of your data is stored locally in your browser.</span>
        </div>
        <div className="p-3 overflow-auto flex-1">
          <ul className="divide-y divide-black">
            {history.length === 0 && (
              <li className="py-2 text-sm text-neutral-600">No history yet.</li>
            )}
            {history.map((h) => (
              <li key={h.id} className="py-2 flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="text-sm">{h.title}</span>
                  <span className="text-sm text-neutral-500">{new Date(h.createdAt).toLocaleString()}</span>
                </div>
                <div className="flex items-center gap-1">
                  <button className="h-8 px-2 border border-black text-sm" onClick={() => setBlocks(h.blocks.map((b) => ({ ...b, id: uid('blk'), attrs: b.attrs.map((a) => ({ ...a, id: uid('attr') })) })))}>Load</button>
                  <button className="h-8 w-8 border border-black" title="Delete" onClick={() => {
                    setHistory((prev) => {
                      const next = prev.filter((x) => x.id !== h.id);
                      try { localStorage.setItem(HISTORY_KEY, JSON.stringify(next)); } catch {}
                      return next;
                    });
                  }}>✕</button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </main>
  );
}
