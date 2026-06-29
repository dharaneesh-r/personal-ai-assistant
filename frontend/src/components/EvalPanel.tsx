import { useState } from 'react'
import { runEval } from '../api/client'
import type { EvalResult } from '../types'

interface Props {
  model: string
  onToast: (msg: string, type?: 'ok' | 'err' | 'info') => void
}

export default function EvalPanel({ model, onToast }: Props) {
  const [q, setQ] = useState('')
  const [a, setA] = useState('')
  const [c, setC] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<EvalResult | null>(null)

  async function run() {
    if (!q.trim() || !a.trim() || !c.trim()) { onToast('Fill all three fields', 'err'); return }
    setLoading(true)
    try {
      const r = await runEval(q, a, c, model)
      setResult(r)
    } catch (e: any) { onToast(e.message, 'err') }
    setLoading(false)
  }

  function scoreColor(s: number) {
    if (s >= 4) return { bar: 'bg-green-500', text: 'text-green-400' }
    if (s >= 3) return { bar: 'bg-yellow-500', text: 'text-yellow-400' }
    return { bar: 'bg-red-500', text: 'text-red-400' }
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto flex flex-col gap-5">

        {/* Header */}
        <div>
          <h2 className="text-lg font-semibold text-gray-100">LLM-as-Judge Evaluation</h2>
          <p className="text-sm text-gray-400 mt-1">Score an answer for faithfulness, relevance, and groundedness.</p>
        </div>

        {/* Form */}
        <div className="bg-gray-850 border border-gray-700 rounded-2xl p-5 flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-gray-300 uppercase tracking-wide">Question</label>
            <input
              value={q} onChange={e => setQ(e.target.value)}
              placeholder="e.g. Where does Dharaneesh work?"
              className="bg-gray-900 border border-gray-700 rounded-xl px-3 py-2.5 text-sm text-gray-200 placeholder-gray-500 outline-none focus:border-green-500 transition-colors"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-gray-300 uppercase tracking-wide">Answer to evaluate</label>
            <textarea
              value={a} onChange={e => setA(e.target.value)}
              placeholder="The answer you want to score..."
              rows={3}
              className="bg-gray-900 border border-gray-700 rounded-xl px-3 py-2.5 text-sm text-gray-200 placeholder-gray-500 outline-none focus:border-green-500 transition-colors resize-none font-sans"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-gray-300 uppercase tracking-wide">Context (ground truth)</label>
            <textarea
              value={c} onChange={e => setC(e.target.value)}
              placeholder="The context the answer should be grounded in..."
              rows={4}
              className="bg-gray-900 border border-gray-700 rounded-xl px-3 py-2.5 text-sm text-gray-200 placeholder-gray-500 outline-none focus:border-green-500 transition-colors resize-none font-sans"
            />
          </div>
          <button
            onClick={run} disabled={loading}
            className="bg-green-600 hover:bg-green-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold rounded-xl py-2.5 text-sm transition-colors"
          >
            {loading ? 'Evaluating...' : 'Run Evaluation'}
          </button>
        </div>

        {/* Results */}
        {result && (
          <div className="bg-gray-850 border border-gray-700 rounded-2xl p-5 slide-up">
            <h3 className="text-sm font-semibold text-gray-200 mb-4">Results</h3>

            {/* Overall */}
            <div className="flex items-center justify-between bg-gray-900 rounded-xl px-4 py-3 mb-4">
              <span className="text-sm text-gray-300 font-medium">Overall Score</span>
              <span className={`text-2xl font-bold ${scoreColor(result.overall).text}`}>
                {result.overall.toFixed(1)} <span className="text-sm text-gray-500">/ 5</span>
              </span>
            </div>

            {/* Per-metric */}
            {([
              { key: 'faithfulness', label: 'Faithfulness', desc: 'Sticks to context?' },
              { key: 'relevance', label: 'Relevance', desc: 'Answers the question?' },
              { key: 'groundedness', label: 'Groundedness', desc: 'Claims traceable to context?' },
            ] as const).map(m => {
              const data = result[m.key]
              const { bar, text } = scoreColor(data.score)
              return (
                <div key={m.key} className="mb-3">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-xs text-gray-400 w-28 flex-shrink-0">{m.label}</span>
                    <div className="flex-1 bg-gray-700 rounded-full h-2 overflow-hidden">
                      <div className={`${bar} h-full rounded-full transition-all duration-700`} style={{ width: `${(data.score / 5) * 100}%` }} />
                    </div>
                    <span className={`text-xs font-bold w-8 text-right ${text}`}>{data.score}/5</span>
                  </div>
                  <p className="text-[11px] text-gray-500 pl-28">{data.reason}</p>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
