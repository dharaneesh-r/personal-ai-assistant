import type { RagOptions, EvalResult } from '../types'

const BASE = ''

export async function streamChat(
  prompt: string,
  model: string,
  history: { role: string; content: string }[],
  onToken: (token: string) => void
): Promise<void> {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, model, history }),
  })
  const reader = res.body!.getReader()
  const dec = new TextDecoder()
  let buf = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    const lines = buf.split('\n')
    buf = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const payload = line.slice(6).trim()
      if (payload === '[DONE]') return
      try {
        const obj = JSON.parse(payload)
        if (obj.token) onToken(obj.token)
      } catch {}
    }
  }
}

export async function queryRag(
  question: string,
  model: string,
  opts: RagOptions,
  history: { user: string; assistant: string }[]
) {
  const res = await fetch(`${BASE}/rag/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question, model,
      top_k: opts.topK,
      score_threshold: opts.scoreThreshold,
      use_hybrid: opts.useHybrid,
      use_rerank: opts.useRerank,
      rewrite_query: opts.rewriteQuery,
      use_graph: opts.useGraph,
      source_filter: opts.sourceFilter,
      history,
    }),
  })
  if (!res.ok) throw new Error((await res.json()).detail)
  return res.json()
}

export async function runAgent(message: string, model: string, sessionId?: string) {
  const res = await fetch(`${BASE}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, model, session_id: sessionId || undefined }),
  })
  if (!res.ok) throw new Error((await res.json()).detail)
  return res.json()
}

export async function getSources() {
  const res = await fetch(`${BASE}/rag/sources`)
  return res.json()
}

export async function deleteSource(source: string) {
  const res = await fetch(`${BASE}/rag/sources?source=${encodeURIComponent(source)}`, { method: 'DELETE' })
  return res.json()
}

export async function ingestFile(file: File, useContextual = false) {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('use_contextual', useContextual.toString())
  const res = await fetch(`${BASE}/ingest/file`, { method: 'POST', body: fd })
  if (!res.ok) throw new Error((await res.json()).detail)
  return res.json()
}

export async function ingestUrl(url: string, useContextual = false) {
  const res = await fetch(`${BASE}/ingest/url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, use_contextual: useContextual }),
  })
  if (!res.ok) throw new Error((await res.json()).detail)
  return res.json()
}

export async function ingestText(text: string, sourceName: string, useContextual = false) {
  const res = await fetch(`${BASE}/ingest/text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, source_name: sourceName, use_contextual: useContextual }),
  })
  if (!res.ok) throw new Error((await res.json()).detail)
  return res.json()
}

export async function createSession() {
  const res = await fetch(`${BASE}/agent/session`, { method: 'POST' })
  return res.json()
}

export async function deleteSession(sessionId: string) {
  return fetch(`${BASE}/agent/session/${sessionId}`, { method: 'DELETE' })
}

export async function debugRag(query: string, topK = 8, useHybrid = true, useRerank = false) {
  const res = await fetch(`${BASE}/rag/debug`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK, score_threshold: 0.0, use_hybrid: useHybrid, use_rerank: useRerank }),
  })
  if (!res.ok) throw new Error((await res.json()).detail)
  return res.json()
}

export async function clearAllSources() {
  const res = await fetch(`${BASE}/rag/sources/all`, { method: 'DELETE' })
  return res.json()
}

export async function runEval(question: string, answer: string, context: string, model: string): Promise<EvalResult> {
  const res = await fetch(`${BASE}/eval/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, answer, context, model }),
  })
  if (!res.ok) throw new Error((await res.json()).detail)
  return res.json()
}

export async function getGraph() {
  const res = await fetch(`${BASE}/rag/graph`)
  if (!res.ok) throw new Error((await res.json()).detail)
  return res.json()
}

export async function clearGraph() {
  const res = await fetch(`${BASE}/rag/graph/clear`, { method: 'DELETE' })
  if (!res.ok) throw new Error((await res.json()).detail)
  return res.json()
}

// --- History API ---

export async function fetchChats() {
  const res = await fetch(`${BASE}/history/chats`)
  if (!res.ok) throw new Error((await res.json()).detail)
  return res.json()
}

export async function fetchChatDetail(sessionId: string) {
  const res = await fetch(`${BASE}/history/chats/${sessionId}`)
  if (!res.ok) throw new Error((await res.json()).detail)
  return res.json()
}

export async function saveSessionOnBackend(session: { id: string; title: string; mode: string; model: string; created_at: string }) {
  const res = await fetch(`${BASE}/history/chats`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(session),
  })
  if (!res.ok) throw new Error((await res.json()).detail)
  return res.json()
}

export async function appendMessageOnBackend(
  sessionId: string,
  message: {
    id: string
    role: string
    content: string
    mode: string
    timestamp: string
    sources?: string[]
    chunks_used?: number
    rewritten_query?: string
    tool_calls?: any[]
    iterations?: number
    model?: string
  }
) {
  const res = await fetch(`${BASE}/history/chats/${sessionId}/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(message),
  })
  if (!res.ok) throw new Error((await res.json()).detail)
  return res.json()
}

export async function deleteChatOnBackend(sessionId: string) {
  const res = await fetch(`${BASE}/history/chats/${sessionId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error((await res.json()).detail)
  return res.json()
}

export async function saveEvalRecord(evalRecord: any) {
  const res = await fetch(`${BASE}/history/evaluations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(evalRecord),
  })
  if (!res.ok) throw new Error((await res.json()).detail)
  return res.json()
}

export async function fetchEvaluations() {
  const res = await fetch(`${BASE}/history/evaluations`)
  if (!res.ok) throw new Error((await res.json()).detail)
  return res.json()
}
