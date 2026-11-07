import { Fragment, memo, useCallback, useEffect, useRef, useState } from "react";
import { BarChart3, Lightbulb, Megaphone, PenLine, RotateCcw, Send, Sparkles, Square, Swords, FileText, X } from "lucide-react";
import { useChat, useRegisteredCharts } from "../context/ChatContext.jsx";
import { useFilters } from "../context/AppContext.jsx";
import { streamAssistantChat } from "../services/api.js";

const INTENT_LABELS = {
  chart_analysis: "Chart analysis", ideas: "Marketing ideas", campaign: "Campaign plan", calendar: "Content calendar",
  copy: "Copywriting", competitor: "Competitor comparison", sentiment: "Sentiment analysis", summary: "Summary", general: "Answer",
};

function quickActions(brand) {
  const who = brand === "All brands" ? "our brand" : brand;
  return [
    { icon: BarChart3, label: "Analyse the charts on this page", prompt: "Analyse all the charts on this page and tell me the most important insights." },
    { icon: Lightbulb, label: "Suggest marketing ideas", prompt: `Suggest 5 marketing ideas for ${who} based on this data.` },
    { icon: Megaphone, label: "Plan a campaign", prompt: `Plan a 4-week launch campaign for ${who}.` },
    { icon: PenLine, label: "Write ad copy", prompt: `Write ad copy and social captions for ${who}.` },
    { icon: Swords, label: "Compare competitors", prompt: `Compare ${who} against its main competitors.` },
    { icon: FileText, label: "Summarise this page", prompt: "Give me an executive summary of this page." },
  ];
}

// ---------------------------------------------------------------- minimal, safe Markdown rendering
function inline(text) {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*|_[^_\s][^_]*_)/g).filter(Boolean).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) return <code key={i}>{part.slice(1, -1)}</code>;
    if ((part.startsWith("*") && part.endsWith("*")) || (part.startsWith("_") && part.endsWith("_"))) return <em key={i}>{part.slice(1, -1)}</em>;
    return <Fragment key={i}>{part}</Fragment>;
  });
}

// Memoised: without this, every streamed chunk re-parsed every earlier message
// in the conversation as well as the one being written.
const Markdown = memo(function Markdown({ text }) {
  const lines = text.replace(/\r/g, "").split("\n");
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    const heading = line.match(/^(#{1,4})\s+(.*)/);
    if (heading) { blocks.push(<h4 key={i}>{inline(heading[2])}</h4>); i++; continue; }
    if (/^\s*\|.*\|\s*$/.test(line)) {
      const rows = [];
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) { rows.push(lines[i]); i++; }
      const cells = rows.filter((r) => !/^\s*\|[\s:|-]+\|\s*$/.test(r)).map((r) => r.trim().slice(1, -1).split("|").map((c) => c.trim()));
      const [head, ...body] = cells;
      blocks.push(<div className="chat-table-wrap" key={`t${i}`}><table><thead><tr>{head.map((c, j) => <th key={j}>{inline(c)}</th>)}</tr></thead><tbody>{body.map((r, k) => <tr key={k}>{r.map((c, j) => <td key={j}>{inline(c)}</td>)}</tr>)}</tbody></table></div>);
      continue;
    }
    const listMatch = /^\s*([-*•]|\d+[.)])\s+/;
    if (listMatch.test(line)) {
      const ordered = /^\s*\d/.test(line);
      const items = [];
      while (i < lines.length && (listMatch.test(lines[i]) || (/^\s{2,}\S/.test(lines[i]) && items.length))) {
        const indented = /^\s{2,}/.test(lines[i]);
        const content = lines[i].replace(listMatch, "").trim();
        if (indented && items.length) items[items.length - 1].sub.push(content); else items.push({ content, sub: [] });
        i++;
      }
      const Tag = ordered ? "ol" : "ul";
      blocks.push(<Tag key={`l${i}`}>{items.map((item, k) => <li key={k}>{inline(item.content)}{item.sub.length > 0 && <ul>{item.sub.map((s, m) => <li key={m}>{inline(s)}</li>)}</ul>}</li>)}</Tag>);
      continue;
    }
    const para = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|\s*\||\s*([-*•]|\d+[.)])\s)/.test(lines[i])) { para.push(lines[i]); i++; }
    blocks.push(<p key={`p${i}`}>{inline(para.join(" "))}</p>);
  }
  return <div className="chat-markdown">{blocks}</div>;
});

/**
 * While an answer is still arriving, only the blocks that are already complete
 * are parsed as Markdown; the unfinished tail is rendered as plain text.
 *
 * The completed prefix is a stable string between block boundaries, so the
 * memoised Markdown above skips re-parsing it on most chunks. Without this,
 * every chunk re-parsed the entire answer from scratch and the tab ran out of
 * memory on long replies.
 */
const StreamingMarkdown = memo(function StreamingMarkdown({ text, streaming }) {
  if (!streaming) return <Markdown text={text} />;
  const cut = text.lastIndexOf("\n\n");
  const stable = cut > 0 ? text.slice(0, cut) : "";
  const tail = cut > 0 ? text.slice(cut + 2) : text;
  return (
    <>
      {stable && <Markdown text={stable} />}
      {tail && <div className="chat-markdown"><p>{tail}<span className="chat-caret" aria-hidden="true" /></p></div>}
    </>
  );
});

// ---------------------------------------------------------------- chat panel
export default function AssistantChat({ pageTitle, pagePath }) {
  const { open, setOpen, request } = useChat();
  const charts = useRegisteredCharts();
  const { filters } = useFilters();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const abortRef = useRef(null);
  const listRef = useRef(null);
  const chartsRef = useRef(charts);
  chartsRef.current = charts;
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  useEffect(() => { listRef.current?.scrollTo({ top: listRef.current.scrollHeight }); }, [messages]);
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => { if (event.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  const send = useCallback(async (text, focusChart = null) => {
    const message = text.trim();
    if (!message || abortRef.current) return;
    const history = messagesRef.current.filter((m) => !m.error && m.content).map(({ role, content }) => ({ role, content }));
    const focusTitle = focusChart && chartsRef.current.find((c) => c.id === focusChart)?.title;
    setMessages((current) => [...current, { role: "user", content: message, chart: focusTitle }, { role: "assistant", content: "", pending: true }]);
    setInput("");
    setBusy(true);
    const controller = new AbortController();
    abortRef.current = controller;
    // A chunk that arrives after the user pressed Stop must not resurrect the
    // message that stop() already marked as stopped.
    const update = (patch) => {
      if (controller.signal.aborted) return;
      setMessages((current) => current.map((m, idx) => idx === current.length - 1 ? { ...m, ...patch } : m));
    };
    try {
      await streamAssistantChat({
        message, history, brand: filters.brand, focusChart,
        page: { path: pagePath, title: pageTitle, filters },
        charts: chartsRef.current,
      }, (content, meta) => update({ content, intent: meta.intent, model: meta.model, pending: false }), controller.signal);
      update({ pending: false });
    } catch (error) {
      // stop() has already marked the message; anything else is a real failure.
      if (error.name !== "AbortError") update({ pending: false, error: true, content: error.message });
    } finally {
      // Only the request that still owns the ref may clear it — a Stop
      // followed immediately by a new question must not be un-busied by the
      // old request finishing.
      if (abortRef.current === controller) {
        abortRef.current = null;
        setBusy(false);
      }
    }
  }, [filters, pagePath, pageTitle]);

  // Requests coming from "Analyse" buttons on chart cards.
  useEffect(() => { if (request) send(request.message, request.focusChart); }, [request]); // eslint-disable-line react-hooks/exhaustive-deps

  // Stop must be self-contained: it marks the message and releases the button
  // immediately, instead of waiting for the aborted fetch to reject.
  const stop = useCallback(() => {
    const controller = abortRef.current;
    if (!controller) return;
    abortRef.current = null;
    controller.abort();
    setBusy(false);
    setMessages((current) => current.map((m, idx) => idx === current.length - 1 ? { ...m, pending: false, stopped: true } : m));
  }, []);
  const reset = () => { stop(); setMessages([]); };
  const onSubmit = (event) => { event.preventDefault(); send(input); };
  const onKeyDown = (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); send(input); } };

  return <>
    {!open && <button className="assistant-launcher" onClick={() => setOpen(true)} aria-label="Open MarketPulse AI assistant"><Sparkles size={18} /><span>Ask AI</span></button>}
    {open && <aside className="assistant-panel" role="dialog" aria-label="MarketPulse AI assistant">
      <header className="assistant-header">
        <span className="assistant-avatar"><Sparkles size={15} /></span>
        <div className="assistant-title"><strong>MarketPulse AI</strong><small>Sees {charts.length} {charts.length === 1 ? "chart" : "charts"} on {pageTitle}{filters.brand !== "All brands" ? ` · ${filters.brand}` : ""}</small></div>
        <button className="icon-button" onClick={reset} aria-label="Start a new conversation" title="New conversation"><RotateCcw size={15} /></button>
        <button className="icon-button" onClick={() => setOpen(false)} aria-label="Close assistant"><X size={16} /></button>
      </header>
      <div className="assistant-messages" ref={listRef} aria-live="polite">
        {!messages.length && <div className="assistant-welcome">
          <p>Hi! I can analyse the charts on this page, suggest marketing ideas, plan campaigns, write copy and compare competitors. Every answer is based on your dashboard data.</p>
          <div className="assistant-quick">{quickActions(filters.brand).map(({ icon: Icon, label, prompt }) => <button key={label} onClick={() => send(prompt)}><Icon size={14} />{label}</button>)}</div>
          {charts.length > 0 && <div className="assistant-chart-list"><span>Or analyse one chart:</span>{charts.map((c) => <button key={c.id} onClick={() => send(`Analyse the "${c.title}" chart`, c.id)}><BarChart3 size={12} />{c.title}</button>)}</div>}
        </div>}
        {messages.map((m, idx) => <div key={idx} className={`chat-msg ${m.role} ${m.error ? "error" : ""}`}>
          {m.role === "user" ? <><p>{m.content}</p>{m.chart && <small className="chat-chart-tag"><BarChart3 size={11} /> {m.chart}</small>}</>
            : m.pending ? <div className="chat-typing" aria-label="Thinking"><i /><i /><i /></div>
            : <>{m.intent && <span className="chat-intent">{INTENT_LABELS[m.intent] || m.intent}{m.model ? ` · ${m.model}` : ""}</span>}{m.error ? <p>{m.content}</p> : <StreamingMarkdown text={m.content} streaming={idx === messages.length - 1 && busy && !m.stopped} />}{m.stopped && <small className="chat-stopped">Stopped</small>}</>}
        </div>)}
      </div>
      <form className="assistant-input" onSubmit={onSubmit}>
        <textarea rows={1} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={onKeyDown} placeholder="Ask about this page, or for ideas…" aria-label="Message MarketPulse AI" />
        {busy ? <button type="button" className="assistant-send" onClick={stop} aria-label="Stop generating"><Square size={14} /></button>
          : <button type="submit" className="assistant-send" disabled={!input.trim()} aria-label="Send message"><Send size={15} /></button>}
      </form>
    </aside>}
  </>;
}
