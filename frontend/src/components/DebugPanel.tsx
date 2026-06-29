import { useState } from 'react'
import { Bug, ChevronDown, ChevronRight, X, Loader2, AlertCircle, CheckCircle2, Info } from 'lucide-react'
import { debugRag } from '../api/client'

interface Chunk {
  rank: number
  score: number
  rerank_score?: number
  source: string
  source_type: string
  text_preview: string
  text_length: number
}

interface DebugResult {
  query: string
  total_chunks_in_db: number
  retrieved: number
  settings: { top_k: number; score_threshold: number; use_hybrid: boolean; use_rerank: boolean }
  chunks: Chunk[]
}

interface Props {
  onClose: () => void
}

export default function DebugPanel({ onClose }: Props) {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(8)
  const [useHybrid, setUseHybrid] = useState(true)
  const [useRerank, setUseRerank] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<DebugResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})

  async function run() {
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const r = await debugRag(query.trim(), topK, useHybrid, useRerank)
      setResult(r)
      setExpanded({})
    } catch (e: any) {
      setError(e.message || 'Unknown error — check that the backend is running.')
    }
    setLoading(false)
  }

  // Normalize bar width relative to top score so bars always look meaningful
  function barWidth(score: number, maxScore: number): number {
    if (maxScore <= 0) return 0
    return Math.max(4, Math.round((score / maxScore) * 100))
  }

  // Rank-based colours (top 1/3 = green, middle = yellow, rest = red)
  function rankColor(rank: number, total: number): string {
    const pct = rank / total
    if (pct <= 0.33) return 'text-green-400 bg-green-950/40 border-green-800/40'
    if (pct <= 0.66) return 'text-yellow-400 bg-yellow-950/40 border-yellow-800/40'
    return 'text-red-400 bg-red-950/40 border-red-800/40'
  }

  function rankBar(rank: number, total: number): string {
    const pct = rank / total
    if (pct <= 0.33) return 'bg-green-500'
    if (pct <= 0.66) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const maxScore = result && result.chunks.length > 0
    ? Math.max(...result.chunks.map(c => c.score), 0.000001)
    : 1
  const isHybrid = result?.settings.use_hybrid ?? useHybrid

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-2xl max-h-[88vh] flex flex-col shadow-2xl mx-4">

        {/* Header */}
        <div className="flex items-center gap-2 px-5 py-4 border-b border-gray-700 flex-shrink-0">
          <Bug size={16} className="text-cyan-400" />
          <h2 className="font-semibold text-gray-100 text-sm">RAG Retrieval Debugger</h2>
          <button onClick={onClose} className="ml-auto text-gray-400 hover:text-gray-200 transition-colors">
            <X size={16} />
          </button>
        </div>

        {/* Controls */}
        <div className="px-5 py-4 border-b border-gray-700 flex flex-col gap-3 flex-shrink-0">
          <div className="flex gap-2">
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && run()}
              placeholder="Enter a query to test retrieval..."
              className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-gray-200 placeholder-gray-500 outline-none focus:border-cyan-500 transition-colors"
            />
            <button
              onClick={run}
              disabled={loading || !query.trim()}
              className="bg-cyan-700 hover:bg-cyan-600 disabled:opacity-40 text-white rounded-xl px-4 text-sm font-medium transition-colors flex items-center gap-1.5 flex-shrink-0"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Bug size={14} />}
              Test
            </button>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <label className="flex items-center gap-1.5 text-gray-300 cursor-pointer select-none">
              <input type="checkbox" checked={useHybrid} onChange={e => setUseHybrid(e.target.checked)} className="accent-cyan-500" />
              Hybrid Search
            </label>
            <label className="flex items-center gap-1.5 text-gray-300 cursor-pointer select-none">
              <input type="checkbox" checked={useRerank} onChange={e => setUseRerank(e.target.checked)} className="accent-cyan-500" />
              Re-rank
            </label>
            <label className="flex items-center gap-1.5 text-gray-300 select-none">
              Top-K:
              <input
                type="number" value={topK} onChange={e => setTopK(Number(e.target.value))} min={1} max={20}
                className="w-12 bg-gray-800 border border-gray-700 rounded px-1.5 py-0.5 text-gray-200 outline-none focus:border-cyan-500"
              />
            </label>
          </div>
        </div>

        {/* Results */}
        <div className="flex-1 overflow-y-auto px-5 py-4">

          {/* Inline error */}
          {error && (
            <div className="flex items-start gap-2 bg-red-950/30 border border-red-800/40 rounded-xl p-3 mb-4">
              <AlertCircle size={15} className="text-red-400 flex-shrink-0 mt-0.5" />
              <div className="text-xs text-red-300">
                <strong>Error:</strong> {error}
              </div>
            </div>
          )}

          {!result && !error && (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <Bug size={32} className="text-gray-700" />
              <p className="text-sm text-gray-400">Enter a query to see what chunks get retrieved</p>
              <p className="text-xs text-gray-600">Shows raw retrieval results before the LLM generates an answer</p>
            </div>
          )}

          {result && (
            <div className="flex flex-col gap-4">

              {/* Stats */}
              <div className="grid grid-cols-3 gap-2">
                {[
                  { label: 'Total in DB', value: result.total_chunks_in_db, color: 'text-gray-300' },
                  { label: 'Retrieved', value: result.retrieved, color: result.retrieved === 0 ? 'text-red-400' : 'text-cyan-400' },
                  { label: 'Top-K set', value: result.settings.top_k, color: 'text-gray-300' },
                ].map(s => (
                  <div key={s.label} className="bg-gray-800 rounded-xl p-3 text-center border border-gray-700">
                    <div className={`text-xl font-bold ${s.color}`}>{s.value}</div>
                    <div className="text-[10px] text-gray-500 mt-0.5">{s.label}</div>
                  </div>
                ))}
              </div>

              {/* Score scale note for hybrid */}
              {isHybrid && result.retrieved > 0 && (
                <div className="flex items-start gap-2 bg-blue-950/30 border border-blue-800/40 rounded-xl p-2.5">
                  <Info size={13} className="text-blue-400 flex-shrink-0 mt-0.5" />
                  <p className="text-[11px] text-blue-300">
                    <strong>Hybrid mode — RRF scores:</strong> max ~0.016 (not 0–1). Bars show <em>relative</em> rank, not absolute relevance.
                  </p>
                </div>
              )}

              {/* Zero results */}
              {result.retrieved === 0 && (
                <div className="flex items-start gap-2 bg-red-950/30 border border-red-800/40 rounded-xl p-3">
                  <AlertCircle size={15} className="text-red-400 flex-shrink-0 mt-0.5" />
                  <div className="text-xs text-red-300">
                    <strong>No chunks retrieved.</strong> The query didn't match anything in your knowledge base.
                    <ul className="mt-1.5 text-red-400 space-y-0.5">
                      <li>• Make sure you've ingested documents first</li>
                      <li>• Try exact words from the uploaded document</li>
                      <li>• Check that ingestion returned chunks &gt; 0</li>
                    </ul>
                  </div>
                </div>
              )}

              {result.retrieved > 0 && (
                <div className="flex items-center gap-2 bg-green-950/30 border border-green-800/40 rounded-xl p-2.5">
                  <CheckCircle2 size={14} className="text-green-400" />
                  <p className="text-xs text-green-300">
                    Retrieved {result.retrieved} chunks · top score{' '}
                    <span className="font-mono">{result.chunks[0].score.toFixed(isHybrid ? 5 : 3)}</span>
                    <span className="text-green-600 ml-1">{isHybrid ? '(RRF)' : '(cosine)'}</span>
                  </p>
                </div>
              )}

              {/* Chunks */}
              {result.chunks.length > 0 && (
                <div className="flex flex-col gap-2">
                  {result.chunks.map((c, i) => (
                    <div key={i} className="border border-gray-700 rounded-xl overflow-hidden">
                      <button
                        onClick={() => setExpanded(p => ({ ...p, [i]: !p[i] }))}
                        className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-gray-800/50 transition-colors text-left"
                      >
                        <span className="text-xs font-bold text-gray-500 w-5 flex-shrink-0">#{c.rank}</span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-300 truncate">
                              {c.source.split('/').pop()?.split('\\').pop() ?? c.source}
                            </span>
                            <span className="text-[10px] text-gray-600 flex-shrink-0">{c.text_length} chars</span>
                          </div>
                          {/* Relative score bar */}
                          <div className="flex items-center gap-2 mt-1">
                            <div className="flex-1 h-1 bg-gray-700 rounded-full overflow-hidden">
                              <div
                                className={`h-full ${rankBar(i, result.retrieved)} rounded-full transition-all`}
                                style={{ width: `${barWidth(c.score, maxScore)}%` }}
                              />
                            </div>
                            <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${rankColor(i, result.retrieved)}`}>
                              {isHybrid ? c.score.toFixed(5) : c.score.toFixed(3)}
                            </span>
                            {c.rerank_score !== undefined && (
                              <span className="text-[10px] text-purple-400 font-mono flex-shrink-0">
                                rr:{c.rerank_score.toFixed(2)}
                              </span>
                            )}
                          </div>
                        </div>
                        {expanded[i]
                          ? <ChevronDown size={13} className="text-gray-500 flex-shrink-0" />
                          : <ChevronRight size={13} className="text-gray-500 flex-shrink-0" />}
                      </button>
                      {expanded[i] && (
                        <div className="px-3 pb-3 pt-1 border-t border-gray-700/50">
                          <div className="text-[10px] text-gray-500 mb-1.5 flex items-center gap-2 uppercase tracking-wide">
                            <span>{c.source_type}</span>
                            <span>·</span>
                            <span className="normal-case text-gray-600 truncate">{c.source}</span>
                          </div>
                          <p className="text-[11px] text-gray-300 font-mono leading-relaxed whitespace-pre-wrap">{c.text_preview}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
