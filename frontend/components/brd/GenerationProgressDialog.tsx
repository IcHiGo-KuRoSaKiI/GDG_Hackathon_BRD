'use client'

import { CheckCircle, Clock, Loader2, Sparkles } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Progress } from '@/components/ui/progress'

interface GenerationProgressDialogProps {
  open: boolean
  documentCount: number
  progress: number
  stage?: string
}

export function GenerationProgressDialog({
  open,
  documentCount,
  progress,
  stage,
}: GenerationProgressDialogProps) {
  return (
    <Dialog open={open}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Generating BRD...
          </DialogTitle>
          <DialogDescription>
            AI is analyzing your documents and generating requirements
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="flex items-center gap-2 text-sm">
            <CheckCircle className="h-4 w-4 text-emerald-500" />
            <span>Analyzed {documentCount} document{documentCount > 1 ? 's' : ''}</span>
          </div>

          <div className="flex items-center gap-2 text-sm">
            {progress >= 50 ? (
              <CheckCircle className="h-4 w-4 text-emerald-500" />
            ) : (
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
            )}
            <span>Extracting requirements...</span>
          </div>

          <div className="flex items-center gap-2 text-sm">
            {progress >= 80 ? (
              <CheckCircle className="h-4 w-4 text-emerald-500" />
            ) : (
              <Clock className="h-4 w-4 text-muted-foreground" />
            )}
            <span>Detecting conflicts...</span>
          </div>

          <div className="flex items-center gap-2 text-sm">
            {progress >= 95 ? (
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
            ) : (
              <Clock className="h-4 w-4 text-muted-foreground" />
            )}
            <span>Finalizing BRD...</span>
          </div>

          <div className="pt-2">
            <Progress value={progress} className="h-2" />
          </div>

          {stage && (
            <p className="text-xs text-muted-foreground text-center">
              {stage}
            </p>
          )}

          <p className="text-xs text-muted-foreground text-center">
            This usually takes 20-30 seconds
          </p>
        </div>
      </DialogContent>
    </Dialog>
  )
}
