'use client'

import { useState } from 'react'
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Circle,
  CheckCircle2,
  Clock,
  MinusCircle,
  ArrowRight,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import { Conflict, ConflictStatus } from '@/lib/api/brds'
import { requirementToSectionKey } from '@/lib/utils/sectionMapping'

interface ConflictPanelProps {
  conflicts: Conflict[]
  onResolveWithAI?: (conflict: Conflict) => void
  onNavigateToSection?: (sectionKey: string) => void
  onStatusChange?: (conflictId: string, status: ConflictStatus) => void
  conflictStatuses?: Record<string, ConflictStatus>
}

const STATUS_CONFIG: Record<ConflictStatus, { label: string; icon: typeof Circle; color: string }> = {
  open: { label: 'Open', icon: Circle, color: 'text-amber-500' },
  resolved: { label: 'Resolved', icon: CheckCircle2, color: 'text-green-500' },
  accepted: { label: 'Accepted', icon: Clock, color: 'text-blue-500' },
  deferred: { label: 'Deferred', icon: MinusCircle, color: 'text-muted-foreground' },
}

const ALL_STATUSES: ConflictStatus[] = ['open', 'resolved', 'accepted', 'deferred']

function getSeverityColor(severity: string) {
  switch (severity) {
    case 'high':
      return 'bg-red-500/10 text-red-500 border-red-500/20'
    case 'medium':
      return 'bg-amber-500/10 text-amber-500 border-amber-500/20'
    case 'low':
      return 'bg-blue-500/10 text-blue-500 border-blue-500/20'
    default:
      return 'bg-muted text-muted-foreground'
  }
}

export function ConflictPanel({
  conflicts,
  onResolveWithAI,
  onNavigateToSection,
  onStatusChange,
  conflictStatuses = {},
}: ConflictPanelProps) {
  const [expanded, setExpanded] = useState(false)

  if (!conflicts || conflicts.length === 0) {
    return null
  }

  // Build summary counts
  const statusCounts = conflicts.reduce(
    (acc, c) => {
      const status = conflictStatuses[c.id] || 'open'
      acc[status] = (acc[status] || 0) + 1
      return acc
    },
    {} as Record<string, number>
  )

  const summaryParts = ALL_STATUSES
    .filter((s) => statusCounts[s])
    .map((s) => `${statusCounts[s]} ${STATUS_CONFIG[s].label}`)

  const openCount = statusCounts['open'] || 0
  const allResolved = openCount === 0

  return (
    <Card className={allResolved
      ? 'border-emerald-500/20 bg-emerald-500/5'
      : 'border-amber-500/20 bg-amber-500/5'
    }>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className={`flex items-center gap-2 ${
            allResolved
              ? 'text-emerald-600 dark:text-emerald-500'
              : 'text-amber-600 dark:text-amber-500'
          }`}>
            {allResolved
              ? <CheckCircle2 className="h-5 w-5" />
              : <AlertTriangle className="h-5 w-5" />
            }
            <span>
              {conflicts.length} Conflict{conflicts.length > 1 ? 's' : ''}
              {summaryParts.length > 0 && (
                <span className="text-sm font-normal text-muted-foreground ml-2">
                  ({summaryParts.join(', ')})
                </span>
              )}
            </span>
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <>
                <ChevronUp className="h-4 w-4 mr-2" />
                Collapse
              </>
            ) : (
              <>
                <ChevronDown className="h-4 w-4 mr-2" />
                Expand
              </>
            )}
          </Button>
        </div>
      </CardHeader>

      {expanded && (
        <CardContent className="space-y-4 max-h-[40vh] overflow-y-auto">
          {conflicts.map((conflict) => {
            const currentStatus = conflictStatuses[conflict.id] || 'open'
            const statusConfig = STATUS_CONFIG[currentStatus]
            const StatusIcon = statusConfig.icon
            const isResolved = currentStatus === 'resolved' || currentStatus === 'accepted' || currentStatus === 'deferred'

            return (
              <div
                key={conflict.id}
                className={`border rounded-lg p-4 bg-card space-y-3 transition-opacity ${
                  isResolved ? 'opacity-60' : ''
                }`}
              >
                {/* Header row: severity + type + status + resolve button */}
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge className={getSeverityColor(conflict.severity)}>
                    {conflict.severity.toUpperCase()}
                  </Badge>
                  <span className="text-xs text-muted-foreground capitalize">
                    {conflict.conflict_type.replace(/_/g, ' ')}
                  </span>

                  <div className="ml-auto flex items-center gap-2">
                    {/* Status dropdown */}
                    {onStatusChange && (
                      <StatusDropdown
                        currentStatus={currentStatus}
                        onStatusChange={(status) => onStatusChange(conflict.id, status)}
                      />
                    )}

                    {/* Resolve with AI button */}
                    {onResolveWithAI && currentStatus === 'open' && (
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-1.5 text-xs h-7"
                        onClick={() => onResolveWithAI(conflict)}
                      >
                        <Sparkles className="h-3.5 w-3.5" />
                        Resolve with AI
                      </Button>
                    )}
                  </div>
                </div>

                <p className="text-sm leading-relaxed">{conflict.description}</p>

                {/* Affected requirements — clickable when mappable */}
                {conflict.affected_requirements.length > 0 && (
                  <div className="pt-3 border-t">
                    <p className="text-xs font-medium text-muted-foreground mb-2">
                      Affected Requirements
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {conflict.affected_requirements.map((req) => {
                        const sectionKey = requirementToSectionKey(req)
                        if (sectionKey && onNavigateToSection) {
                          return (
                            <Badge
                              key={req}
                              variant="outline"
                              className="text-xs font-mono cursor-pointer hover:bg-accent transition-colors gap-1"
                              onClick={() => onNavigateToSection(sectionKey)}
                            >
                              {req}
                              <ArrowRight className="h-3 w-3" />
                            </Badge>
                          )
                        }
                        return (
                          <Badge key={req} variant="outline" className="text-xs font-mono">
                            {req}
                          </Badge>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </CardContent>
      )}
    </Card>
  )
}

/** Popover dropdown for conflict status selection */
function StatusDropdown({
  currentStatus,
  onStatusChange,
}: {
  currentStatus: ConflictStatus
  onStatusChange: (status: ConflictStatus) => void
}) {
  const [open, setOpen] = useState(false)
  const config = STATUS_CONFIG[currentStatus]
  const Icon = config.icon

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-1.5 text-xs h-7 px-2">
          <Icon className={`h-3.5 w-3.5 ${config.color}`} />
          {config.label}
          <ChevronDown className="h-3 w-3 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-36 p-1" align="end">
        {ALL_STATUSES.map((status) => {
          const sc = STATUS_CONFIG[status]
          const StatusIcon = sc.icon
          return (
            <Button
              key={status}
              variant="ghost"
              size="sm"
              className={`w-full justify-start gap-2 text-xs h-8 ${
                status === currentStatus ? 'bg-accent' : ''
              }`}
              onClick={() => {
                onStatusChange(status)
                setOpen(false)
              }}
            >
              <StatusIcon className={`h-3.5 w-3.5 ${sc.color}`} />
              {sc.label}
            </Button>
          )
        })}
      </PopoverContent>
    </Popover>
  )
}
