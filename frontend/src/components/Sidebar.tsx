import { useState, useRef } from 'react'
import { Upload, Link2, FileText, Trash2, Database, RefreshCw, CheckCircle, Loader2, X, Plus, MessageSquare, Square, CheckSquare } from 'lucide-react'
import type { Source, Mode, ChatSession } from '../types'
import { ingestFile, ingestUrl, ingestText, deleteSource } from '../api/client'

interface Props {
  sources: Source[]
  mode: Mode
  onSourcesChange: () => void
  onToast: (msg: string, type?: 'ok' | 'err' | 'info') => void
  onClearAll: () => void
  chats: ChatSession[]
  activeChatId: string | null
  onSelectChat: (id: string) => void
  onNewChat: () => void
  onDeleteChat: (id: string) => void
  selectedSources: string[]
  onToggleSource: (source: string) => void
}

type Tab = 'file' | 'url' | 'text'

const modeColors: Record<Mode, { dot: string; label: string; text: string; bg: string; border: string }> = {
  chat:  { dot: 'bg-violet-500', label: '💬 Chat',  text: 'text-violet-400', bg: 'bg-violet-950/20', border: 'border-violet-600/30' },
  rag:   { dot: 'bg-cyan-500',   label: '🔍 RAG',   text: 'text-cyan-400',   bg: 'bg-cyan-950/20',   border: 'border-cyan-600/30'   },
  agent: { dot: 'bg-orange-500', label: '🤖 Agent', text: 'text-orange-400', bg: 'bg-orange-950/20', border: 'border-orange-600/30' },
  eval:  { dot: 'bg-green-500',  label: '📊 Eval',  text: 'text-green-400',  bg: 'bg-green-950/20',  border: 'border-green-600/30'  },
  graph: { dot: 'bg-pink-500',   label: '🕸️ Graph', text: 'text-pink-400',  bg: 'bg-pink-950/20',  border: 'border-pink-600/30'   },
}

const typeIcon: Record<string, string> = { pdf: '📄', docx: '📝', txt: '📃', url: '🌐', text: '✏️' }

export default function Sidebar({
  sources,
  mode,
  onSourcesChange,
  onToast,
  onClearAll,
  chats,
  activeChatId,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  selectedSources,
  onToggleSource,
}: Props) {
  const [sidebarTab, setSidebarTab] = useState<'chats' | 'docs'>('chats')
  const [tab, setTab] = useState<Tab>('file')
  const [urlVal, setUrlVal] = useState('')
  const [textVal, setTextVal] = useState('')
  const [textName, setTextName] = useState('')
  const [dragging, setDragging] = useState(false)
  const [fileLoading, setFileLoading] = useState(false)
  const [urlLoading, setUrlLoading] = useState(false)
  const [textLoading, setTextLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [lastIngested, setLastIngested] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  async function handleFile(file: File) {
    setFileLoading(true)
    setLastIngested(null)
    try {
      const d = await ingestFile(file)
      onToast(`✓ ${d.chunks_stored} chunks stored from ${file.name}`, 'ok')
      setLastIngested(`${file.name} — ${d.chunks_stored} chunks`)
      onSourcesChange()
    } catch (e: any) { onToast(e.message, 'err') }
    setFileLoading(false)
    if (fileRef.current) fileRef.current.value = ''
  }

  async function handleUrl() {
    if (!urlVal.trim()) return
    setUrlLoading(true)
    try {
      const d = await ingestUrl(urlVal.trim())
      onToast(`✓ ${d.chunks_stored} chunks from URL`, 'ok')
      setLastIngested(`${urlVal} — ${d.chunks_stored} chunks`)
      setUrlVal('')
      onSourcesChange()
    } catch (e: any) { onToast(e.message, 'err') }
    setUrlLoading(false)
  }

  async function handleText() {
    if (!textVal.trim()) return
    setTextLoading(true)
    try {
      const name = textName.trim() || 'manual_input'
      const d = await ingestText(textVal.trim(), name)
      onToast(`✓ ${d.chunks_stored} chunks stored`, 'ok')
      setLastIngested(`${name} — ${d.chunks_stored} chunks`)
      setTextVal(''); setTextName('')
      onSourcesChange()
    } catch (e: any) { onToast(e.message, 'err') }
    setTextLoading(false)
  }

  async function handleDelete(source: string) {
    if (!confirm(`Remove "${source.split('/').pop()}" from the knowledge base?`)) return
    try {
      await deleteSource(source)
      onToast('Source removed', 'ok')
      onSourcesChange()
    } catch (e: any) { onToast(e.message, 'err') }
  }

  async function handleRefresh() {
    setRefreshing(true)
    await onSourcesChange()
    setTimeout(() => setRefreshing(false), 600)
  }

  const mc = modeColors[mode]
  const chatModeIcons: Record<Mode, string> = { chat: '💬', rag: '🔍', agent: '🤖', eval: '📊', graph: '🕸️' }

  return (
    <div className="w-64 flex-shrink-0 bg-gray-900 border-r border-gray-700 flex flex-col overflow-hidden">

      {/* Logo + Mode Indicator */}
      <div className="px-4 py-3 border-b border-gray-700 flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-violet-600 rounded-lg flex items-center justify-center text-xs font-bold text-white">G</div>
            <span className="font-semibold text-sm text-gray-100">Groq AI</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className={`w-1.5 h-1.5 rounded-full ${mc.dot}`} />
            <span className={`text-[11px] font-medium ${mc.text}`}>{mc.label}</span>
          </div>
        </div>

        {/* Sidebar Mode Tabs (Chats vs Documents) */}
        <div className="flex gap-1 bg-gray-800 p-0.5 rounded-lg mt-2.5">
          <button
            onClick={() => setSidebarTab('chats')}
            className={`flex-1 text-xs py-1.5 rounded-md font-medium transition-all flex items-center justify-center gap-1.5 cursor-pointer
              ${sidebarTab === 'chats' ? 'bg-gray-700 text-gray-100 shadow-sm border border-gray-700/50' : 'text-gray-400 hover:text-gray-200'}`}
          >
            <MessageSquare size={12} />
            Chats
          </button>
          <button
            onClick={() => setSidebarTab('docs')}
            className={`flex-1 text-xs py-1.5 rounded-md font-medium transition-all flex items-center justify-center gap-1.5 cursor-pointer
              ${sidebarTab === 'docs' ? 'bg-gray-700 text-gray-100 shadow-sm border border-gray-700/50' : 'text-gray-400 hover:text-gray-200'}`}
          >
            <Database size={12} />
            Docs
          </button>
        </div>
      </div>

      {/* Toggled Content */}
      {sidebarTab === 'chats' ? (
        // --- CHATS HISTORY TAB ---
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* New Chat Button */}
          <div className="p-3 flex-shrink-0">
            <button
              onClick={onNewChat}
              className="w-full flex items-center justify-center gap-2 bg-gray-800 hover:bg-gray-750 border border-gray-700 hover:border-gray-600 text-gray-200 rounded-xl py-2.5 text-xs font-medium transition-all cursor-pointer shadow-sm active:scale-[0.98]"
            >
              <Plus size={14} className="text-violet-400" />
              New Chat
            </button>
          </div>

          {/* Recent Chats List */}
          <div className="flex-1 overflow-y-auto px-3 pb-3 flex flex-col gap-1">
            <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest px-1 mb-1 flex-shrink-0">
              Recent Chats
            </div>
            
            {chats.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-center px-4 flex-1 justify-center">
                <MessageSquare size={20} className="text-gray-700" />
                <p className="text-xs text-gray-500">No chat history yet</p>
              </div>
            ) : (
              <div className="flex flex-col gap-1">
                {chats.map(c => {
                  const isActive = activeChatId === c.id
                  const activeColor = modeColors[c.mode]
                  return (
                    <div
                      key={c.id}
                      onClick={() => onSelectChat(c.id)}
                      className={`group flex items-center justify-between px-3 py-2 rounded-xl text-xs cursor-pointer transition-all border
                        ${isActive 
                          ? `${activeColor.bg} ${activeColor.border} text-gray-100 font-medium` 
                          : 'bg-transparent border-transparent text-gray-400 hover:bg-gray-800/40 hover:text-gray-200'}`}
                    >
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        <span className="text-[11px] flex-shrink-0">{chatModeIcons[c.mode] ?? '💬'}</span>
                        <span className="truncate flex-1">{c.title}</span>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onDeleteChat(c.id)
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 rounded-md text-gray-500 hover:text-red-400 hover:bg-red-950/30 transition-all flex-shrink-0 ml-1.5"
                        title="Delete chat"
                      >
                        <X size={11} />
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      ) : (
        // --- DOCUMENTS / INGESTION TAB ---
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Ingest section */}
          <div className="px-3 pt-3 pb-2 border-b border-gray-700 flex-shrink-0">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-widest">Ingest Source</span>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 mb-2 bg-gray-800 p-0.5 rounded-lg">
              {(['file', 'url', 'text'] as Tab[]).map(t => (
                <button key={t} onClick={() => setTab(t)}
                  className={`flex-1 text-[11px] py-1 rounded-md font-medium transition-all capitalize cursor-pointer
                    ${tab === t ? 'bg-gray-700 text-gray-100 shadow-sm border border-gray-700/30' : 'text-gray-500 hover:text-gray-300'}`}>
                  {t === 'file' ? '📎 File' : t === 'url' ? '🌐 URL' : '✏️ Text'}
                </button>
              ))}
            </div>

            {/* File tab */}
            {tab === 'file' && (
              <div>
                <div
                  onClick={() => !fileLoading && fileRef.current?.click()}
                  onDragOver={e => { e.preventDefault(); setDragging(true) }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={e => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) handleFile(f) }}
                  className={`border-2 border-dashed rounded-xl p-4 text-center transition-all cursor-pointer
                    ${fileLoading ? 'border-violet-600 bg-violet-950/30 cursor-not-allowed' :
                      dragging ? 'border-violet-500 bg-violet-950/40 scale-[1.01]' :
                      'border-gray-700 hover:border-violet-600 hover:bg-violet-950/20'}`}
                >
                  <input ref={fileRef} type="file" accept=".pdf,.txt,.docx" className="hidden"
                    onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f) }} />
                  {fileLoading ? (
                    <div className="flex flex-col items-center gap-2">
                      <Loader2 size={20} className="text-violet-400 animate-spin" />
                      <span className="text-xs text-violet-400">Processing...</span>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-1.5">
                      <Upload size={18} className="text-gray-400" />
                      <span className="text-xs text-gray-300 font-medium">Drop file or click</span>
                      <span className="text-[10px] text-gray-500">PDF · DOCX · TXT</span>
                    </div>
                  )}
                </div>
                {lastIngested && tab === 'file' && (
                  <div className="mt-2 flex items-center gap-1.5 px-2 py-1.5 bg-green-950/40 border border-green-800/40 rounded-lg">
                    <CheckCircle size={11} className="text-green-500 flex-shrink-0" />
                    <span className="text-[10px] text-green-400 truncate">{lastIngested}</span>
                  </div>
                )}
              </div>
            )}

            {/* URL tab */}
            {tab === 'url' && (
              <div className="flex flex-col gap-2">
                <input
                  value={urlVal} onChange={e => setUrlVal(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleUrl()}
                  placeholder="https://yourwebsite.com"
                  disabled={urlLoading}
                  className="bg-gray-800 border border-gray-700 rounded-lg text-xs px-3 py-2 text-gray-200 placeholder-gray-500 outline-none focus:border-violet-500 transition-colors disabled:opacity-50"
                />
                <button onClick={handleUrl} disabled={urlLoading || !urlVal.trim()}
                  className="flex items-center justify-center gap-1.5 bg-violet-700 hover:bg-violet-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg py-2 text-xs font-medium transition-colors cursor-pointer">
                  {urlLoading ? <><Loader2 size={12} className="animate-spin" /> Scraping...</> : <><Link2 size={12} /> Ingest URL</>}
                </button>
                <p className="text-[10px] text-gray-500 leading-relaxed">
                  Scrapes the page text and stores it as chunks in the vector DB.
                </p>
              </div>
            )}

            {/* Text tab */}
            {tab === 'text' && (
              <div className="flex flex-col gap-1.5">
                <input
                  value={textName} onChange={e => setTextName(e.target.value)}
                  placeholder="Label (e.g. my-bio, notes)"
                  disabled={textLoading}
                  className="bg-gray-800 border border-gray-700 rounded-lg text-xs px-2.5 py-1.5 text-gray-200 placeholder-gray-500 outline-none focus:border-violet-500 transition-colors"
                />
                <textarea
                  value={textVal} onChange={e => setTextVal(e.target.value)}
                  placeholder="Paste any text here — bio, notes, docs, FAQs..."
                  rows={5}
                  disabled={textLoading}
                  className="bg-gray-800 border border-gray-700 rounded-lg text-xs px-2.5 py-2 text-gray-200 placeholder-gray-500 outline-none focus:border-violet-500 resize-none font-sans transition-colors"
                />
                <button onClick={handleText} disabled={textLoading || !textVal.trim()}
                  className="flex items-center justify-center gap-1.5 bg-violet-700 hover:bg-violet-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg py-2 text-xs font-medium transition-colors cursor-pointer">
                  {textLoading ? <><Loader2 size={12} className="animate-spin" /> Storing...</> : <><FileText size={12} /> Add to Knowledge Base</>}
                </button>
              </div>
            )}
          </div>

          {/* Sources header */}
          <div className="flex items-center justify-between px-3 py-2 flex-shrink-0">
            <div className="flex items-center gap-1.5">
              <Database size={11} className="text-gray-500" />
              <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-widest">Sources</span>
              {sources.length > 0 && (
                <span className="text-[10px] bg-gray-800 text-violet-400 px-1.5 py-0.5 rounded-full border border-gray-700">
                  {sources.length}
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              <button onClick={handleRefresh} className="text-gray-500 hover:text-gray-300 transition-colors cursor-pointer" title="Refresh">
                <RefreshCw size={11} className={refreshing ? 'animate-spin' : ''} />
              </button>
              {sources.length > 0 && (
                <button onClick={onClearAll} className="text-gray-600 hover:text-red-400 transition-colors cursor-pointer" title="Clear all sources">
                  <Trash2 size={11} />
                </button>
              )}
            </div>
          </div>

          {/* Sources list */}
          <div className="flex-1 overflow-y-auto px-3 pb-3">
            {sources.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-6 text-center">
                <Database size={24} className="text-gray-700" />
                <p className="text-xs text-gray-500">No documents indexed yet</p>
              </div>
            ) : (
              <div className="flex flex-col gap-1.5">
                {sources.map(s => {
                  const name = s.source.split('/').pop()?.split('\\').pop() ?? s.source
                  const maxChunks = Math.max(...sources.map(x => x.chunk_count))
                  const barWidth = Math.round((s.chunk_count / maxChunks) * 100)
                  const isSelected = selectedSources.includes(s.source)
                  return (
                    <div key={s.source}
                      className={`group rounded-xl border transition-all overflow-hidden cursor-pointer ${
                        isSelected 
                          ? 'bg-violet-950/10 border-violet-500/40 shadow-sm' 
                          : 'bg-gray-800 border-gray-700 hover:border-gray-600'
                      }`}>
                      <div className="flex items-center gap-2 px-2.5 py-2">
                        <button 
                          onClick={(e) => { e.stopPropagation(); onToggleSource(s.source) }}
                          className={`flex-shrink-0 transition-colors ${isSelected ? 'text-violet-400' : 'text-gray-500 hover:text-gray-400'}`}
                        >
                          {isSelected ? <CheckSquare size={14} /> : <Square size={14} />}
                        </button>
                        <div className="flex-1 min-w-0" onClick={() => onToggleSource(s.source)}>
                          <div className="text-xs text-gray-200 truncate font-medium" title={s.source}>{name}</div>
                          <div className="text-[10px] text-gray-500 mt-0.5">{s.source_type} · {s.chunk_count} chunks</div>
                        </div>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDelete(s.source) }}
                          className="opacity-0 group-hover:opacity-100 p-1 rounded-md text-gray-500 hover:text-red-400 hover:bg-red-950/30 transition-all flex-shrink-0">
                          <X size={11} />
                        </button>
                      </div>
                      {/* Chunk bar */}
                      <div className="h-0.5 bg-gray-700">
                        <div className="h-full bg-violet-600/60 transition-all" style={{ width: `${barWidth}%` }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* RAG tip */}
          {mode === 'rag' && sources.length > 0 && (
            <div className="px-3 pb-3 flex-shrink-0">
              <div className="bg-cyan-950/30 border border-cyan-800/30 rounded-xl px-3 py-2">
                <p className="text-[10px] text-cyan-400 font-medium mb-0.5">💡 Better RAG accuracy</p>
                <p className="text-[10px] text-cyan-600 leading-relaxed">
                  Enable <strong className="text-cyan-500">Hybrid Search</strong> + <strong className="text-cyan-500">Re-rank</strong> in the settings.
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
