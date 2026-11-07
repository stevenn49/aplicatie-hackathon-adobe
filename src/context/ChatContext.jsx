import { createContext, useCallback, useContext, useEffect, useMemo, useState, useSyncExternalStore } from "react";

// Charts on the current page register their data here so the assistant can analyse them.
// A tiny external store (not React state) keeps registration from re-rendering the pages.
function createChartStore() {
  const charts = new Map();
  const listeners = new Set();
  let snapshot = [];
  const emit = () => { snapshot = [...charts.entries()].map(([id, chart]) => ({ id, ...chart })); listeners.forEach((fn) => fn()); };
  return {
    set(id, chart) { charts.set(id, chart); emit(); },
    remove(id) { if (charts.delete(id)) emit(); },
    subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    getSnapshot: () => snapshot,
  };
}

const ChatContext = createContext(null);
export const chartId = (title) => String(title).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

export function ChatProvider({ children }) {
  const [store] = useState(createChartStore);
  const [open, setOpen] = useState(false);
  const [request, setRequest] = useState(null); // { message, focusChart, nonce }

  const askAssistant = useCallback((message, focusChart = null) => {
    setOpen(true);
    setRequest({ message, focusChart, nonce: Date.now() + Math.random() });
  }, []);
  const value = useMemo(() => ({ store, open, setOpen, request, askAssistant }), [store, open, request, askAssistant]);
  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChat() {
  const context = useContext(ChatContext);
  if (!context) throw new Error("useChat must be used within ChatProvider");
  return context;
}

export function useRegisteredCharts() {
  const { store } = useChat();
  return useSyncExternalStore(store.subscribe, store.getSnapshot);
}

/** Register a chart's data with the assistant while the component is mounted. */
export function useRegisterChart(chart) {
  const { store } = useChat();
  const id = chart?.title && chart?.data ? chartId(chart.title) : null;
  useEffect(() => {
    if (!id) return undefined;
    store.set(id, { title: chart.title, subtitle: typeof chart.subtitle === "string" ? chart.subtitle : undefined, data: chart.data, note: chart.note });
    return () => store.remove(id);
  }, [store, id, chart?.data, chart?.subtitle, chart?.note]);
  return id;
}

/** Registers data that is shown on the page but not inside a ChartCard (KPI tiles, matrices, ...). */
export function ChartData({ title, subtitle, data, note }) {
  useRegisterChart({ title, subtitle, data, note });
  return null;
}
