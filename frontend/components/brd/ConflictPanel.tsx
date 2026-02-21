'use client'

import { AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Conflict } from '@/lib/api/brds'

interface ConflictPanelProps {
  conflicts: Conflict[]
}

export function ConflictPanel({ conflicts }: ConflictPanelProps) {
  const [expanded, setExpanded] = useState(false)

  if (!conflicts || conflicts.length === 0) {
    return null
  }

  const getSeverityColor = (severity: string) => {
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

  return (
    <Card className="border-amber-500/20 bg-amber-500/5">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-amber-600 dark:text-amber-500">
            <AlertTriangle className="h-5 w-5" />
            {conflicts.length} Requirement Conflict{conflicts.length > 1 ? 's' : ''} Detected
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
        <CardContent className="space-y-4">
          {conflicts.map((conflict) => (
            <div
              key={conflict.id}
              className="border rounded-lg p-4 bg-card space-y-3"
            >
              <div className="flex items-center gap-2 mb-2">
                <Badge className={getSeverityColor(conflict.severity)}>
                  {conflict.severity.toUpperCase()}
                </Badge>
                <span className="text-xs text-muted-foreground capitalize">
                  {conflict.conflict_type.replace(/_/g, ' ')}
                </span>
              </div>

              <p className="text-sm leading-relaxed">{conflict.description}</p>

              {conflict.affected_requirements.length > 0 && (
                <div className="pt-3 border-t">
                  <p className="text-xs font-medium text-muted-foreground mb-2">
                    Affected Requirements
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {conflict.affected_requirements.map((req) => (
                      <Badge key={req} variant="outline" className="text-xs font-mono">
                        {req}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </CardContent>
      )}
    </Card>
  )
}
