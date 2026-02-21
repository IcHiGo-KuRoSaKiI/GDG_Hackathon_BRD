'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Download, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { getBRD, BRD } from '@/lib/api/brds'
import { BRDSectionTabs } from '@/components/brd/BRDSectionTabs'
import { BRDSection } from '@/components/brd/BRDSection'
import { ConflictPanel } from '@/components/brd/ConflictPanel'
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
  const router = useRouter()
  const projectId = params.projectId as string
  const brdId = params.brdId as string

  const [brd, setBRD] = useState<BRD | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeSection, setActiveSection] = useState('executive_summary')

  useEffect(() => {
    loadBRD()
  }, [projectId, brdId])

  const loadBRD = async () => {
    try {
      setLoading(true)
      const data = await getBRD(projectId, brdId)
      setBRD(data)

      // Set first available section as active
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

  const handleExport = () => {
    if (!brd || !brd.sections) return

    // Compile all sections into a markdown document
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

    // Create download
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
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
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

          <Button onClick={handleExport} className="gap-2">
            <Download className="h-4 w-4" />
            Export as Markdown
          </Button>
        </div>
      </div>

      {/* Conflicts Panel */}
      {brd.conflicts && brd.conflicts.length > 0 && (
        <div className="mb-8">
          <ConflictPanel conflicts={brd.conflicts} />
        </div>
      )}

      {/* Section Tabs */}
      <div className="mb-6">
        <BRDSectionTabs
          activeSection={activeSection}
          onSectionChange={setActiveSection}
          availableSections={availableSections}
        />
      </div>

      {/* Section Content */}
      <div className="mb-8">
        <BRDSection
          section={brd.sections?.[activeSection as keyof typeof brd.sections]}
          title={SECTION_TITLES[activeSection] || activeSection}
        />
      </div>
    </div>
  )
}
