'use client'

import { ExternalLink } from 'lucide-react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Button } from '@/components/ui/button'

interface Citation {
  id: string
  text: string
  source: string
  document_id: string
}

interface CitationBadgeProps {
  citation: Citation
  onViewDocument?: (documentId: string) => void
}

export function CitationBadge({ citation, onViewDocument }: CitationBadgeProps) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <span className="inline-flex items-center text-xs px-1.5 py-0.5 bg-primary/10 text-primary rounded cursor-pointer hover:bg-primary/20 transition-colors">
          [{citation.id}]
        </span>
      </PopoverTrigger>
      <PopoverContent className="w-80">
        <div className="space-y-3">
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1">Source</p>
            <p className="text-sm font-medium">{citation.source}</p>
          </div>

          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1">Excerpt</p>
            <p className="text-sm text-muted-foreground leading-relaxed">
              "{citation.text}"
            </p>
          </div>

          {onViewDocument && (
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={() => onViewDocument(citation.document_id)}
            >
              <ExternalLink className="h-3 w-3 mr-2" />
              View Document
            </Button>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}
