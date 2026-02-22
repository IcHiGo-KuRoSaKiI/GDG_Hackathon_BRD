'use client'

import { useState, useEffect } from 'react'
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
import { Input } from '@/components/ui/input'
import {
  Project,
  previewProjectDeletion,
  confirmProjectDeletion,
  DeletePreviewResponse,
} from '@/lib/api/projects'
import { getApiError } from '@/lib/utils/formatters'

interface DeleteProjectDialogProps {
  project: Project | null
  open: boolean
  onClose: () => void
  onDeleted: () => void
}

export function DeleteProjectDialog({
  project,
  open,
  onClose,
  onDeleted,
}: DeleteProjectDialogProps) {
  const [confirmText, setConfirmText] = useState('')
  const [preview, setPreview] = useState<DeletePreviewResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (open && project) {
      loadPreview()
    }
  }, [open, project])

  const loadPreview = async () => {
    if (!project) return

    setLoading(true)
    setError('')
    try {
      const data = await previewProjectDeletion(project.project_id)
      setPreview(data)
    } catch (err: any) {
      setError(getApiError(err, 'Failed to prepare deletion'))
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!project || !preview || confirmText !== project.name) return

    setDeleting(true)
    setError('')
    try {
      await confirmProjectDeletion(project.project_id, preview.deletion_id)
      onDeleted()
      handleClose()
    } catch (err: any) {
      setError(getApiError(err, 'Failed to delete project'))
    } finally {
      setDeleting(false)
    }
  }

  const handleClose = () => {
    if (!deleting) {
      setConfirmText('')
      setPreview(null)
      setError('')
      onClose()
    }
  }

  const isConfirmValid = confirmText === project?.name

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-destructive">
            <Trash2 className="h-5 w-5" />
            Delete Project
          </DialogTitle>
          <DialogDescription>
            This action cannot be undone and will permanently delete all associated data.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {loading && (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          )}

          {error && (
            <div className="p-4 text-sm text-destructive bg-destructive/10 border border-destructive/20">
              {error}
            </div>
          )}

          {!loading && preview && (
            <>
              <div className="p-4 bg-amber-500/10 border border-amber-500/20">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-amber-600 dark:text-amber-500">
                      This will permanently delete:
                    </p>
                    <ul className="text-xs text-amber-600/80 dark:text-amber-500/80 space-y-1 list-disc list-inside">
                      <li>The project &ldquo;{project?.name}&rdquo;</li>
                      <li>{preview.documents_to_delete} document{preview.documents_to_delete !== 1 ? 's' : ''} and their metadata</li>
                      <li>{preview.brds_to_delete} generated BRD{preview.brds_to_delete !== 1 ? 's' : ''}</li>
                      <li>{preview.chunks_to_delete} text chunks</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">
                  To confirm, type the project name:{' '}
                  <span className="font-bold text-primary">{project?.name}</span>
                </label>
                <Input
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  placeholder="Enter project name"
                  disabled={deleting}
                  autoComplete="off"
                />
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={deleting}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={!isConfirmValid || deleting || loading || !preview}
          >
            {deleting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Deleting...
              </>
            ) : (
              <>
                <Trash2 className="h-4 w-4 mr-2" />
                Delete Project
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
