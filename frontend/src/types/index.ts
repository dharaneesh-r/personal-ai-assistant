export type Mode = 'chat' | 'rag' | 'agent' | 'eval'

export interface ToolCall {
  tool: string
  args: Record<string, unknown>
  result: Record<string, unknown>
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  mode: Mode
  timestamp: Date
  // RAG extras
  sources?: string[]
  chunksUsed?: number
  rewrittenQuery?: string
  // Agent extras
  toolCalls?: ToolCall[]
  iterations?: number
  sessionId?: string
  // meta
  model?: string
  streaming?: boolean
}

export interface Source {
  source: string
  source_type: string
  chunk_count: number
}

export interface RagOptions {
  topK: number
  scoreThreshold: number
  useHybrid: boolean
  useRerank: boolean
  rewriteQuery: boolean
}

export interface EvalResult {
  overall: number
  faithfulness: { score: number; reason: string }
  relevance: { score: number; reason: string }
  groundedness: { score: number; reason: string }
}

export interface SessionInfo {
  session_id: string
  turns: number
}
