import { useState, useEffect, useRef, useCallback } from 'react'
import { Plus, Trash2, Settings2, RotateCcw, Bug } from 'lucide-react'
import Sidebar from './components/Sidebar'
import MessageItem from './components/MessageItem'
import EvalPanel from './components/EvalPanel'
import DebugPanel from './components/DebugPanel'
import type { Mode, Message, Source, RagOptions } from './types'
import { streamChat, queryRag, runAgent, getSources, createSession, deleteSession, clearAllSources } from './api/client'

const MODELS = ['llama-3.1-8b-instant', 'llama-3.3-70b-versatile']

function uid() {
  return Math.random().toString(36).slice(2)
}

interface Toast { id: string; msg: string; type: 'ok' | 'err' | 'info' }

export default function App() {
  const [mode, setMode] = useState<Mode>('chat')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [model, setModel] = useState('llama-3.1-8b-instant')
  const [sources, setSources] = useState<Source[]>([])
  const [toasts, setToasts] = useState<Toast[]>([])
  const [showOptions, setShowOptions] = useState(false)
  const [showDebug, setShowDebug] = useState(false)

  // RAG options
  const [ragOpts, setRagOpts] = useState<RagOptions>({
    topK: 5, scoreThreshold: 0.15,
    useHybrid: true, useRerank: false, rewriteQuery: false,
  })

  // Agent sessions
  const [sessions, setSessions] = useState<{ id: string; label: string }[]>([])
  const [activeSession, setActiveSession] = useState<string>('')

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => { loadSources() }, [])
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  async function loadSources() {
    try { setSources(await getSources()) } catch {}
  }

  function toast(msg: string, type: 'ok' | 'err' | 'info' = 'ok') {
    const id = uid()
    setToasts(p => [...p, { id, msg, type }])
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 3200)
  }

  function switchMode(m: Mode) {
    setMode(m)
    setShowOptions(false)
    const defaultModels: Record<Mode, string> = {
      chat: 'llama-3.1-8b-instant',
      rag: 'llama-3.1-8b-instant',
      agent: 'llama-3.3-70b-versatile',
      eval: 'llama-3.1-8b-instant',
    }
    setModel(defaultModels[m])
  }

  async function handleSend() {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    setLoading(true)
    inputRef.current!.style.height = 'auto'

    const userMsg: Message = { id: uid(), role: 'user', content: text, mode, timestamp: new Date() }
    setMessages(p => [...p, userMsg])

    const aiId = uid()
    const aiMsg: Message = { id: aiId, role: 'assistant', content: '', mode, timestamp: new Date(), model, streaming: true }
    setMessages(p => [...p, aiMsg])

    try {
      if (mode === 'chat') {
        await streamChat(text, model, token => {
          setMessages(p => p.map(m => m.id === aiId ? { ...m, content: m.content + token } : m))
        })
        setMessages(p => p.map(m => m.id === aiId ? { ...m, streaming: false } : m))

      } else if (mode === 'rag') {
        const data = await queryRag(text, model, ragOpts)
        setMessages(p => p.map(m => m.id === aiId ? {
          ...m, content: data.answer, streaming: false,
          sources: data.sources, chunksUsed: data.chunks_used,
          rewrittenQuery: data.rewritten_query || undefined,
        } : m))

      } else if (mode === 'agent') {
        const data = await runAgent(text, model, activeSession || undefined)
        setMessages(p => p.map(m => m.id === aiId ? {
          ...m, content: data.answer, streaming: false,
          toolCalls: data.tool_calls_made, iterations: data.iterations,
          sessionId: data.session_id || undefined,
        } : m))
      }
    } catch (e: any) {
      setMessages(p => p.map(m => m.id === aiId ? { ...m, content: '⚠️ ' + e.message, streaming: false } : m))
    }
    setLoading(false)
    inputRef.current?.focus()
  }

  function onKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  function autoResize(el: HTMLTextAreaElement) {
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }

  async function newSession() {
    const data = await createSession()
    const label = 'Session ' + data.session_id.slice(0, 8)
    setSessions(p => [...p, { id: data.session_id, label }])
    setActiveSession(data.session_id)
    toast('New session created', 'ok')
  }

  async function removeSession(id: string) {
    await deleteSession(id)
    setSessions(p => p.filter(s => s.id !== id))
    if (activeSession === id) setActiveSession('')
    toast('Session deleted', 'ok')
  }

  const tabCls = (t: Mode) => {
    const base = 'px-4 py-2 rounded-xl text-sm font-medium transition-all cursor-pointer border'
    const active: Record<Mode, string> = {
      chat: 'bg-violet-600/20 border-violet-600/40 text-violet-300',
      rag: 'bg-cyan-600/20 border-cyan-600/40 text-cyan-300',
      agent: 'bg-orange-600/20 border-orange-600/40 text-orange-300',
      eval: 'bg-green-600/20 border-green-600/40 text-green-300',
    }
    const inactive = 'bg-transparent border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-600'
    return `${base} ${mode === t ? active[t] : inactive}`
  }

  const modeIcon: Record<Mode, string> = { chat: '💬', rag: '🔍', agent: '🤖', eval: '📊' }
  const modeLabel: Record<Mode, string> = { chat: 'Chat', rag: 'RAG', agent: 'Agent', eval: 'Eval' }
  const placeholders: Record<Mode, string> = {
    chat: 'Message Groq...',
    rag: 'Ask about your documents...',
    agent: 'Ask the agent anything...',
    eval: '',
  }

  const emptyMsgs: Record<Mode, { icon: string; title: string; sub: string; pills: string[] }> = {
    chat: { icon: '💬', title: 'How can I help you today?', sub: 'Direct LLM — streaming responses', pills: ['Explain RAG pipelines', 'What is ChromaDB?', 'How does BM25 work?'] },
    rag: { icon: '🔍', title: 'Ask about your documents', sub: 'Retrieval-augmented generation from your knowledge base', pills: ["What are Dharaneesh's skills?", 'Summarize the Scrolla project', 'What tech stack is used?'] },
    agent: { icon: '🤖', title: 'Agent is ready', sub: 'Tools: rag_lookup · web_search · calculator · run_python', pills: ['Search the web for latest AI news', 'What is 2^32?', 'Run some Python code'] },
    eval: { icon: '📊', title: 'Evaluate your RAG pipeline', sub: '', pills: [] },
  }

  return (
    <div className="flex h-screen bg-gray-800 text-gray-100 overflow-hidden">
      <Sidebar sources={sources} mode={mode} onSourcesChange={loadSources} onToast={toast}
        onClearAll={async () => {
          if (!confirm('Delete ALL sources from the knowledge base?')) return
          const r = await clearAllSources()
          toast(`Removed ${r.deleted_sources} sources (${r.deleted_chunks} chunks)`, 'ok')
          loadSources()
        }}
      />

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* Top bar */}
        <div className="flex items-center gap-2 px-4 py-2.5 border-b border-gray-700 bg-gray-850 flex-shrink-0">
          {(['chat', 'rag', 'agent', 'eval'] as Mode[]).map(t => (
            <button key={t} onClick={() => switchMode(t)} className={tabCls(t)}>
              {modeIcon[t]} {modeLabel[t]}
            </button>
          ))}
          <div className="ml-auto flex items-center gap-2">
            <select
              value={model} onChange={e => setModel(e.target.value)}
              className="bg-gray-700 border border-gray-600 rounded-lg text-xs px-2.5 py-1.5 text-gray-200 outline-none focus:border-violet-500 cursor-pointer"
            >
              {MODELS.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
            {mode !== 'eval' && (
              <>
                <button onClick={() => setShowOptions(p => !p)} className={`p-1.5 rounded-lg border transition-colors ${showOptions ? 'border-violet-500 text-violet-400 bg-violet-950/30' : 'border-gray-600 text-gray-400 hover:text-gray-200'}`} title="Options">
                  <Settings2 size={15} />
                </button>
                {mode === 'rag' && (
                  <button onClick={() => setShowDebug(true)} className="p-1.5 rounded-lg border border-gray-600 text-gray-400 hover:text-cyan-400 hover:border-cyan-600 transition-colors" title="Debug retrieval">
                    <Bug size={15} />
                  </button>
                )}
                <button onClick={() => setMessages([])} className="p-1.5 rounded-lg border border-gray-600 text-gray-400 hover:text-gray-200 transition-colors" title="Clear chat">
                  <RotateCcw size={15} />
                </button>
              </>
            )}
          </div>
        </div>

        {/* Options panel */}
        {showOptions && mode === 'rag' && (
          <div className="flex flex-wrap items-center gap-4 px-4 py-2.5 bg-gray-850 border-b border-gray-700 text-xs slide-up">
            {[
              { key: 'useHybrid', label: 'Hybrid Search' },
              { key: 'useRerank', label: 'Re-rank' },
              { key: 'rewriteQuery', label: 'Query Rewrite' },
            ].map(opt => (
              <label key={opt.key} className="flex items-center gap-1.5 text-gray-300 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={ragOpts[opt.key as keyof RagOptions] as boolean}
                  onChange={e => setRagOpts(p => ({ ...p, [opt.key]: e.target.checked }))}
                  className="accent-cyan-500 w-3.5 h-3.5"
                />
                {opt.label}
              </label>
            ))}
            <div className="flex items-center gap-1.5 text-gray-300">
              <span>Top-K</span>
              <input
                type="number" min={1} max={20} value={ragOpts.topK}
                onChange={e => setRagOpts(p => ({ ...p, topK: Number(e.target.value) }))}
                className="w-12 bg-gray-700 border border-gray-600 rounded px-1.5 py-0.5 text-gray-200 outline-none focus:border-cyan-500"
              />
            </div>
          </div>
        )}

        {showOptions && mode === 'agent' && (
          <div className="flex flex-wrap items-center gap-3 px-4 py-2.5 bg-gray-850 border-b border-gray-700 text-xs slide-up">
            <span className="text-gray-400">Session:</span>
            <select
              value={activeSession} onChange={e => setActiveSession(e.target.value)}
              className="bg-gray-700 border border-gray-600 rounded-lg px-2 py-1 text-gray-200 outline-none focus:border-orange-500 text-xs max-w-[180px]"
            >
              <option value="">Stateless (no memory)</option>
              {sessions.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
            </select>
            <button onClick={newSession} className="flex items-center gap-1 px-2 py-1 rounded-lg border border-gray-600 text-gray-300 hover:border-orange-500 hover:text-orange-400 transition-colors">
              <Plus size={11} /> New
            </button>
            {activeSession && (
              <button onClick={() => removeSession(activeSession)} className="flex items-center gap-1 px-2 py-1 rounded-lg border border-red-800 text-red-400 hover:bg-red-950/20 transition-colors">
                <Trash2 size={11} /> Delete
              </button>
            )}
          </div>
        )}

        {/* Eval panel */}
        {mode === 'eval' ? (
          <EvalPanel model={model} onToast={toast} />
        ) : (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center gap-4 p-6">
                  <div className="text-5xl">{emptyMsgs[mode].icon}</div>
                  <div className="text-center">
                    <div className="text-xl font-semibold text-gray-200">{emptyMsgs[mode].title}</div>
                    <div className="text-sm text-gray-400 mt-1">{emptyMsgs[mode].sub}</div>
                  </div>
                  {emptyMsgs[mode].pills.length > 0 && (
                    <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                      {emptyMsgs[mode].pills.map(p => (
                        <button key={p} onClick={() => { setInput(p); inputRef.current?.focus() }}
                          className="text-sm px-3.5 py-1.5 rounded-xl border border-gray-600 text-gray-300 hover:border-gray-500 hover:bg-gray-750 transition-colors">
                          {p}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="max-w-3xl mx-auto px-4 py-6 flex flex-col gap-5">
                  {messages.map(msg => <MessageItem key={msg.id} msg={msg} />)}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* Input */}
            <div className="px-4 pb-4 pt-2 flex-shrink-0">
              <div className="max-w-3xl mx-auto">
                <div className="flex gap-2 items-end bg-gray-700 border border-gray-600 rounded-2xl px-3 py-2 focus-within:border-gray-500 transition-colors">
                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={e => { setInput(e.target.value); autoResize(e.target) }}
                    onKeyDown={onKey}
                    placeholder={placeholders[mode]}
                    rows={1}
                    disabled={loading}
                    className="flex-1 bg-transparent text-sm text-gray-100 placeholder-gray-500 outline-none resize-none py-1 min-h-[28px] max-h-[160px] font-sans leading-relaxed disabled:opacity-50"
                  />
                  <button
                    onClick={handleSend}
                    disabled={!input.trim() || loading}
                    className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition-all
                      ${!input.trim() || loading ? 'bg-gray-600 text-gray-400 cursor-not-allowed' :
                        mode === 'rag' ? 'bg-cyan-600 hover:bg-cyan-500 text-white' :
                        mode === 'agent' ? 'bg-orange-600 hover:bg-orange-500 text-white' :
                        'bg-violet-600 hover:bg-violet-500 text-white'}`}
                  >
                    {loading ? (
                      <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                      </svg>
                    ) : (
                      <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                      </svg>
                    )}
                  </button>
                </div>
                <div className="text-[11px] text-gray-500 text-center mt-1.5">
                  Enter to send · Shift+Enter for new line
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {showDebug && <DebugPanel onClose={() => setShowDebug(false)} />}

      {/* Toasts */}
      <div className="fixed bottom-5 right-5 flex flex-col gap-2 z-50">
        {toasts.map(t => (
          <div key={t.id} className={`slide-up px-4 py-2.5 rounded-xl text-sm shadow-lg border max-w-xs
            ${t.type === 'ok' ? 'bg-green-950 border-green-700 text-green-300' :
              t.type === 'err' ? 'bg-red-950 border-red-700 text-red-300' :
              'bg-violet-950 border-violet-700 text-violet-300'}`}>
            {t.msg}
          </div>
        ))}
      </div>
    </div>
  )
}
