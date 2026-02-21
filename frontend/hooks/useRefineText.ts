'use client'

import { useCallback, useRef, useState } from 'react'
import { refineText } from '@/lib/api/brds'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  sourcesUsed?: string[]
}

interface UseRefineTextOptions {
  projectId: string
  brdId: string
}

export interface UseRefineTextReturn {
  messages: ChatMessage[]
  isLoading: boolean
  latestRefinedText: string | null
  sendPrompt: (instruction: string) => Promise<void>
  initSession: (selectedText: string, sectionKey: string, mode: 'refine' | 'generate') => void
  reset: () => void
}

/**
 * Manages multi-turn chat state for inline BRD text refinement.
 *
 * Each turn sends the latest refined text (or original selection) as
 * `selected_text` and the user's new instruction. This builds a
 * conversational feel without requiring server-side session state.
 */
export function useRefineText({
  projectId,
  brdId,
}: UseRefineTextOptions): UseRefineTextReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [latestRefinedText, setLatestRefinedText] = useState<string | null>(null)

  // Keep the original selected text and section key stable across turns
  const originalTextRef = useRef('')
  const sectionKeyRef = useRef('')
  const modeRef = useRef<'refine' | 'generate'>('refine')

  const initSession = useCallback(
    (selectedText: string, sectionKey: string, mode: 'refine' | 'generate') => {
      originalTextRef.current = selectedText
      sectionKeyRef.current = sectionKey
      modeRef.current = mode
      setMessages([])
      setLatestRefinedText(null)
    },
    []
  )

  const sendPrompt = useCallback(
    async (instruction: string) => {
      const userMsg: ChatMessage = {
        role: 'user',
        content: instruction,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, userMsg])
      setIsLoading(true)

      try {
        // On subsequent turns, send the latest refined text so the AI
        // can iterate on its own output rather than the original
        const textToRefine = latestRefinedText ?? originalTextRef.current

        const result = await refineText(projectId, brdId, {
          selected_text: textToRefine,
          instruction,
          section_context: sectionKeyRef.current,
          mode: modeRef.current === 'generate' ? 'agentic' : 'simple',
        })

        setLatestRefinedText(result.refined)

        const assistantMsg: ChatMessage = {
          role: 'assistant',
          content: result.refined,
          timestamp: new Date(),
          sourcesUsed: result.sources_used,
        }
        setMessages((prev) => [...prev, assistantMsg])
      } catch (err: any) {
        const errorMsg: ChatMessage = {
          role: 'assistant',
          content: `Error: ${err.response?.data?.detail || err.message || 'Something went wrong'}`,
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, errorMsg])
      } finally {
        setIsLoading(false)
      }
    },
    [projectId, brdId, latestRefinedText]
  )

  const reset = useCallback(() => {
    setMessages([])
    setLatestRefinedText(null)
    originalTextRef.current = ''
    sectionKeyRef.current = ''
  }, [])

  return {
    messages,
    isLoading,
    latestRefinedText,
    sendPrompt,
    initSession,
    reset,
  }
}
