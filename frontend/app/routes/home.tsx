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

const PALETTE = [
  { label: "system", tag: "system" },
  { label: "instruction", tag: "instruction" },
  { label: "context", tag: "context" },
  { label: "example", tag: "example" },
  { label: "input", tag: "input" },
  { label: "output", tag: "output_format" },
  { label: "note", tag: "note" },
  { label: "custom", tag: "custom" },
];

const STORAGE_KEY = "xml-block-builder:v2";

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
    const attrs = renderAttrs(b.attrs);
    const hasContent = b.content.trim().length > 0;
    const open = attrs ? `<${b.tag} ${attrs}>` : `<${b.tag}>`;
    lines.push(indent(level) + open);
    if (hasContent) {
      // multiline preserved
      b.content.split("\n").forEach((ln) => {
        lines.push(indent(level + 1) + escapeXml(ln));
      });
    }
    lines.push(indent(level) + `</${b.tag}>`);
  };

  blocks.forEach((b) => renderBlock(b, 0));
  return lines.join("\n");
}

function parseXmlToBlocks(xml: string): { root?: string; blocks: Block[]; wrapped?: boolean; error?: string } {
  try {
    const parser = new DOMParser();
    let doc = parser.parseFromString(xml, "text/xml");
    const perr = doc.getElementsByTagName("parsererror")[0];
    let wrapped = false;
    if (perr) {
      // Try wrapping with a root if multiple top-level nodes (internal only)
      doc = parser.parseFromString(`<x-root>\n${xml}\n</x-root>`, "text/xml");
      wrapped = true;
    }
    const err = doc.getElementsByTagName("parsererror")[0];
    if (err) {
      return { blocks: [], error: err.textContent || "XML parse error" };
    }
    const rootEl = doc.documentElement;
    // If the document element has element children, treat it as root
    const children = Array.from(rootEl.childNodes).filter((n) => n.nodeType === 1) as Element[];
    const hasElementChildren = children.length > 0;
    const targetEls = hasElementChildren ? children : [rootEl];
    const blocks: Block[] = targetEls.map((el) => ({
      id: uid("blk"),
      tag: el.tagName,
      content: (el.textContent || "").trim(),
      attrs: Array.from(el.attributes).map((a) => ({ id: uid("attr"), name: a.name, value: a.value })),
    }));

    // Only keep a root when input was a valid single-root XML we didn't wrap ourselves
    const rootName = !wrapped && hasElementChildren ? rootEl.tagName : undefined;
    return { root: rootName, blocks, wrapped };
  } catch (e: any) {
    return { blocks: [], error: e?.message || "Failed to parse XML" };
  }
}

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Prompt Blocks — XML Builder" },
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

function TextInput(
  props: React.InputHTMLAttributes<HTMLInputElement> & { label?: string; labelSrOnly?: boolean }
) {
  const { label, labelSrOnly, className = "", id, ...rest } = props;
  return (
    <label className="flex items-center gap-2 text-sm">
      {label && <span className={labelSrOnly ? "sr-only" : "min-w-16"}>{label}</span>}
      <input
        id={id}
        {...rest}
        className={`h-8 px-2 border border-black focus-visible:outline focus-visible:outline-2 focus-visible:outline-black ${className}`}
      />
    </label>
  );
}

function TextArea(
  props: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string; labelSrOnly?: boolean }
) {
  const { label, labelSrOnly, className = "", id, ...rest } = props;
  return (
    <label className="flex flex-col gap-2 text-sm">
      {label && <span className={labelSrOnly ? "sr-only" : ""}>{label}</span>}
      <textarea
        id={id}
        {...rest}
        className={`min-h-24 p-2 border border-black focus-visible:outline focus-visible:outline-2 focus-visible:outline-black ${className}`}
      />
    </label>
  );
}

export default function Home() {
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [indent, setIndent] = useState<number>(2);
  const [importError, setImportError] = useState<string | undefined>();
  const importRef = useRef<HTMLInputElement>(null);
  const [justAddedId, setJustAddedId] = useState<string | null>(null);
  const [bumped, setBumped] = useState<{ id: string; dir: -1 | 1 } | null>(null);
  const [removing, setRemoving] = useState<Set<string>>(new Set());

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
          { id: uid("blk"), tag: "output_format", content: "JSON with fields: answer, reasoning", attrs: [] },
        ]);
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

  function addBlock(tag: string) {
    const id = uid("blk");
    setBlocks((prev) => [
      ...prev,
      { id, tag, content: "", attrs: [] },
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
    navigator.clipboard.writeText(xml).catch(() => {});
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
  }

  function handleImportXml(text: string) {
    const { blocks: blks, error } = parseXmlToBlocks(text);
    setImportError(error);
    if (!error) {
      setBlocks(blks);
    }
  }

  function handleNew() {
    setBlocks([]);
    setIndent(2);
  }

  function loadTemplate(kind: string) {
    if (kind === "qa") {
      setBlocks([
        { id: uid("blk"), tag: "system", content: "You answer questions concisely.", attrs: [] },
        { id: uid("blk"), tag: "context", content: "Use only the provided context.", attrs: [] },
        { id: uid("blk"), tag: "input", content: "{question}", attrs: [{ id: uid("attr"), name: "role", value: "user" }] },
        { id: uid("blk"), tag: "output_format", content: "Plain text answer only.", attrs: [] },
      ]);
    } else if (kind === "cot") {
      setBlocks([
        { id: uid("blk"), tag: "system", content: "Reason step-by-step before final answer.", attrs: [] },
        { id: uid("blk"), tag: "instruction", content: "Think briefly, then answer.", attrs: [] },
        { id: uid("blk"), tag: "input", content: "{problem}", attrs: [] },
        { id: uid("blk"), tag: "output_format", content: "JSON { reasoning, answer }", attrs: [] },
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
              <ToolbarButton onClick={() => importRef.current?.click()} aria-label="Import TXT">Import</ToolbarButton>
              <input
                ref={importRef}
                type="file"
                accept=".txt,text/plain"
                className="hidden"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  const text = await file.text();
                  handleImportXml(text);
                  e.currentTarget.value = "";
                }}
              />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <input
              type="number"
              min={0}
              max={8}
              className="h-8 w-16 px-2 border border-black"
              value={indent}
              onChange={(e) => setIndent(Number(e.target.value) || 0)}
              title="Indent spaces"
            />
            <select
              className="h-8 px-2 border border-black"
              onChange={(e) => e.target.value && loadTemplate(e.target.value)}
              defaultValue=""
              title="Load a template"
            >
              <option value="" disabled>
                Templates
              </option>
              <option value="starter">Starter</option>
              <option value="qa">Q&A</option>
              <option value="cot">Chain-of-thought</option>
            </select>
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
                className="h-8 px-2 border border-black hover:bg-black hover:text-white text-sm"
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
              const animClass = isRemoving ? "anim-pop-out" : isAdded ? "anim-pop-in flash-bg" : isBumped;
              return (
              <li key={b.id} className={`p-3 ${animClass}`}>
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      className="h-8 w-36 px-2 border border-black"
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
                    <div className="text-xs text-neutral-600">No attributes</div>
                  )}
                  {b.attrs.map((a) => (
                    <div key={a.id} className="flex items-center gap-2">
                      <input
                        type="text"
                        className="h-8 w-40 px-2 border border-black"
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
                  <TextArea
                    label="Content"
                    placeholder="Text content (optional)."
                    value={b.content}
                    onChange={(e) => updateBlock(b.id, { content: e.target.value })}
                  />
                </div>
              </li>
            );})}
          </ul>
        </div>

        {/* Preview */}
        <div aria-labelledby="preview-title" className="border border-black flex flex-col">
          <h2 id="preview-title" className="px-3 h-12 border-b border-black flex items-center justify-between text-sm tracking-wide">
            <span>Preview</span>
            <div className="flex items-center gap-2">
              <ToolbarButton onClick={handleCopy}>Copy</ToolbarButton>
              <ToolbarButton onClick={handleDownload}>Download</ToolbarButton>
            </div>
          </h2>
          <div className="p-3 flex-1 overflow-auto">
            <pre className="text-sm leading-6 overflow-x-auto">
              <code>{xml}</code>
            </pre>
          </div>
          <div className="border-t border-black p-3">
            <TextArea
              label="Import"
              placeholder="Prompt"
              className="min-h-24"
              onChange={(e) => setImportError(undefined)}
              onBlur={(e) => {
                const text = e.target.value.trim();
                if (text) handleImportXml(text);
              }}
            />
            {importError && (
              <p className="mt-2 text-sm text-red-600">{importError}</p>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
