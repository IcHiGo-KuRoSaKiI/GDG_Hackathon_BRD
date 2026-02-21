'use client'

import { useEffect, useRef, useState } from 'react'
import { X, Send, Check, RotateCcw, Sparkles, PenLine, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ChatMessage } from '@/hooks/useRefineText'

interface RefineChatPanelProps {
  open: boolean
  mode: 'refine' | 'generate'
  sectionTitle: string
  originalText: string
  messages: ChatMessage[]
  isLoading: boolean
  latestRefinedText: string | null
  onSendPrompt: (instruction: string) => void
  onAccept: () => void
  onClose: () => void
}

export function RefineChatPanel({
  open,
  mode,
  sectionTitle,
  originalText,
  messages,
  isLoading,
  latestRefinedText,
  onSendPrompt,
  onAccept,
  onClose,
}: RefineChatPanelProps) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

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
    onSendPrompt(trimmed)
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
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />

      {/* Panel */}
      <div
        className="fixed right-0 top-0 h-full w-[420px] max-w-full bg-background border-l shadow-2xl z-50 flex flex-col animate-in slide-in-from-right duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b shrink-0">
          <div className="flex items-center gap-2">
            {mode === 'refine' ? (
              <Sparkles className="h-4 w-4 text-primary" />
            ) : (
              <PenLine className="h-4 w-4 text-primary" />
            )}
            <div>
              <h3 className="text-sm font-semibold">
                {mode === 'refine' ? 'Refine Text' : 'Generate Content'}
              </h3>
              <p className="text-xs text-muted-foreground">{sectionTitle}</p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Original text (refine mode only) */}
        {mode === 'refine' && originalText && (
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
                {mode === 'refine'
                  ? 'Describe how you want to refine the selected text.'
                  : 'Describe what content you want to generate.'}
              </p>
              <p className="text-xs">
                {mode === 'generate'
                  ? 'AI will search your project documents for context.'
                  : 'You can iterate with multiple prompts until satisfied.'}
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[90%] rounded-lg p-3 text-sm ${
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted border'
                }`}
              >
                {msg.role === 'assistant' ? (
                  <div className="prose prose-sm dark:prose-invert max-w-none">
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
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-muted border rounded-lg p-3 flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                {mode === 'generate' ? 'Searching documents & generating...' : 'Refining...'}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Accept bar (when refined text available) */}
        {latestRefinedText && !isLoading && (
          <div className="p-3 border-t bg-muted/30 shrink-0 flex items-center gap-2">
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
                mode === 'refine'
                  ? 'e.g. "Make this more concise and professional"'
                  : 'e.g. "Add a security requirements section covering OAuth and RBAC"'
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
            Enter to send, Shift+Enter for new line, Esc to close
          </p>
        </div>
      </div>
    </>
  )
}
