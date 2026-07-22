import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Copy, Check, ChevronRight } from 'lucide-react'
import type { Message } from '../types'
import mermaid from 'mermaid'

// Initialize Mermaid with theme variables matching the theme
mermaid.initialize({
  startOnLoad: true,
  theme: 'dark',
  securityLevel: 'loose',
  themeVariables: {
    background: '#18181b',
    primaryColor: '#7c3aed',
    primaryTextColor: '#ececec',
    lineColor: '#52525b',
  }
})

function sanitizeMermaidCode(raw: string): string {
  let cleaned = raw.trim();

  // Split inline collapsed connections onto newlines (e.g. A --> B C --> D)
  cleaned = cleaned.replace(/\s+(\w+)\s*(-->|-.->|==>|->|->>)/g, '\n$1 $2');
  
  // Remove markdown fences
  cleaned = cleaned.replace(/^```mermaid\s*/i, '');
  cleaned = cleaned.replace(/^```\s*/i, '');
  cleaned = cleaned.replace(/```$/, '');
  
  // Replace # comments with %% comments
  cleaned = cleaned.split('\n').map(line => {
    const trimmed = line.trim();
    if (trimmed.startsWith('#') && !trimmed.startsWith('#rgba') && !trimmed.startsWith('#hex')) {
      return '%%' + line.slice(1);
    }
    return line;
  }).join('\n');

  // Fix common LLM mistakes: unclosed or missing opening quotes in multiline labels
  cleaned = cleaned.replace(/\[\s*"([^"\]]*)]/g, '["$1"]');
  cleaned = cleaned.replace(/\[([^"\]]*)"\s*]/g, '["$1"]');
  cleaned = cleaned.replace(/\(\s*"([^")]*)\)/g, '("$1")');
  cleaned = cleaned.replace(/\([^")]*"\s*\)/g, '("$1")');
  cleaned = cleaned.replace(/\{\s*"([^"}]*)}/g, '{"$1"}');
  cleaned = cleaned.replace(/\{([^"}]*)"\s*}/g, '{"$1"}');

  // Temporarily extract all double-quoted strings to prevent regex corruption inside labels
  const quotes: string[] = [];
  cleaned = cleaned.replace(/"([^"\\]*(?:\\.[^"\\]*)*)"/g, (match) => {
    quotes.push(match.replace(/\r?\n/g, ' <br/> '));
    return `__QUOTE_${quotes.length - 1}__`;
  });

  // Wrap all unquoted node labels (brackets, parentheses, braces) in double quotes to prevent syntax errors
  cleaned = cleaned.replace(/(\w+)\s*\[([^"\]]+)\]/g, (match, id, text) => {
    if (text.includes('__QUOTE_')) return match;
    return `${id}["${text.trim().replace(/"/g, "'").replace(/\r?\n/g, ' <br/> ')}"]`;
  });
  cleaned = cleaned.replace(/(\w+)\s*\(([^")]+)\)/g, (match, id, text) => {
    if (text.includes('__QUOTE_')) return match;
    return `${id}("${text.trim().replace(/"/g, "'").replace(/\r?\n/g, ' <br/> ')}")`;
  });
  cleaned = cleaned.replace(/(\w+)\s*\{([^"}]+)\}/g, (match, id, text) => {
    if (text.includes('__QUOTE_')) return match;
    return `${id}{"${text.trim().replace(/"/g, "'").replace(/\r?\n/g, ' <br/> ')}"}`;
  });

  // Restore the double-quoted strings
  cleaned = cleaned.replace(/__QUOTE_(\d+)__/g, (match, id) => {
    return quotes[parseInt(id, 10)];
  });

  // Fix arrow symbols: replace '->>' and '->' with '-->' safely
  cleaned = cleaned.split('\n').map(line => {
    // If it's a flowchart or graph diagram, clean up arrows
    const trimmed = line.trim().toLowerCase();
    if (!trimmed.startsWith('sequencediagram')) {
      line = line.replace(/->>/g, '-->');
      line = line.replace(/(?<!-)->(?!>)/g, '-->');
      line = line.replace(/\|([^|]+)\|\s*(?:>-|->|-->|>)\s*/g, '|$1| ');
      line = line.replace(/>-/g, '-->');
    }
    return line;
  }).filter(line => {
    const trimmed = line.trim();
    if (trimmed === '') return false;
    const match = /^([A-Za-z]+)(?:,\s*|\s+)([A-Za-z]+)/.exec(trimmed);
    if (match) {
      const firstWord = match[1].toLowerCase();
      const validKeywords = [
        'subgraph', 'end', 'classdef', 'class', 'click', 'style', 'linkstyle', 'note', 'direction', 
        'graph', 'flowchart', 'pie', 'gantt', 'sequencediagram', 'classdiagram', 'statediagram', 
        'erdiagram', 'gitgraph', 'mindmap', 'timeline', 'c4diagram', 'participant', 'actor', 'state', 'title'
      ];
      if (!validKeywords.includes(firstWord)) {
        return false;
      }
    }
    return true;
  }).join('\n');

  // Ensure diagram starts with valid Mermaid type declaration
  const lower = cleaned.toLowerCase();
  const validStarts = [
    'graph', 'flowchart', 'sequencediagram', 'classdiagram', 
    'statediagram', 'erdiagram', 'gantt', 'pie', 'gitgraph', 
    'mindmap', 'timeline', 'c4diagram'
  ];
  const hasValidStart = validStarts.some(start => lower.startsWith(start));
  if (!hasValidStart) {
    cleaned = 'graph TD\n' + cleaned;
  }
  
  return cleaned.trim();
}

function wrapRawMermaidCharts(text: string): string {
  if (!text) return '';
  const validStarts = ['graph', 'flowchart', 'sequencediagram', 'classdiagram', 'statediagram', 'erdiagram', 'gantt', 'pie', 'gitgraph', 'mindmap', 'timeline', 'c4diagram'];
  const lines = text.split('\n');
  let inMermaidBlock = false;
  let inFence = false;
  let mermaidLines: string[] = [];
  const processedLines: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();
    const lower = trimmed.toLowerCase();

    if (trimmed.startsWith('```')) {
      if (inMermaidBlock) {
        processedLines.push('```mermaid\n' + mermaidLines.join('\n') + '\n```');
        mermaidLines = [];
        inMermaidBlock = false;
      }
      inFence = !inFence;
      processedLines.push(line);
      continue;
    }

    if (inFence) {
      processedLines.push(line);
      continue;
    }

    const startsWithKeyword = validStarts.some(start => lower.startsWith(start));
    
    if (!inMermaidBlock && startsWithKeyword && (lower.includes('tb') || lower.includes('td') || lower.includes('lr') || lower.includes('rl') || lower.includes('-->') || lower.includes('->') || lower.includes('==>'))) {
      inMermaidBlock = true;
      mermaidLines.push(line);
    } else if (inMermaidBlock) {
      // If it looks like a regular sentence (capital letter followed by lowercase, no mermaid-specific characters like [, (, {, >) then end block.
      if (trimmed !== '' && /^[A-Z][a-z]/.test(trimmed) && !trimmed.includes('-->') && !trimmed.includes('->') && !trimmed.includes('[') && !trimmed.includes('(')) {
        processedLines.push('```mermaid\n' + mermaidLines.join('\n') + '\n```');
        mermaidLines = [];
        inMermaidBlock = false;
        processedLines.push(line);
      } else {
        mermaidLines.push(line);
      }
    } else {
      processedLines.push(line);
    }
  }

  if (inMermaidBlock && mermaidLines.length > 0) {
    processedLines.push('```mermaid\n' + mermaidLines.join('\n') + '\n```');
  }

  return processedLines.join('\n');
}

function MermaidRenderer({ code }: { code: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [svg, setSvg] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const renderChart = async () => {
      try {
        const id = 'mermaid-' + Math.random().toString(36).slice(2, 9)
        // Clean up previous runs
        if (containerRef.current) {
          containerRef.current.innerHTML = ''
        }
        // Render SVG dynamically
        const sanitized = sanitizeMermaidCode(code)
        const { svg: renderedSvg } = await mermaid.render(id, sanitized)
        if (active) {
          setSvg(renderedSvg)
          setError(null)
        }
      } catch (err: any) {
        console.error("Mermaid Render Error:", err)
        // Extract syntax errors if available
        if (active) {
          setError(err.message || 'Failed to parse Mermaid diagram')
        }
      }
    }

    renderChart()
    return () => {
      active = false
    }
  }, [code])

  if (error) {
    return (
      <div className="bg-red-950/20 border border-red-900/30 rounded-xl p-3.5 my-2 text-xs text-red-400 font-mono overflow-x-auto">
        <div className="font-semibold mb-1 flex items-center gap-1.5">⚠️ Mermaid Render Error</div>
        <pre className="text-[10px] text-red-300 whitespace-pre-wrap">{code}</pre>
      </div>
    )
  }

  return (
    <div className="bg-gray-900/60 p-4 border border-gray-700 rounded-xl my-2 flex justify-center overflow-x-auto shadow-inner">
      <div ref={containerRef} className="hidden" />
      {svg ? (
        <div className="w-full flex justify-center" dangerouslySetInnerHTML={{ __html: svg }} />
      ) : (
        <div className="text-xs text-gray-500 animate-pulse py-2">Rendering diagram...</div>
      )}
    </div>
  )
}


function AgentResearchLoader() {
  const steps = [
    { text: 'Initializing autonomous research agent...', icon: '🤖' },
    { text: 'Searching internet for product reviews & specifications...', icon: '🌐' },
    { text: 'Crawling branded product catalogs & e-commerce pages...', icon: '📄' },
    { text: 'Extracting key specs, prices, and features...', icon: '✂️' },
    { text: 'Ingesting data chunks into ChromaDB vector index...', icon: '📥' },
    { text: 'Retrieving context & ranking candidates using cross-encoder...', icon: '🧠' },
    { text: 'Formulating final recommendation report...', icon: '✨' },
  ]
  const [currentStep, setCurrentStep] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentStep(s => (s < steps.length - 1 ? s + 1 : s))
    }, 4500)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="flex flex-col gap-3 py-1 text-xs">
      <div className="flex items-center gap-2">
        <svg className="animate-spin w-4 h-4 text-orange-400" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
        </svg>
        <span className="text-gray-300 font-medium animate-pulse">Agent is thinking...</span>
      </div>
      <div className="flex flex-col gap-2 pl-4 border-l border-gray-700 ml-2">
        {steps.map((s, idx) => {
          if (idx > currentStep) return null
          const isCurrent = idx === currentStep
          return (
            <div key={idx} className={`flex items-center gap-2 transition-all duration-500 ${isCurrent ? 'text-orange-400 font-semibold translate-x-1' : 'text-gray-500'}`}>
              <span>{s.icon}</span>
              <span>{s.text}</span>
              {isCurrent && <span className="w-1.5 h-1.5 bg-orange-400 rounded-full animate-ping ml-1" />}
            </div>
          )
        })}
      </div>
    </div>
  )
}

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
            msg.mode === 'agent' ? (
              <AgentResearchLoader />
            ) : (
              <div className="flex gap-1 py-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full dot-1" />
                <span className="w-2 h-2 bg-gray-400 rounded-full dot-2" />
                <span className="w-2 h-2 bg-gray-400 rounded-full dot-3" />
              </div>
            )
          ) : (
            <div className="prose-ai text-sm text-gray-100">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ node, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '')
                    const lang = match ? match[1] : ''
                    const codeVal = String(children).replace(/\n$/, '')
                    if (lang === 'mermaid') {
                      return <MermaidRenderer code={codeVal} />
                    }
                    return <code className={className} {...props}>{children}</code>
                  }
                }}
              >
                {wrapRawMermaidCharts(msg.content)}
              </ReactMarkdown>
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
