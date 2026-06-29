import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Copy, Check, ChevronRight } from 'lucide-react'
import type { Message } from '../types'

interface Props { msg: Message }

export default function MessageItem({ msg }: Props) {
  const [copied, setCopied] = useState(false)
  const [openTools, setOpenTools] = useState<Record<number, boolean>>({})

  function copy() {
    navigator.clipboard.writeText(msg.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  function toggleTool(i: number) {
    setOpenTools(p => ({ ...p, [i]: !p[i] }))
  }

  const time = msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  const toolIcon: Record<string, string> = {
    rag_lookup: '🔍', web_search: '🌐', calculator: '🧮', run_python: '🐍',
  }

  if (msg.role === 'user') {
    return (
      <div className="flex justify-end gap-3 group">
        <div className="max-w-2xl">
          <div className="bg-gray-700 text-gray-100 rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap">
            {msg.content}
          </div>
          <div className="flex items-center justify-end gap-2 mt-1 px-1">
            <span className="text-[10px] text-gray-500">{time}</span>
            <button onClick={copy} className="text-gray-500 hover:text-gray-300 transition-colors opacity-0 group-hover:opacity-100">
              {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
            </button>
          </div>
        </div>
        <div className="w-7 h-7 rounded-full bg-violet-600 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">U</div>
      </div>
    )
  }

  // Assistant message
  const borderColor = msg.mode === 'rag' ? 'border-cyan-900/40' : msg.mode === 'agent' ? 'border-orange-900/40' : 'border-gray-700'

  return (
    <div className="flex gap-3 group">
      <div className={`w-7 h-7 rounded-full flex items-center justify-center text-sm flex-shrink-0 mt-0.5 bg-gray-750 border ${borderColor}`}>
        {msg.mode === 'rag' ? '🔍' : msg.mode === 'agent' ? '🤖' : '✨'}
      </div>

      <div className="flex-1 min-w-0 max-w-3xl">
        {/* Main bubble */}
        <div className={`bg-gray-800 border ${borderColor} rounded-2xl rounded-tl-sm px-4 py-3`}>
          {msg.streaming && !msg.content ? (
            <div className="flex gap-1 py-1">
              <span className="w-2 h-2 bg-gray-400 rounded-full dot-1" />
              <span className="w-2 h-2 bg-gray-400 rounded-full dot-2" />
              <span className="w-2 h-2 bg-gray-400 rounded-full dot-3" />
            </div>
          ) : (
            <div className="prose-ai text-sm text-gray-100">
              <ReactMarkdown>{msg.content}</ReactMarkdown>
              {msg.streaming && <span className="cursor-blink" />}
            </div>
          )}
        </div>

        {/* Rewritten query */}
        {msg.rewrittenQuery && (
          <div className="mt-1.5 px-1 text-xs text-gray-500 italic">
            Rewritten query: "{msg.rewrittenQuery}"
          </div>
        )}

        {/* Tool calls */}
        {msg.toolCalls && msg.toolCalls.length > 0 && (
          <div className="mt-2 flex flex-col gap-1.5">
            {msg.toolCalls.map((tc, i) => (
              <div key={i} className="border border-orange-900/30 rounded-xl overflow-hidden">
                <button
                  onClick={() => toggleTool(i)}
                  className="w-full flex items-center gap-2 px-3 py-2 bg-orange-950/20 hover:bg-orange-950/30 transition-colors text-left"
                >
                  <span className="text-sm">{toolIcon[tc.tool] ?? '🔧'}</span>
                  <span className="text-xs font-semibold text-orange-400">{tc.tool}</span>
                  <span className="text-xs text-gray-500 flex-1 truncate">{JSON.stringify(tc.args)}</span>
                  <ChevronRight size={12} className={`text-gray-500 transition-transform flex-shrink-0 ${openTools[i] ? 'rotate-90' : ''}`} />
                </button>
                {openTools[i] && (
                  <div className="px-3 py-2 bg-gray-900 text-[11px] font-mono text-gray-300 whitespace-pre-wrap break-all max-h-48 overflow-y-auto">
                    {JSON.stringify(tc.result, null, 2)}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Source chips (RAG) */}
        {msg.sources && msg.sources.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5 px-1">
            {msg.sources.map(s => (
              <span key={s} className="text-[11px] px-2 py-0.5 bg-cyan-950/40 border border-cyan-800/30 rounded-full text-cyan-400">
                📄 {s.split('/').pop()?.split('\\').pop() ?? s}
              </span>
            ))}
          </div>
        )}

        {/* Footer meta */}
        <div className="flex items-center gap-3 mt-1.5 px-1">
          <span className="text-[10px] text-gray-500">{time}</span>
          {msg.model && <span className="text-[10px] text-gray-500">{msg.model}</span>}
          {msg.chunksUsed !== undefined && <span className="text-[10px] text-cyan-600">{msg.chunksUsed} chunks</span>}
          {msg.iterations !== undefined && <span className="text-[10px] text-orange-600">{msg.iterations} iter</span>}
          {msg.sessionId && <span className="text-[10px] text-gray-600">session:{msg.sessionId.slice(0, 6)}</span>}
          <button onClick={copy} className="text-gray-500 hover:text-gray-300 transition-colors opacity-0 group-hover:opacity-100 ml-auto">
            {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
          </button>
        </div>
      </div>
    </div>
  )
}
