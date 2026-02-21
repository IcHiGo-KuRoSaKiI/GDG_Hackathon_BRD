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
import {
  Document,
  previewDocumentDeletion,
  deleteDocument,
  DeletePreviewResponse,
} from '@/lib/api/documents'

interface DeleteDocumentDialogProps {
  document: Document | null
  projectId: string
  open: boolean
  onClose: () => void
  onDeleted: () => void
}

export function DeleteDocumentDialog({
  document,
  projectId,
  open,
  onClose,
  onDeleted,
}: DeleteDocumentDialogProps) {
  const [preview, setPreview] = useState<DeletePreviewResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (open && document) {
      loadPreview()
    }
  }, [open, document])

  const loadPreview = async () => {
    if (!document) return

    setLoading(true)
    setError('')
    try {
      const data = await previewDocumentDeletion(projectId, document.doc_id)
      setPreview(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load deletion preview')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!document) return

    setDeleting(true)
    setError('')
    try {
      await deleteDocument(projectId, document.doc_id)
      onDeleted()
      onClose()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete document')
    } finally {
      setDeleting(false)
    }
  }

  const handleClose = () => {
    if (!deleting) {
      setPreview(null)
      setError('')
      onClose()
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-destructive">
            <Trash2 className="h-5 w-5" />
            Delete Document
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to delete this document?
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          )}

          {error && (
            <div className="p-4 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md mb-4">
              {error}
            </div>
          )}

          {!loading && preview && (
            <>
              <div className="space-y-3">
                <div className="p-3 bg-muted rounded-md">
                  <p className="text-sm font-medium">{document?.filename}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {document?.chomper_metadata?.word_count || 0} words •{' '}
                    {document?.ai_metadata?.document_type || 'Unknown'}
                  </p>
                </div>

                {preview.brd_ids_to_delete.length > 0 && (
                  <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-md">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-amber-600 dark:text-amber-500">
                          Warning: This will affect {preview.brd_ids_to_delete.length} BRD
                          {preview.brd_ids_to_delete.length > 1 ? 's' : ''}
                        </p>
                        <p className="text-xs text-amber-600/80 dark:text-amber-500/80 mt-1">
                          {preview.warning_message}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                <p className="text-sm text-muted-foreground">
                  This action cannot be undone. The document and all its metadata will be
                  permanently removed.
                </p>
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
            disabled={loading || deleting}
          >
            {deleting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Deleting...
              </>
            ) : (
              <>
                <Trash2 className="h-4 w-4 mr-2" />
                Delete Document
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
