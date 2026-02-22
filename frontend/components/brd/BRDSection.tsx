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

/** Check if a string looks like a pipe-delimited table row */
function isPipeRow(s: string): boolean {
  const t = s.trim()
  return t.startsWith('|') && t.endsWith('|') && t.split('|').length >= 3
}

/** Check if a string is a table separator row (| --- | --- |) */
function isSeparatorRow(s: string): boolean {
  const t = s.trim()
  if (!t.startsWith('|')) return false
  const cells = t.split('|').filter(Boolean)
  return cells.every((c) => /^\s*:?-{2,}:?\s*$/.test(c))
}

/**
 * Parse pipe-delimited text into table rows.
 * Returns null if text doesn't look like a table.
 */
function parsePipeTable(text: string): { headers: string[]; rows: string[][] } | null {
  // Split by newline, handle both \n and literal \n in strings
  const lines = text
    .replace(/\\n/g, '\n')
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l.length > 0)

  if (lines.length < 2) return null

  // Find pipe rows
  const pipeLines = lines.filter((l) => l.includes('|'))
  if (pipeLines.length < 2) return null

  // Parse each pipe line into cells
  const parseLine = (line: string): string[] => {
    // Remove leading/trailing pipes, split by |
    let trimmed = line.trim()
    if (trimmed.startsWith('|')) trimmed = trimmed.slice(1)
    if (trimmed.endsWith('|')) trimmed = trimmed.slice(0, -1)
    return trimmed.split('|').map((c) => c.trim())
  }

  // First pipe line is header
  const allPipeLines = lines.filter((l) => l.includes('|'))

  // Find separator (row with only dashes/colons)
  const sepIdx = allPipeLines.findIndex((l) => isSeparatorRow(l))

  let headers: string[]
  let dataLines: string[]

  if (sepIdx >= 0) {
    // Use line before separator as header, lines after as data
    const headerIdx = Math.max(0, sepIdx - 1)
    headers = parseLine(allPipeLines[headerIdx] || '')
    dataLines = allPipeLines.slice(sepIdx + 1)
  } else {
    // No separator found — first line is header, rest is data
    headers = parseLine(allPipeLines[0])
    dataLines = allPipeLines.slice(1)
  }

  if (headers.length === 0) return null

  const rows = dataLines
    .filter((l) => !isSeparatorRow(l))
    .map((l) => parseLine(l))

  if (rows.length === 0) return null

  return { headers, rows }
}

/**
 * Aggressive markdown preprocessor:
 * 1. Fix literal \\n in strings → actual newlines
 * 2. Remove blank lines inside table blocks
 * 3. Trim leading whitespace from table rows
 * 4. Ensure blank line before/after table
 */
function preprocessMarkdown(content: string): string {
  // Fix literal \\n that may come from JSON double-escaping
  let fixed = content.replace(/\\n/g, '\n')

  const lines = fixed.split('\n')
  const result: string[] = []
  let inTable = false

  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trim()
    const looksLikeTable = trimmed.includes('|') && (trimmed.startsWith('|') || /\|.*\|/.test(trimmed))

    if (looksLikeTable) {
      if (!inTable) {
        // Ensure blank line before table
        if (result.length > 0 && result[result.length - 1].trim() !== '') {
          result.push('')
        }
        inTable = true
      }
      result.push(trimmed)
    } else if (inTable) {
      if (trimmed === '') {
        // Skip blank lines inside tables
        continue
      } else {
        inTable = false
        result.push('')
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
      const regex = /\[(\d+)\]|(?:Priority:\s*)(High|Medium|Low|Critical|Optional)/gi
      let match

      while ((match = regex.exec(child)) !== null) {
        if (match.index > lastIndex) {
          parts.push(child.substring(lastIndex, match.index))
        }

        if (match[1]) {
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

  /** Render a cell's text content with priority badge support */
  const renderCellContent = (text: string, keyPrefix: string) => {
    // Handle <br> tags
    const parts = text.split(/<br\s*\/?>/gi)
    return parts.map((part, i) => {
      const priorityMatch = part.match(/Priority:\s*(High|Medium|Low|Critical|Optional)/i)
      if (priorityMatch) {
        const before = part.slice(0, priorityMatch.index)
        const after = part.slice((priorityMatch.index || 0) + priorityMatch[0].length)
        return (
          <React.Fragment key={`${keyPrefix}-${i}`}>
            {i > 0 && <br />}
            {before}Priority: <PriorityBadge level={priorityMatch[1]} />{after}
          </React.Fragment>
        )
      }
      return (
        <React.Fragment key={`${keyPrefix}-${i}`}>
          {i > 0 && <br />}
          {part}
        </React.Fragment>
      )
    })
  }

  /**
   * Fallback: render pipe-delimited text as an HTML table.
   * This catches tables that remark-gfm failed to parse.
   */
  const FallbackTable = ({ text }: { text: string }) => {
    const table = parsePipeTable(text)
    if (!table) return null

    return (
      <div className="overflow-x-auto my-6 border border-border/60">
        <table className="w-full text-sm brd-table">
          <thead className="bg-muted/70 border-b-2 border-border">
            <tr>
              {table.headers.map((h, i) => (
                <th
                  key={i}
                  className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, ri) => (
              <tr
                key={ri}
                className="border-b border-border/40 hover:bg-muted/30 transition-colors"
              >
                {row.map((cell, ci) => (
                  <td key={ci} className="px-4 py-3 align-top break-words max-w-[400px]">
                    {renderCellContent(cell, `r${ri}c${ci}`)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  // Custom markdown components with enhanced styling
  const mdComponents: Record<string, React.FC<any>> = {
    p: ({ children }: { children?: React.ReactNode }) => {
      // Extract text content to check if this is a failed table parse
      const textContent = React.Children.toArray(children)
        .map((c) => (typeof c === 'string' ? c : ''))
        .join('')

      // If paragraph contains pipe-delimited text, render as fallback table
      if (textContent.includes('|') && (textContent.match(/\|/g) || []).length >= 4) {
        const table = parsePipeTable(textContent)
        if (table) {
          return <FallbackTable text={textContent} />
        }
      }

      return <p className="mb-4 last:mb-0 leading-relaxed">{injectEnhancements(children)}</p>
    },
    li: ({ children }: { children?: React.ReactNode }) => (
      <li className="leading-relaxed">{injectEnhancements(children)}</li>
    ),
    strong: ({ children }: { children?: React.ReactNode }) => {
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
    // Tables — clean, readable design (for when remark-gfm DOES parse correctly)
    table: ({ children }: { children?: React.ReactNode }) => (
      <div className="overflow-x-auto my-6 border border-border/60">
        <table className="w-full text-sm brd-table">{children}</table>
      </div>
    ),
    thead: ({ children }: { children?: React.ReactNode }) => (
      <thead className="bg-muted/70 border-b-2 border-border">{children}</thead>
    ),
    th: ({ children }: { children?: React.ReactNode }) => (
      <th className="px-4 py-3 text-left text-xs font-bold uppercase tracking-wider text-muted-foreground">
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
    blockquote: ({ children }: { children?: React.ReactNode }) => (
      <blockquote className="border-l-2 border-primary/40 pl-4 py-1 my-4 text-muted-foreground italic">
        {children}
      </blockquote>
    ),
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
