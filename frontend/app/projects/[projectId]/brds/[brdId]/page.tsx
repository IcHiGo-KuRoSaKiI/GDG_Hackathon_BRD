'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import { ArrowLeft, Download, Loader2, MessageSquare } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { getBRD, updateBRDSection, BRD } from '@/lib/api/brds'
import { BRDSectionTabs } from '@/components/brd/BRDSectionTabs'
import { BRDSection } from '@/components/brd/BRDSection'
import { ConflictPanel } from '@/components/brd/ConflictPanel'
import { RefineToolbar } from '@/components/brd/RefineToolbar'
import { RefineChatPanel } from '@/components/brd/RefineChatPanel'
import { useTextSelection } from '@/hooks/useTextSelection'
import { useRefineText } from '@/hooks/useRefineText'
import { formatRelativeTime } from '@/lib/utils/formatters'
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

  // Callback ref so useTextSelection re-runs when the element mounts after loading
  const [contentEl, setContentEl] = useState<HTMLDivElement | null>(null)

  // Snapshot selection state when chat opens (selection gets cleared on open)
  const refineSelectedTextRef = useRef('')
  const refineSectionKeyRef = useRef('')
  const refineModeRef = useRef<'refine' | 'generate'>('refine')

  const selection = useTextSelection(contentEl)
  const refine = useRefineText({ projectId, brdId })

  useEffect(() => {
    loadBRD()
  }, [projectId, brdId])

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
    refineModeRef.current = selection.mode
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
      if (originalSelectedText && currentSection.content.includes(originalSelectedText)) {
        newContent = currentSection.content.replace(
          originalSelectedText,
          refine.latestRefinedText
        )
      } else {
        // Generate mode or text not found — append to end of section
        newContent = currentSection.content + '\n\n' + refine.latestRefinedText
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

      // Keep sidebar open — clear refinement state, add confirmation
      refineSelectedTextRef.current = ''
      refine.clearRefinement()
      refine.addSystemMessage('Changes saved')
    } catch (err: any) {
      console.error('Failed to save section:', err)
    } finally {
      setSaving(false)
    }
  }, [refine, brd, projectId, brdId])

  // Close sidebar — keep messages for when it reopens
  const handleCloseChat = useCallback(() => {
    setChatOpen(false)
  }, [])

  // Explicit New Chat — clear everything
  const handleNewChat = useCallback(() => {
    refineSelectedTextRef.current = ''
    refineSectionKeyRef.current = activeSection
    refineModeRef.current = 'refine'
    refine.reset()
  }, [refine, activeSection])

  // General chat — send a question about the BRD (no text selection)
  const handleSendChat = useCallback(
    (message: string) => {
      refine.sendChat(message, activeSection)
    },
    [refine, activeSection]
  )

  // Toggle sidebar open/closed
  const handleToggleChat = useCallback(() => {
    setChatOpen((prev) => !prev)
  }, [])

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
      {/* Header */}
      <div className="px-8 pt-8 pb-0 shrink-0">
        <Link href={`/projects/${projectId}`}>
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Project
          </Button>
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Business Requirements Document</h1>
            <p className="text-muted-foreground">
              {brd.created_at && `Generated ${formatRelativeTime(brd.created_at)} • `}
              {availableSections.length} sections
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={handleToggleChat} className="gap-2">
              <MessageSquare className="h-4 w-4" />
              {chatOpen ? 'Hide Chat' : 'Chat'}
            </Button>
            <Button onClick={handleExport} className="gap-2">
              <Download className="h-4 w-4" />
              Export
            </Button>
          </div>
        </div>

        {/* Conflicts Panel */}
        {brd.conflicts && brd.conflicts.length > 0 && (
          <div className="mt-6">
            <ConflictPanel conflicts={brd.conflicts} />
          </div>
        )}

        {/* Section Tabs */}
        <div className="mt-6 mb-0">
          <BRDSectionTabs
            activeSection={activeSection}
            onSectionChange={setActiveSection}
            availableSections={availableSections}
          />
        </div>
      </div>

      {/* Main content area — flex row */}
      <div className="flex flex-1 min-h-0">
        {/* BRD content — scrollable */}
        <div className="flex-1 min-w-0 overflow-y-auto px-8 py-6 relative" ref={setContentEl}>
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

        {/* Chat Sidebar */}
        <RefineChatPanel
          open={chatOpen}
          mode={refineModeRef.current}
          sectionTitle={SECTION_TITLES[refineSectionKeyRef.current] || refineSectionKeyRef.current || SECTION_TITLES[activeSection] || activeSection}
          originalText={refineSelectedTextRef.current}
          messages={refine.messages}
          isLoading={refine.isLoading || saving}
          latestRefinedText={refine.latestRefinedText}
          hasActiveRefinement={refine.hasActiveRefinement}
          onSendPrompt={refine.sendPrompt}
          onSendChat={handleSendChat}
          onAccept={handleAccept}
          onNewChat={handleNewChat}
          onClose={handleCloseChat}
        />
      </div>
    </div>
  )
}
