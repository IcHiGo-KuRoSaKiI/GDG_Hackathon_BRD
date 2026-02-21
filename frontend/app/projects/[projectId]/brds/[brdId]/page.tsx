'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import { ArrowLeft, CheckCircle2, Cpu, DollarSign, Download, Loader2, MessageSquare, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { getBRD, updateBRDSection, updateConflictStatus, BRD, Conflict, ConflictStatus } from '@/lib/api/brds'
import { BRDSectionTabs } from '@/components/brd/BRDSectionTabs'
import { BRDSection } from '@/components/brd/BRDSection'
import { ConflictPanel } from '@/components/brd/ConflictPanel'
import { RefineToolbar } from '@/components/brd/RefineToolbar'
import { RefineChatPanel } from '@/components/brd/RefineChatPanel'
import { useTextSelection } from '@/hooks/useTextSelection'
import { useRefineText } from '@/hooks/useRefineText'
import { formatRelativeTime } from '@/lib/utils/formatters'
import { requirementToSectionKey } from '@/lib/utils/sectionMapping'
import Link from 'next/link'

const SECTION_TITLES: Record<string, string> = {
  executive_summary: 'Executive Summary',
  business_objectives: 'Business Objectives',
  stakeholders: 'Stakeholders',
  project_scope: 'Project Scope',
  functional_requirements: 'Functional Requirements',
  non_functional_requirements: 'Non-Functional Requirements',
  assumptions: 'Assumptions',
  success_metrics: 'Success Metrics',
  timeline: 'Timeline',
  project_background: 'Project Background',
  dependencies: 'Dependencies',
  risks: 'Risks',
  cost_benefit: 'Cost-Benefit Analysis',
}

export default function BRDViewerPage() {
  const params = useParams()
  const projectId = params.projectId as string
  const brdId = params.brdId as string

  const [brd, setBRD] = useState<BRD | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeSection, setActiveSection] = useState('executive_summary')
  const [chatOpen, setChatOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [updatedSection, setUpdatedSection] = useState<string | null>(null)
  const [isResolvingConflict, setIsResolvingConflict] = useState(false)
  const updatedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Callback ref so useTextSelection re-runs when the element mounts after loading
  const [contentEl, setContentEl] = useState<HTMLDivElement | null>(null)

  // Snapshot selection state when chat opens (selection gets cleared on open)
  const refineSelectedTextRef = useRef('')
  const refineSectionKeyRef = useRef('')

  // Track which conflict is being AI-resolved (so we can auto-update status on accept)
  const resolvingConflictRef = useRef<{ conflict: Conflict; index: number } | null>(null)

  const selection = useTextSelection(contentEl)
  const refine = useRefineText({ projectId, brdId })

  useEffect(() => {
    loadBRD()
  }, [projectId, brdId])

  // Clean up update indicator timer
  useEffect(() => {
    return () => {
      if (updatedTimerRef.current) clearTimeout(updatedTimerRef.current)
    }
  }, [])

  // Build conflict statuses from backend data
  const conflictStatuses: Record<string, ConflictStatus> = {}
  if (brd?.conflicts) {
    brd.conflicts.forEach((c) => {
      if (c.status) conflictStatuses[c.id] = c.status
    })
  }

  const loadBRD = async () => {
    try {
      setLoading(true)
      const data = await getBRD(projectId, brdId)
      setBRD(data)

      if (data.sections) {
        const availableSections = Object.keys(data.sections).filter(
          (key) => data.sections[key as keyof typeof data.sections]?.content
        )
        if (availableSections.length > 0) {
          setActiveSection(availableSections[0])
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load BRD')
    } finally {
      setLoading(false)
    }
  }

  // Open the refine chat panel — snapshot selection into refs before clearing
  const handleOpenRefine = useCallback(() => {
    refineSelectedTextRef.current = selection.selectedText
    refineSectionKeyRef.current = selection.sectionKey || activeSection
    refine.initSession(selection.selectedText, selection.sectionKey || activeSection, selection.mode)
    setChatOpen(true)
    selection.clearSelection()
  }, [selection, refine, activeSection])

  // Accept refined text → persist to backend, keep sidebar open
  const handleAccept = useCallback(async () => {
    if (!refine.latestRefinedText || !brd) return

    const sectionKey = refineSectionKeyRef.current
    const originalSelectedText = refineSelectedTextRef.current
    setSaving(true)

    try {
      const currentSection = brd.sections?.[sectionKey as keyof typeof brd.sections]
      if (!currentSection) return

      let newContent: string
      const responseType = refine.latestResponseType

      if (responseType === 'generation') {
        // Generation mode — append new content to section
        newContent = currentSection.content + '\n\n' + refine.latestRefinedText
      } else if (originalSelectedText && currentSection.content.includes(originalSelectedText)) {
        // Refinement with specific text selection — substring replace
        newContent = currentSection.content.replace(
          originalSelectedText,
          refine.latestRefinedText
        )
      } else {
        // Refinement without matching selection (e.g., conflict resolution,
        // or "apply" after brainstorming) — full section replacement
        newContent = refine.latestRefinedText
      }

      await updateBRDSection(projectId, brdId, sectionKey, newContent)

      // Update local state
      setBRD((prev) => {
        if (!prev) return prev
        return {
          ...prev,
          sections: {
            ...prev.sections,
            [sectionKey]: {
              ...prev.sections[sectionKey as keyof typeof prev.sections]!,
              content: newContent,
            },
          },
        }
      })

      // Show visual update indicator on the section — auto-navigate if needed
      setActiveSection(sectionKey)
      setUpdatedSection(sectionKey)
      if (updatedTimerRef.current) clearTimeout(updatedTimerRef.current)
      updatedTimerRef.current = setTimeout(() => setUpdatedSection(null), 5000)

      // If we were resolving a conflict, auto-mark it as resolved
      if (resolvingConflictRef.current) {
        const { index } = resolvingConflictRef.current
        try {
          await updateConflictStatus(projectId, brdId, index, 'resolved', refine.latestRefinedText)
          // Update local state so the UI reflects the change immediately
          setBRD((prev) => {
            if (!prev || !prev.conflicts) return prev
            const updatedConflicts = [...prev.conflicts]
            if (updatedConflicts[index]) {
              updatedConflicts[index] = { ...updatedConflicts[index], status: 'resolved' }
            }
            return { ...prev, conflicts: updatedConflicts }
          })
          refine.addSystemMessage('Changes saved — conflict marked as resolved')
        } catch (err) {
          console.error('Failed to update conflict status:', err)
          refine.addSystemMessage('Changes saved (conflict status update failed)')
        }
        resolvingConflictRef.current = null
        setIsResolvingConflict(false)
      } else {
        refine.addSystemMessage('Changes saved')
      }

      // Keep sidebar open — clear refinement state
      refineSelectedTextRef.current = ''
      refine.clearRefinement()
    } catch (err: any) {
      console.error('Failed to save section:', err)
    } finally {
      setSaving(false)
    }
  }, [refine, brd, projectId, brdId])

  // Confirm & close a conflict without changing BRD text (already resolved)
  const handleConfirmClose = useCallback(async () => {
    if (!resolvingConflictRef.current) return
    const { index } = resolvingConflictRef.current

    try {
      await updateConflictStatus(projectId, brdId, index, 'resolved')
      setBRD((prev) => {
        if (!prev || !prev.conflicts) return prev
        const updatedConflicts = [...prev.conflicts]
        if (updatedConflicts[index]) {
          updatedConflicts[index] = { ...updatedConflicts[index], status: 'resolved' }
        }
        return { ...prev, conflicts: updatedConflicts }
      })
      refine.addSystemMessage('Conflict confirmed as resolved — no BRD changes needed')
    } catch (err) {
      console.error('Failed to update conflict status:', err)
      refine.addSystemMessage('Failed to update conflict status')
    }

    resolvingConflictRef.current = null
    setIsResolvingConflict(false)
    refine.clearRefinement()
  }, [projectId, brdId, refine])

  // Close sidebar — keep messages for when it reopens
  const handleCloseChat = useCallback(() => {
    setChatOpen(false)
  }, [])

  // Explicit New Chat — clear everything
  const handleNewChat = useCallback(() => {
    refineSelectedTextRef.current = ''
    refineSectionKeyRef.current = activeSection
    resolvingConflictRef.current = null
    setIsResolvingConflict(false)
    refine.reset()
  }, [refine, activeSection])

  // Unified send — everything goes through refine.sendMessage
  const handleSendMessage = useCallback(
    (message: string) => {
      refine.sendMessage(message, activeSection)
    },
    [refine, activeSection]
  )

  // Toggle sidebar open/closed
  const handleToggleChat = useCallback(() => {
    setChatOpen((prev) => !prev)
  }, [])

  // Resolve conflict with AI — open chat pre-loaded with conflict context
  const handleResolveConflict = useCallback(
    (conflict: Conflict) => {
      // Track which conflict we're resolving (for auto-status on accept)
      const conflictIndex = brd?.conflicts?.findIndex((c) => c.id === conflict.id) ?? -1
      resolvingConflictRef.current = conflictIndex >= 0 ? { conflict, index: conflictIndex } : null
      setIsResolvingConflict(conflictIndex >= 0)

      const contextText = [
        `Conflict Type: ${conflict.conflict_type}`,
        `Severity: ${conflict.severity}`,
        `Description: ${conflict.description}`,
        `Affected Requirements: ${conflict.affected_requirements.join(', ')}`,
      ].join('\n')

      // Find the best section to set as context
      const sectionKey =
        conflict.affected_requirements
          .map((r) => requirementToSectionKey(r))
          .find(Boolean) || activeSection

      refineSelectedTextRef.current = contextText
      refineSectionKeyRef.current = sectionKey
      refine.initSession(contextText, sectionKey, 'refine')
      setChatOpen(true)

      // Auto-send a resolution request
      refine.sendMessage(
        `Help me resolve this ${conflict.severity}-severity ${conflict.conflict_type} conflict: "${conflict.description}". The affected requirements are: ${conflict.affected_requirements.join(', ')}. Suggest how to resolve this contradiction in the BRD.`,
        sectionKey
      )
    },
    [refine, activeSection, brd]
  )

  // Navigate to a BRD section (from conflict requirement badge click)
  const handleNavigateToSection = useCallback(
    (sectionKey: string) => {
      setActiveSection(sectionKey)
      // Scroll the content into view — contentEl is inside the scrollable parent
      requestAnimationFrame(() => {
        contentEl?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      })
    },
    [contentEl]
  )

  // Update conflict status (persisted to Firestore)
  const handleConflictStatusChange = useCallback(
    async (conflictId: string, status: ConflictStatus) => {
      const index = brd?.conflicts?.findIndex((c) => c.id === conflictId) ?? -1
      if (index < 0) return

      // Optimistic local update
      setBRD((prev) => {
        if (!prev || !prev.conflicts) return prev
        const updated = [...prev.conflicts]
        updated[index] = { ...updated[index], status }
        return { ...prev, conflicts: updated }
      })

      try {
        await updateConflictStatus(projectId, brdId, index, status)
      } catch (err) {
        console.error('Failed to persist conflict status:', err)
      }
    },
    [brd, projectId, brdId]
  )

  const handleExport = () => {
    if (!brd || !brd.sections) return

    let markdown = `# Business Requirements Document\n\n`
    markdown += `Generated: ${new Date(brd.created_at).toLocaleDateString()}\n\n`
    markdown += `---\n\n`

    Object.entries(brd.sections).forEach(([key, section]) => {
      if (section?.content) {
        const title = SECTION_TITLES[key] || key
        markdown += `## ${title}\n\n`
        markdown += `${section.content}\n\n`

        if (section.citations && section.citations.length > 0) {
          markdown += `### Citations\n\n`
          section.citations.forEach((citation) => {
            markdown += `- [${citation.id}] ${citation.source}: "${citation.text}"\n`
          })
          markdown += `\n`
        }

        markdown += `---\n\n`
      }
    })

    const blob = new Blob([markdown], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `BRD-${brdId?.slice(0, 8) || 'export'}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error || !brd) {
    return (
      <div className="p-8">
        <div className="p-4 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
          {error || 'BRD not found'}
        </div>
      </div>
    )
  }

  const availableSections = brd.sections
    ? Object.keys(brd.sections).filter(
        (key) => brd.sections[key as keyof typeof brd.sections]?.content
      )
    : []

  return (
    <div className="h-screen flex flex-col">
      {/* Fixed header: title bar only */}
      <div className="px-4 md:px-8 pt-4 md:pt-8 pb-4 shrink-0">
        <Link href={`/projects/${projectId}`}>
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Project
          </Button>
        </Link>

        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-xl md:text-3xl font-bold mb-2">Business Requirements Document</h1>
            <div className="flex flex-wrap items-center gap-2 md:gap-3 text-sm text-muted-foreground">
              <span>
                {brd.created_at && `Generated ${formatRelativeTime(brd.created_at)} · `}
                {availableSections.length} sections
              </span>
              {brd.generation_metadata?.token_usage && (
                <div className="hidden md:flex items-center gap-2 px-2.5 py-1 bg-muted/50 rounded-full text-xs font-medium">
                  <span className="flex items-center gap-1" title="Total tokens used">
                    <Zap className="h-3 w-3" />
                    {(brd.generation_metadata.token_usage.total_tokens / 1000).toFixed(0)}k tokens
                  </span>
                  <span className="text-muted-foreground/40">|</span>
                  <span className="flex items-center gap-1" title="Estimated LLM cost">
                    <DollarSign className="h-3 w-3" />
                    ${brd.generation_metadata.token_usage.estimated_cost_usd.toFixed(2)}
                  </span>
                  {brd.generation_metadata.model && (
                    <>
                      <span className="text-muted-foreground/40">|</span>
                      <span className="flex items-center gap-1" title="Model used">
                        <Cpu className="h-3 w-3" />
                        {brd.generation_metadata.model}
                      </span>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Button variant="outline" onClick={handleToggleChat} className="gap-2 flex-1 md:flex-none">
              <MessageSquare className="h-4 w-4" />
              {chatOpen ? 'Hide Chat' : 'Chat'}
            </Button>
            <Button onClick={handleExport} className="gap-2 flex-1 md:flex-none">
              <Download className="h-4 w-4" />
              Export
            </Button>
          </div>
        </div>
      </div>

      {/* Main area — flex row */}
      <div className="flex flex-1 min-h-0">
        {/* Left column: scrollable with conflict panel + sticky tabs + content */}
        <div className="flex-1 min-w-0 overflow-y-auto">
          {/* Conflicts Panel — scrolls with content */}
          {brd.conflicts && brd.conflicts.length > 0 && (
            <div className="px-4 md:px-8 mb-4">
              <ConflictPanel
                conflicts={brd.conflicts}
                onResolveWithAI={handleResolveConflict}
                onNavigateToSection={handleNavigateToSection}
                onStatusChange={handleConflictStatusChange}
                conflictStatuses={conflictStatuses}
              />
            </div>
          )}

          {/* Section Tabs — sticky so they stay visible while scrolling */}
          <div className="sticky top-0 z-10 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 px-4 md:px-8 py-2 border-b">
            <BRDSectionTabs
              activeSection={activeSection}
              onSectionChange={setActiveSection}
              availableSections={availableSections}
            />
          </div>

          {/* BRD content */}
          <div
            className={`px-4 md:px-8 py-6 relative transition-colors duration-700 ${
              updatedSection === activeSection
                ? 'bg-emerald-500/5'
                : ''
            }`}
            ref={setContentEl}
          >
            {/* Update success banner */}
            {updatedSection === activeSection && (
              <div className="mb-4 flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-4 py-2.5 animate-slide-in">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span className="font-medium">
                  {SECTION_TITLES[activeSection] || activeSection} updated successfully
                </span>
              </div>
            )}

            <BRDSection
              section={brd.sections?.[activeSection as keyof typeof brd.sections]}
              title={SECTION_TITLES[activeSection] || activeSection}
              sectionKey={activeSection}
            />

            {/* Floating Refine Toolbar */}
            {selection.isActive && !chatOpen && (
              <RefineToolbar
                position={selection.toolbarPosition}
                mode={selection.mode}
                onRefine={handleOpenRefine}
              />
            )}
          </div>
        </div>

        {/* Chat Sidebar */}
        <RefineChatPanel
          open={chatOpen}
          sectionTitle={SECTION_TITLES[refineSectionKeyRef.current] || refineSectionKeyRef.current || SECTION_TITLES[activeSection] || activeSection}
          originalText={refineSelectedTextRef.current}
          messages={refine.messages}
          isLoading={refine.isLoading || saving}
          latestRefinedText={refine.latestRefinedText}
          hasActiveRefinement={refine.hasActiveRefinement}
          canConfirmClose={isResolvingConflict && !refine.hasActiveRefinement && refine.latestResponseType === 'answer' && !refine.isLoading && !saving}
          onSendMessage={handleSendMessage}
          onAccept={handleAccept}
          onConfirmClose={handleConfirmClose}
          onNewChat={handleNewChat}
          onClose={handleCloseChat}
        />
      </div>
    </div>
  )
}
