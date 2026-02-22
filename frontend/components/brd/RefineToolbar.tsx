'use client'

import { Sparkles, PenLine } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface RefineToolbarProps {
  position: { top: number; left: number }
  mode: 'refine' | 'generate'
  onRefine: () => void
}

export function RefineToolbar({ position, mode, onRefine }: RefineToolbarProps) {
  return (
    <div
      className="absolute z-50 animate-in fade-in slide-in-from-bottom-2 duration-150"
      style={{ top: position.top, left: position.left, transform: 'translateX(-50%)' }}
    >
      <Button
        size="sm"
        variant="secondary"
        className="border gap-1.5 text-xs font-medium"
        onClick={(e) => {
          e.stopPropagation()
          onRefine()
        }}
      >
        {mode === 'refine' ? (
          <>
            <Sparkles className="h-3.5 w-3.5" />
            Refine with AI
          </>
        ) : (
          <>
            <PenLine className="h-3.5 w-3.5" />
            Add Content
          </>
        )}
      </Button>
    </div>
  )
}
