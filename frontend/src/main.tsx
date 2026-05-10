import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, BarChart3, Bot, FileText, Gauge, MessagesSquare, Play } from 'lucide-react';
import './styles.css';

type Page = 'dashboard' | 'requests' | 'models' | 'playground';

type Metrics = {
  total_requests: number;
  success_requests: number;
  failed_requests: number;
  active_requests: number;
  cache_hit_rate: number;
  avg_latency_ms: number;
  avg_ttft_ms: number;
  error_rate: number;
};

type RequestLog = {
  time?: string;
  request_id?: string;
  user?: string;
  model?: string;
  backend?: string;
  stream?: boolean;
  cache_hit?: boolean;
  ttft_ms?: number | null;
  total_latency_ms?: number;
  status?: string;
  error?: string | null;
};

type ModelInfo = {
  model: string;
  backend: string;
  endpoint: string | null;
  model_name: string;
  max_context_tokens?: number | null;
};

const API_BASE = import.meta.env.VITE_GATEWAY_API_BASE ?? 'http://127.0.0.1:8000';

const navItems: Array<{ id: Page; label: string; icon: React.ReactNode }> = [
  { id: 'dashboard', label: 'Dashboard', icon: <Gauge size={18} /> },
  { id: 'requests', label: 'Requests', icon: <FileText size={18} /> },
  { id: 'models', label: 'Models', icon: <Bot size={18} /> },
  { id: 'playground', label: 'Playground', icon: <MessagesSquare size={18} /> },
];

function App() {
  const [page, setPage] = useState<Page>('dashboard');

  return (
    <div className="min-h-screen bg-slate-100 text-ink">
      <aside className="fixed inset-y-0 left-0 w-64 border-r border-line bg-white">
        <div className="flex h-16 items-center gap-3 border-b border-line px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded bg-cyan-600 text-white">
            <Activity size={20} />
          </div>
          <div>
            <div className="text-sm font-semibold">LightLLM</div>
            <div className="text-xs text-slate-500">Gateway Console</div>
          </div>
        </div>
        <nav className="space-y-1 p-3">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setPage(item.id)}
              className={`flex w-full items-center gap-3 rounded px-3 py-2 text-left text-sm transition ${
                page === item.id
                  ? 'bg-cyan-50 text-cyan-800'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="ml-64 min-h-screen p-6">
        {page === 'dashboard' && <Dashboard />}
        {page === 'requests' && <Requests />}
        {page === 'models' && <Models />}
        {page === 'playground' && <Playground />}
      </main>
    </div>
  );
}

function Dashboard() {
  const { data, loading, error, reload } = useFetch<Metrics>('/metrics');
  const cards = useMemo(
    () => [
      ['Total requests', data?.total_requests],
      ['Success requests', data?.success_requests],
      ['Failed requests', data?.failed_requests],
      ['Active requests', data?.active_requests],
      ['Cache hit rate', asPercent(data?.cache_hit_rate)],
      ['Avg latency', asMs(data?.avg_latency_ms)],
      ['Avg TTFT', asMs(data?.avg_ttft_ms)],
      ['Error rate', asPercent(data?.error_rate)],
    ],
    [data],
  );

  return (
    <Screen title="Dashboard" action={<RefreshButton onClick={reload} />}>
      <State loading={loading} error={error} />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map(([label, value]) => (
          <div key={label} className="rounded border border-line bg-white p-4">
            <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
            <div className="mt-3 text-2xl font-semibold">{value ?? '-'}</div>
          </div>
        ))}
      </div>
    </Screen>
  );
}

function Requests() {
  const { data, loading, error, reload } = useFetch<RequestLog[]>('/api/requests?limit=100');
  return (
    <Screen title="Requests" action={<RefreshButton onClick={reload} />}>
      <State loading={loading} error={error} />
      <Table
        headers={[
          'time',
          'request_id',
          'user',
          'model',
          'backend',
          'stream',
          'cache_hit',
          'ttft_ms',
          'total_latency_ms',
          'status',
          'error',
        ]}
        rows={(data ?? []).map((item) => [
          item.time,
          item.request_id,
          item.user,
          item.model,
          item.backend,
          String(item.stream ?? ''),
          String(item.cache_hit ?? ''),
          asMs(item.ttft_ms),
          asMs(item.total_latency_ms),
          item.status,
          item.error,
        ])}
      />
    </Screen>
  );
}

function Models() {
  const { data, loading, error, reload } = useFetch<ModelInfo[]>('/api/models');
  return (
    <Screen title="Models" action={<RefreshButton onClick={reload} />}>
      <State loading={loading} error={error} />
      <Table
        headers={['model', 'backend', 'endpoint', 'model_name', 'max_context_tokens']}
        rows={(data ?? []).map((item) => [
          item.model,
          item.backend,
          item.endpoint,
          item.model_name,
          item.max_context_tokens ?? '',
        ])}
      />
    </Screen>
  );
}

function Playground() {
  const { data: models } = useFetch<ModelInfo[]>('/api/models');
  const [model, setModel] = useState('mock-small');
  const [apiKey, setApiKey] = useState('sk-demo');
  const [message, setMessage] = useState('hello');
  const [stream, setStream] = useState(false);
  const [response, setResponse] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (models?.length && !models.some((item) => item.model === model)) {
      setModel(models[0].model);
    }
  }, [models, model]);

  async function send() {
    setLoading(true);
    setError(null);
    setResponse('');
    try {
      const payload = {
        model,
        messages: [{ role: 'user', content: message }],
        stream,
      };
      const res = await fetch(`${API_BASE}/v1/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        setError(await res.text());
        return;
      }
      if (!stream) {
        const data = await res.json();
        setResponse(data.choices?.[0]?.message?.content ?? JSON.stringify(data, null, 2));
        return;
      }
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) {
        setError('Response stream is not available.');
        return;
      }
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        setResponse((current) => current + decoder.decode(value, { stream: true }));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen title="Playground">
      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <div className="space-y-4 rounded border border-line bg-white p-4">
          <label className="block text-sm font-medium">
            Model
            <select
              className="mt-2 w-full rounded border border-line px-3 py-2"
              value={model}
              onChange={(event) => setModel(event.target.value)}
            >
              {(models ?? [{ model: 'mock-small' } as ModelInfo]).map((item) => (
                <option key={item.model} value={item.model}>
                  {item.model}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-medium">
            API Key
            <input
              className="mt-2 w-full rounded border border-line px-3 py-2"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
            />
          </label>
          <label className="block text-sm font-medium">
            User Message
            <textarea
              className="mt-2 min-h-32 w-full rounded border border-line px-3 py-2"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
            />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={stream} onChange={(event) => setStream(event.target.checked)} />
            stream=true
          </label>
          <button
            onClick={send}
            disabled={loading}
            className="inline-flex w-full items-center justify-center gap-2 rounded bg-cyan-700 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-800 disabled:opacity-60"
          >
            <Play size={16} />
            {loading ? 'Sending...' : 'Send'}
          </button>
        </div>
        <div className="rounded border border-line bg-white p-4">
          <div className="mb-3 text-sm font-semibold">Response</div>
          {error && <div className="mb-3 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
          <pre className="min-h-96 overflow-auto whitespace-pre-wrap rounded bg-slate-950 p-4 text-sm text-slate-100">
            {response || 'No response yet.'}
          </pre>
        </div>
      </div>
    </Screen>
  );
}

function Screen({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section>
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{title}</h1>
          <p className="mt-1 text-sm text-slate-500">Backend: {API_BASE}</p>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function RefreshButton({ onClick }: { onClick: () => void }) {
  return (
    <button onClick={onClick} className="rounded border border-line bg-white px-3 py-2 text-sm hover:bg-slate-50">
      Refresh
    </button>
  );
}

function State({ loading, error }: { loading: boolean; error: string | null }) {
  if (loading) return <div className="mb-4 rounded border border-line bg-white p-3 text-sm">Loading...</div>;
  if (error) return <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>;
  return null;
}

function Table({ headers, rows }: { headers: string[]; rows: Array<Array<React.ReactNode>> }) {
  return (
    <div className="overflow-x-auto rounded border border-line bg-white">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-500">
          <tr>
            {headers.map((header) => (
              <th key={header} className="whitespace-nowrap px-3 py-3 font-medium">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td className="px-3 py-4 text-slate-500" colSpan={headers.length}>
                No data
              </td>
            </tr>
          ) : (
            rows.map((row, index) => (
              <tr key={index} className="border-t border-line">
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex} className="whitespace-nowrap px-3 py-3 text-slate-700">
                    {cell ?? ''}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

function useFetch<T>(path: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}${path}`);
      if (!response.ok) throw new Error(await response.text());
      setData((await response.json()) as T);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [path]);

  return { data, loading, error, reload: load };
}

function asMs(value: number | null | undefined) {
  if (value === null || value === undefined) return '-';
  return `${value.toFixed(1)} ms`;
}

function asPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return '-';
  return `${(value * 100).toFixed(1)}%`;
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
