'use client'

import { useCallback, useRef, useState } from 'react'
import { chatMessage, ResponseType } from '@/lib/api/brds'
import { getApiError } from '@/lib/utils/formatters'

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
  latestResponseType: ResponseType | null
  hasActiveRefinement: boolean
  sendMessage: (message: string, sectionKey: string) => Promise<void>
  initSession: (selectedText: string, sectionKey: string, mode: 'refine' | 'generate') => void
  addSystemMessage: (content: string) => void
  clearRefinement: () => void
  reset: () => void
}

/**
 * Manages persistent chat state for unified BRD interaction.
 *
 * All messages go through the single /chat endpoint. The backend AI
 * classifies responses as refinement/answer/generation via the
 * submit_response virtual tool. Frontend uses response_type to
 * decide UI behavior (Accept bar visibility).
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
  const [latestResponseType, setLatestResponseType] = useState<ResponseType | null>(null)

  // Keep the original selected text stable across turns
  const originalTextRef = useRef('')
  const sectionKeyRef = useRef('')

  // Accept bar shows when the last response was refinement or generation
  const hasActiveRefinement =
    latestResponseType === 'refinement' || latestResponseType === 'generation'

  const addSystemMessage = useCallback((content: string) => {
    setMessages((prev) => [...prev, { role: 'system', content, timestamp: new Date() }])
  }, [])

  // Start a refine session — updates context, adds separator, keeps messages
  const initSession = useCallback(
    (selectedText: string, sectionKey: string, mode: 'refine' | 'generate') => {
      originalTextRef.current = selectedText
      sectionKeyRef.current = sectionKey
      setLatestRefinedText(null)
      setLatestResponseType(null)

      const label = selectedText
        ? `Refining selected text in ${sectionKey.replace(/_/g, ' ')}`
        : `Generating content for ${sectionKey.replace(/_/g, ' ')}`
      setMessages((prev) => [...prev, { role: 'system', content: label, timestamp: new Date() }])
    },
    []
  )

  // Unified send — routes everything through the /chat endpoint
  const sendMessage = useCallback(
    async (message: string, sectionKey: string) => {
      const userMsg: ChatMessage = {
        role: 'user',
        content: message,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, userMsg])
      setIsLoading(true)

      try {
        // If we have a latest refined text from a previous turn, use that
        // as the selected_text for iterative refinement
        const selectedText = latestRefinedText ?? originalTextRef.current

        // Build conversation history from previous messages (skip system hints)
        // Use a snapshot of messages before adding the current user message
        const history = messages
          .filter((m) => m.role === 'user' || m.role === 'assistant')
          .map((m) => ({ role: m.role, content: m.content }))
          .slice(-20)

        const result = await chatMessage(projectId, brdId, {
          message,
          section_context: sectionKey || sectionKeyRef.current,
          selected_text: selectedText || undefined,
          conversation_history: history.length > 0 ? history : undefined,
        })

        // Update state based on response type
        if (result.response_type === 'refinement' || result.response_type === 'generation') {
          setLatestRefinedText(result.content)
        }
        setLatestResponseType(result.response_type)

        const assistantMsg: ChatMessage = {
          role: 'assistant',
          content: result.content,
          timestamp: new Date(),
          sourcesUsed: result.sources_used,
        }
        setMessages((prev) => {
          const updated = [...prev, assistantMsg]
          // Add a hint when refinement is ready so user knows to click Accept
          if (result.response_type === 'refinement' || result.response_type === 'generation') {
            updated.push({
              role: 'system',
              content: 'Click "Accept & Replace" below to apply these changes to the BRD.',
              timestamp: new Date(),
            })
          }
          return updated
        })
      } catch (err: any) {
        const errorMsg: ChatMessage = {
          role: 'assistant',
          content: `Error: ${getApiError(err, 'Something went wrong')}`,
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, errorMsg])
      } finally {
        setIsLoading(false)
      }
    },
    [projectId, brdId, latestRefinedText]
  )

  // Clear refinement tracking without wiping messages (used after Accept)
  const clearRefinement = useCallback(() => {
    setLatestRefinedText(null)
    setLatestResponseType(null)
    originalTextRef.current = ''
  }, [])

  const reset = useCallback(() => {
    setMessages([])
    setLatestRefinedText(null)
    setLatestResponseType(null)
    originalTextRef.current = ''
    sectionKeyRef.current = ''
  }, [])

  return {
    messages,
    isLoading,
    latestRefinedText,
    latestResponseType,
    hasActiveRefinement,
    sendMessage,
    initSession,
    addSystemMessage,
    clearRefinement,
    reset,
  }
}
