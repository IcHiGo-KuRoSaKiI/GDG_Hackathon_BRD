'use client'

import { useState } from 'react'
import { AlertTriangle, Loader2, Trash2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { BRD, deleteBRD } from '@/lib/api/brds'
import { getApiError } from '@/lib/utils/formatters'

interface DeleteBRDDialogProps {
  brd: BRD | null
  projectId: string
  open: boolean
  onClose: () => void
  onDeleted: () => void
}

export function DeleteBRDDialog({
  brd,
  projectId,
  open,
  onClose,
  onDeleted,
}: DeleteBRDDialogProps) {
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState('')

  const handleDelete = async () => {
    if (!brd?.id) return

    setDeleting(true)
    setError('')
    try {
      await deleteBRD(projectId, brd.id)
      onDeleted()
      handleClose()
    } catch (err: any) {
      setError(getApiError(err, 'Failed to delete BRD'))
    } finally {
      setDeleting(false)
    }
  }

  const handleClose = () => {
    if (!deleting) {
      setError('')
      onClose()
    }
  }

  const sectionCount = brd?.sections
    ? Object.keys(brd.sections).filter(
        (key) => brd.sections[key as keyof typeof brd.sections]?.content
      ).length
    : 0

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-destructive">
            <Trash2 className="h-5 w-5" />
            Delete BRD
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to delete this BRD?
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {error && (
            <div className="p-4 text-sm text-destructive bg-destructive/10 border border-destructive/20 mb-4">
              {error}
            </div>
          )}

          <div className="space-y-3">
            <div className="p-3 bg-muted">
              <p className="text-sm font-medium">
                BRD #{brd?.id?.slice(0, 8) || 'Unknown'}
              </p>
              {brd?.created_at && (
                <p className="text-xs text-muted-foreground mt-1">
                  Generated {new Date(brd.created_at).toLocaleDateString()}
                </p>
              )}
              {sectionCount > 0 && (
                <p className="text-xs text-muted-foreground">
                  {sectionCount} sections
                </p>
              )}
            </div>

            <div className="p-4 bg-amber-500/10 border border-amber-500/20">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-amber-600 dark:text-amber-500">
                    Warning
                  </p>
                  <p className="text-xs text-amber-600/80 dark:text-amber-500/80 mt-1">
                    This action cannot be undone. The BRD and all its content will be
                    permanently removed.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={deleting}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={deleting || !brd?.id}
          >
            {deleting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Deleting...
              </>
            ) : (
              <>
                <Trash2 className="h-4 w-4 mr-2" />
                Delete BRD
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
