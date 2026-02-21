'use client'

import { useCallback, useRef, useState } from 'react'
import { refineText } from '@/lib/api/brds'

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
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
  hasActiveRefinement: boolean
  sendPrompt: (instruction: string) => Promise<void>
  sendChat: (message: string, sectionKey: string) => Promise<void>
  initSession: (selectedText: string, sectionKey: string, mode: 'refine' | 'generate') => void
  addSystemMessage: (content: string) => void
  clearRefinement: () => void
  reset: () => void
}

/**
 * Manages persistent chat state for BRD refinement and general queries.
 *
 * Supports two interaction modes:
 * 1. Refine: user selects text → initSession → sendPrompt iterates on it
 * 2. Chat: user types a question → sendChat queries the BRD via agentic mode
 *
 * Messages persist across sidebar open/close. Only reset() clears history.
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

  const hasActiveRefinement = originalTextRef.current !== ''

  const addSystemMessage = useCallback((content: string) => {
    setMessages((prev) => [...prev, { role: 'system', content, timestamp: new Date() }])
  }, [])

  // Start a refine session — keeps existing messages, updates context
  const initSession = useCallback(
    (selectedText: string, sectionKey: string, mode: 'refine' | 'generate') => {
      originalTextRef.current = selectedText
      sectionKeyRef.current = sectionKey
      modeRef.current = mode
      setLatestRefinedText(null)

      // Add a separator so the user sees the context switch
      const label = selectedText
        ? `Refining selected text in ${sectionKey.replace(/_/g, ' ')}`
        : `Generating content for ${sectionKey.replace(/_/g, ' ')}`
      setMessages((prev) => [...prev, { role: 'system', content: label, timestamp: new Date() }])
    },
    []
  )

  // Send a refinement prompt (for active refine sessions)
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

  // Send a general chat message (no text selection, uses agentic mode)
  const sendChat = useCallback(
    async (message: string, sectionKey: string) => {
      // Clear any active refinement context so Accept bar doesn't show
      originalTextRef.current = ''
      sectionKeyRef.current = sectionKey
      setLatestRefinedText(null)

      const userMsg: ChatMessage = {
        role: 'user',
        content: message,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, userMsg])
      setIsLoading(true)

      try {
        const result = await refineText(projectId, brdId, {
          selected_text: '',
          instruction: message,
          section_context: sectionKey,
          mode: 'agentic',
        })

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
    [projectId, brdId]
  )

  // Clear refinement tracking without wiping messages (used after Accept)
  const clearRefinement = useCallback(() => {
    setLatestRefinedText(null)
    originalTextRef.current = ''
  }, [])

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
    hasActiveRefinement,
    sendPrompt,
    sendChat,
    initSession,
    addSystemMessage,
    clearRefinement,
    reset,
  }
}
