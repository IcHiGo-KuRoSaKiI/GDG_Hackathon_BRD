'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { X, Send, Check, CheckCircle2, RotateCcw, Sparkles, Loader2, MessageSquare, Plus, GripVertical } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ChatMessage } from '@/hooks/useRefineText'
import { useIsMobile } from '@/hooks/useIsMobile'

const MIN_WIDTH = 360
const MAX_WIDTH = 800
const DEFAULT_WIDTH = 520

interface RefineChatPanelProps {
  open: boolean
  sectionTitle: string
  originalText: string
  messages: ChatMessage[]
  isLoading: boolean
  latestRefinedText: string | null
  hasActiveRefinement: boolean
  canConfirmClose?: boolean
  onSendMessage: (message: string) => void
  onAccept: () => void
  onConfirmClose?: () => void
  onNewChat: () => void
  onClose: () => void
}

export function RefineChatPanel({
  open,
  sectionTitle,
  originalText,
  messages,
  isLoading,
  latestRefinedText,
  hasActiveRefinement,
  canConfirmClose,
  onSendMessage,
  onAccept,
  onConfirmClose,
  onNewChat,
  onClose,
}: RefineChatPanelProps) {
  const [input, setInput] = useState('')
  const [width, setWidth] = useState(DEFAULT_WIDTH)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const isDragging = useRef(false)
  const isMobile = useIsMobile()

  // Resize drag handler (desktop only)
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    isDragging.current = true
    const startX = e.clientX
    const startWidth = width

    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return
      const delta = startX - e.clientX
      const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startWidth + delta))
      setWidth(newWidth)
    }

    const handleMouseUp = () => {
      isDragging.current = false
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [width])

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // Focus input when panel opens
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 200)
    }
  }, [open])

  const handleSubmit = () => {
    const trimmed = input.trim()
    if (!trimmed || isLoading) return
    onSendMessage(trimmed)
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
    if (e.key === 'Escape') {
      onClose()
    }
  }

  if (!open) return null

  return (
    <div
      className={
        isMobile
          ? 'fixed inset-0 z-50 bg-background flex flex-col'
          : 'shrink-0 border-l bg-background flex flex-col h-full relative'
      }
      style={isMobile ? undefined : { width: `${width}px` }}
    >
      {/* Resize handle — desktop only */}
      {!isMobile && (
        <div
          onMouseDown={handleMouseDown}
          className="absolute left-0 top-0 bottom-0 w-1.5 cursor-col-resize z-20 group hover:bg-primary/20 active:bg-primary/30 transition-colors"
          title="Drag to resize"
        >
          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1.5 h-12 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
            <GripVertical className="h-4 w-4 text-muted-foreground" />
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          {hasActiveRefinement ? (
            <Sparkles className="h-4 w-4 text-primary shrink-0" />
          ) : (
            <MessageSquare className="h-4 w-4 text-primary shrink-0" />
          )}
          <div className="min-w-0">
            <h3 className="text-sm font-semibold truncate">
              {hasActiveRefinement ? 'Refine Text' : 'BRD Chat'}
            </h3>
            <p className="text-xs text-muted-foreground truncate">{sectionTitle}</p>
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <Button
            variant="ghost"
            size="icon"
            onClick={onNewChat}
            className="h-8 w-8"
            title="New Chat"
          >
            <Plus className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Original text (refine mode only) */}
      {hasActiveRefinement && originalText && (
        <div className="p-3 mx-4 mt-3 rounded-md bg-muted/50 border text-xs shrink-0">
          <p className="text-muted-foreground font-medium mb-1">Selected text:</p>
          <p className="line-clamp-4">{originalText}</p>
        </div>
      )}

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !isLoading && (
          <div className="text-center text-muted-foreground text-sm py-8">
            <p className="mb-2">
              {hasActiveRefinement
                ? 'Describe how you want to refine the selected text.'
                : 'Ask anything about this BRD.'}
            </p>
            <p className="text-xs">
              AI will search your project documents for context.
            </p>
          </div>
        )}

        {messages.map((msg, i) => {
          if (msg.role === 'system') {
            return (
              <div key={i} className="flex justify-center">
                <span className="text-[11px] text-muted-foreground bg-muted/50 px-3 py-1 rounded-full">
                  {msg.content}
                </span>
              </div>
            )
          }

          return (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`rounded-lg p-3 text-sm ${
                  msg.role === 'user'
                    ? 'max-w-[85%] bg-primary text-primary-foreground'
                    : 'w-full bg-muted border'
                }`}
              >
                {msg.role === 'assistant' ? (
                  <div className="prose prose-sm dark:prose-invert max-w-none overflow-x-auto">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                    {msg.sourcesUsed && msg.sourcesUsed.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2 pt-2 border-t">
                        {msg.sourcesUsed.map((src) => (
                          <Badge key={src} variant="outline" className="text-[10px]">
                            {src}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <p>{msg.content}</p>
                )}
              </div>
            </div>
          )
        })}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-muted border rounded-lg p-3 flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              {hasActiveRefinement ? 'Refining...' : 'Searching documents...'}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Accept bar (only when AI returned refinement/generation) */}
      {hasActiveRefinement && latestRefinedText && !isLoading && (
        <div className="px-3 py-3 border-t-2 border-primary/30 bg-primary/10 shrink-0 space-y-2">
          <p className="text-xs text-primary font-medium px-1">
            Ready to apply changes to the BRD
          </p>
          <div className="flex items-center gap-2">
            <Button size="sm" className="gap-1.5 flex-1" onClick={onAccept}>
              <Check className="h-3.5 w-3.5" />
              Accept & Replace
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5"
              onClick={() => inputRef.current?.focus()}
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Iterate
            </Button>
          </div>
        </div>
      )}

      {/* Confirm & Close bar (conflict already resolved, no BRD changes needed) */}
      {canConfirmClose && onConfirmClose && (
        <div className="px-3 py-3 border-t-2 border-emerald-500/30 bg-emerald-500/10 shrink-0 space-y-2">
          <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium px-1">
            AI verified — this conflict is already resolved in the BRD
          </p>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              className="gap-1.5 flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
              onClick={onConfirmClose}
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              Confirm & Close
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5"
              onClick={() => inputRef.current?.focus()}
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Disagree
            </Button>
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="p-3 border-t shrink-0">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              hasActiveRefinement
                ? 'e.g. "Make this more concise and professional"'
                : 'Ask about this BRD...'
            }
            rows={2}
            className="flex-1 resize-none rounded-md border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            disabled={isLoading}
          />
          <Button
            size="icon"
            onClick={handleSubmit}
            disabled={!input.trim() || isLoading}
            className="shrink-0 self-end"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="text-[10px] text-muted-foreground mt-1.5">
          Enter to send{isMobile ? '' : ', Shift+Enter for new line'}, Esc to close
        </p>
      </div>
    </div>
  )
}
