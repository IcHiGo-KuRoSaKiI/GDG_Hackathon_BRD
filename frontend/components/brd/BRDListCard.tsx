'use client'

import { FileText, AlertTriangle, CheckCircle, CheckCircle2, Clock, Loader2, Trash2 } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { BRD } from '@/lib/api/brds'
import { formatRelativeTime } from '@/lib/utils/formatters'
import Link from 'next/link'

interface BRDListCardProps {
  brd: BRD
  projectId: string
  onDelete?: (brd: BRD) => void
}

export function BRDListCard({ brd, projectId, onDelete }: BRDListCardProps) {
  const handleDeleteClick = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    onDelete?.(brd)
  }
  const sectionCount = brd.sections
    ? Object.keys(brd.sections).filter(
        (key) => brd.sections[key as keyof typeof brd.sections]?.content
      ).length
    : 0

  const getStatusBadge = () => {
    switch (brd.status) {
      case 'complete':
        return (
          <Badge variant="default" className="bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20">
            <CheckCircle className="h-3 w-3 mr-1" />
            Complete
          </Badge>
        )
      case 'processing':
        return (
          <Badge variant="default" className="bg-amber-500/10 text-amber-500 hover:bg-amber-500/20">
            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
            Processing {brd.processing_progress ? `(${brd.processing_progress}%)` : ''}
          </Badge>
        )
      case 'failed':
        return (
          <Badge variant="destructive">
            <AlertTriangle className="h-3 w-3 mr-1" />
            Failed
          </Badge>
        )
      default:
        return null
    }
  }

  return (
    <Card className="hover:shadow-lg transition-all hover:border-primary/50">
      <CardContent className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-start gap-3 flex-1">
            <FileText className="h-5 w-5 text-primary mt-1" />
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-medium">BRD #{brd.id?.slice(0, 8) || 'Generating...'}</h3>
                {getStatusBadge()}
              </div>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                <span>
                  {brd.created_at
                    ? `Generated ${formatRelativeTime(brd.created_at)}`
                    : 'In progress...'}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {brd.status === 'complete' && brd.id && (
              <Link href={`/projects/${projectId}/brds/${brd.id}`}>
                <Button variant="outline" size="sm">
                  View
                </Button>
              </Link>
            )}
            {onDelete && brd.id && (
              <Button
                variant="ghost"
                size="icon"
                className="text-muted-foreground hover:text-destructive"
                onClick={handleDeleteClick}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>

        {brd.status === 'complete' && (
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>{sectionCount} sections</span>
            {brd.conflicts && brd.conflicts.length > 0 && (() => {
              const total = brd.conflicts.length
              const resolvedCount = brd.conflicts.filter(
                (c) => c.status && c.status !== 'open'
              ).length
              const allResolved = resolvedCount === total

              return (
                <span className={`flex items-center gap-1 ${
                  allResolved ? 'text-emerald-500' : 'text-amber-500'
                }`}>
                  {allResolved
                    ? <CheckCircle2 className="h-3 w-3" />
                    : <AlertTriangle className="h-3 w-3" />
                  }
                  {total} conflict{total > 1 ? 's' : ''}
                  {resolvedCount > 0 && (
                    <span className="text-muted-foreground font-normal">
                      ({resolvedCount} resolved)
                    </span>
                  )}
                </span>
              )
            })()}
          </div>
        )}

        {brd.status === 'processing' && brd.processing_stage && (
          <p className="text-sm text-muted-foreground mt-2">{brd.processing_stage}</p>
        )}
      </CardContent>
    </Card>
  )
}
