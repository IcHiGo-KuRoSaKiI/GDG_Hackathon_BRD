'use client'

import React from 'react'
import { Copy, Check } from 'lucide-react'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { Button } from '@/components/ui/button'
import { CitationBadge } from './CitationBadge'
import { BRDSection as BRDSectionType } from '@/lib/api/brds'

interface BRDSectionProps {
  section: BRDSectionType | undefined
  title: string
  sectionKey?: string
  onViewDocument?: (documentId: string) => void
}

// Priority badge color map
const PRIORITY_COLORS: Record<string, string> = {
  high: 'bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/30',
  critical: 'bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/30',
  medium: 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30',
  low: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
  optional: 'bg-slate-500/15 text-slate-600 dark:text-slate-400 border-slate-500/30',
}

function PriorityBadge({ level }: { level: string }) {
  const normalized = level.trim().toLowerCase()
  const colors = PRIORITY_COLORS[normalized] || 'bg-muted text-muted-foreground border-border'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 text-xs font-semibold uppercase tracking-wider border ${colors}`}>
      {level.trim()}
    </span>
  )
}

/**
 * Fix common markdown table issues from AI-generated content:
 * 1. Remove blank lines between table header and separator
 * 2. Remove blank lines between table rows
 * 3. Trim leading whitespace from table rows
 * 4. Ensure blank line before table start
 */
function preprocessMarkdown(content: string): string {
  const lines = content.split('\n')
  const result: string[] = []
  let inTable = false

  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trim()
    const isTableRow = /^\|/.test(trimmed)

    if (isTableRow) {
      if (!inTable) {
        // Ensure blank line before table starts (if prev line isn't blank/heading)
        if (result.length > 0 && result[result.length - 1].trim() !== '') {
          result.push('')
        }
        inTable = true
      }
      // Push trimmed table row (remove leading whitespace that breaks parsing)
      result.push(trimmed)
    } else if (inTable) {
      if (trimmed === '') {
        // Skip blank lines inside tables — they break remark-gfm parsing
        continue
      } else {
        // Non-table, non-blank line → table ended
        inTable = false
        result.push('') // blank line after table
        result.push(lines[i])
      }
    } else {
      result.push(lines[i])
    }
  }

  return result.join('\n')
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

  const processedContent = preprocessMarkdown(section.content)

  // Walk React children and replace [N] citation markers with CitationBadge
  // Also detect "Priority: High/Medium/Low" patterns and inject colored badges
  const injectEnhancements = (children: React.ReactNode): React.ReactNode => {
    return React.Children.map(children, (child) => {
      if (typeof child !== 'string') return child

      const parts: React.ReactNode[] = []
      let lastIndex = 0
      // Match citation [N] and priority patterns
      const regex = /\[(\d+)\]|(?:Priority:\s*)(High|Medium|Low|Critical|Optional)/gi
      let match

      while ((match = regex.exec(child)) !== null) {
        if (match.index > lastIndex) {
          parts.push(child.substring(lastIndex, match.index))
        }

        if (match[1]) {
          // Citation marker [N]
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
        } else if (match[2]) {
          // Priority pattern — "Priority: High"
          parts.push('Priority: ')
          parts.push(<PriorityBadge key={`p-${match.index}`} level={match[2]} />)
        }

        lastIndex = match.index + match[0].length
      }

      if (lastIndex < child.length) {
        parts.push(child.substring(lastIndex))
      }

      return parts.length > 0 ? <>{parts}</> : child
    })
  }

  // Custom markdown components with enhanced styling
  const mdComponents: Record<string, React.FC<any>> = {
    p: ({ children }: { children?: React.ReactNode }) => (
      <p className="mb-4 last:mb-0 leading-relaxed">{injectEnhancements(children)}</p>
    ),
    li: ({ children }: { children?: React.ReactNode }) => (
      <li className="leading-relaxed">{injectEnhancements(children)}</li>
    ),
    strong: ({ children }: { children?: React.ReactNode }) => {
      // Detect requirement IDs like "FR-01", "NFR-02", "FR-EVAL-01"
      const text = React.Children.toArray(children).join('')
      const isReqId = /^(FR|NFR|BR|SR|TR)-[\w.-]+$/i.test(text.trim())
      const isLabel = /^(Requirement|Acceptance Criteria|Description|Rationale|Impact|Risk|Mitigation):?$/i.test(text.trim())
      const isScopeTag = /^(IN-SCOPE|OUT-OF-SCOPE)$/i.test(text.trim())

      if (isReqId) {
        return (
          <span className="inline-flex items-center px-2 py-0.5 text-xs font-bold font-mono uppercase tracking-wider bg-primary/10 text-primary border border-primary/30 mr-1">
            {children}
          </span>
        )
      }
      if (isScopeTag) {
        const isIn = /IN-SCOPE/i.test(text)
        return (
          <span className={`inline-flex items-center px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider border ${
            isIn
              ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
              : 'bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/30'
          }`}>
            {children}
          </span>
        )
      }
      if (isLabel) {
        return <span className="font-semibold text-muted-foreground uppercase text-xs tracking-wider">{children}</span>
      }
      return <strong>{children}</strong>
    },
    // Tables — clean, readable design
    table: ({ children }: { children?: React.ReactNode }) => (
      <div className="overflow-x-auto my-6 border border-border/60">
        <table className="w-full text-sm brd-table">{children}</table>
      </div>
    ),
    thead: ({ children }: { children?: React.ReactNode }) => (
      <thead className="bg-muted/70 border-b-2 border-border">{children}</thead>
    ),
    th: ({ children }: { children?: React.ReactNode }) => (
      <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground whitespace-nowrap">
        {injectEnhancements(children)}
      </th>
    ),
    tr: ({ children }: { children?: React.ReactNode }) => (
      <tr className="border-b border-border/40 hover:bg-muted/30 transition-colors">
        {children}
      </tr>
    ),
    td: ({ children }: { children?: React.ReactNode }) => (
      <td className="px-4 py-3 align-top break-words max-w-[400px]">
        {injectEnhancements(children)}
      </td>
    ),
    // Headings inside content — visual hierarchy
    h1: ({ children }: { children?: React.ReactNode }) => (
      <h1 className="text-xl font-bold font-mono mt-8 mb-4 pb-2 border-b border-border/50">{children}</h1>
    ),
    h2: ({ children }: { children?: React.ReactNode }) => (
      <h2 className="text-lg font-bold font-mono mt-6 mb-3 pb-1.5 border-b border-border/30">{children}</h2>
    ),
    h3: ({ children }: { children?: React.ReactNode }) => (
      <h3 className="text-base font-bold mt-5 mb-2 text-primary">{children}</h3>
    ),
    h4: ({ children }: { children?: React.ReactNode }) => (
      <h4 className="text-sm font-bold mt-4 mb-2 uppercase tracking-wider">{children}</h4>
    ),
    // Blockquotes
    blockquote: ({ children }: { children?: React.ReactNode }) => (
      <blockquote className="border-l-2 border-primary/40 pl-4 py-1 my-4 text-muted-foreground italic">
        {children}
      </blockquote>
    ),
    // Horizontal rules as section dividers
    hr: () => <hr className="my-6 border-border/50" />,
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

      <div className="border p-4 md:p-6 bg-card" data-section-key={sectionKey}>
        <div className="prose prose-sm dark:prose-invert max-w-none brd-content">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeRaw]}
            components={mdComponents}
          >
            {processedContent}
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
                className="text-sm p-3 bg-muted/50"
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
