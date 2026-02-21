'use client'

import React from 'react'
import { Copy, Check } from 'lucide-react'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from '@/components/ui/button'
import { CitationBadge } from './CitationBadge'
import { BRDSection as BRDSectionType } from '@/lib/api/brds'

interface BRDSectionProps {
  section: BRDSectionType | undefined
  title: string
  sectionKey?: string
  onViewDocument?: (documentId: string) => void
}

export function BRDSection({ section, title, sectionKey, onViewDocument }: BRDSectionProps) {
  const [copied, setCopied] = useState(false)

  if (!section || !section.content) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        <p>This section is not available yet.</p>
      </div>
    )
  }

  const handleCopy = async () => {
    await navigator.clipboard.writeText(section.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Walk React children and replace [N] citation markers with CitationBadge
  const injectCitations = (children: React.ReactNode): React.ReactNode => {
    return React.Children.map(children, (child) => {
      if (typeof child !== 'string') return child

      const parts: React.ReactNode[] = []
      let lastIndex = 0
      const regex = /\[(\d+)\]/g
      let match

      while ((match = regex.exec(child)) !== null) {
        if (match.index > lastIndex) {
          parts.push(child.substring(lastIndex, match.index))
        }
        const citationId = match[1]
        const citation = section.citations?.find((c) => c.id === citationId)
        if (citation) {
          parts.push(
            <CitationBadge
              key={`c-${match.index}`}
              citation={citation}
              onViewDocument={onViewDocument}
            />
          )
        } else {
          parts.push(`[${citationId}]`)
        }
        lastIndex = match.index + match[0].length
      }

      if (lastIndex < child.length) {
        parts.push(child.substring(lastIndex))
      }

      return parts.length > 0 ? <>{parts}</> : child
    })
  }

  // Custom markdown components that inject citation badges and style tables
  const mdComponents: Record<string, React.FC<{ children?: React.ReactNode }>> = {
    p: ({ children }) => <p className="mb-4 last:mb-0">{injectCitations(children)}</p>,
    li: ({ children }) => <li>{injectCitations(children)}</li>,
    table: ({ children }) => (
      <div className="overflow-x-auto my-4">
        <table className="w-full border-collapse text-sm">{children}</table>
      </div>
    ),
    thead: ({ children }) => <thead className="bg-muted/50">{children}</thead>,
    th: ({ children }) => (
      <th className="p-2 border text-left font-semibold">{injectCitations(children)}</th>
    ),
    td: ({ children }) => (
      <td className="p-2 border">{injectCitations(children)}</td>
    ),
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">{title}</h2>
        <Button
          variant="outline"
          size="sm"
          onClick={handleCopy}
          className="gap-2"
        >
          {copied ? (
            <>
              <Check className="h-4 w-4" />
              Copied
            </>
          ) : (
            <>
              <Copy className="h-4 w-4" />
              Copy
            </>
          )}
        </Button>
      </div>

      <div className="border rounded-lg p-6 bg-card" data-section-key={sectionKey}>
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
            {section.content}
          </ReactMarkdown>
        </div>
      </div>

      {section.citations && section.citations.length > 0 && (
        <div className="border-t pt-6">
          <h3 className="text-sm font-medium mb-4">Citations</h3>
          <div className="space-y-3">
            {section.citations.map((citation) => (
              <div
                key={citation.id}
                className="text-sm p-3 bg-muted/50 rounded-md"
              >
                <div className="flex items-start gap-2">
                  <span className="font-medium text-primary">[{citation.id}]</span>
                  <div className="flex-1">
                    <p className="font-medium mb-1">{citation.source}</p>
                    <p className="text-muted-foreground text-xs">&ldquo;{citation.text}&rdquo;</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
