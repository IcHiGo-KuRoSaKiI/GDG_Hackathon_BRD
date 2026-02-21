'use client'

import { useEffect, useRef, useState } from 'react'
import { Pencil } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { useToast } from '@/hooks/use-toast'
import { updateProject, Project } from '@/lib/api/projects'

interface EditableProjectHeaderProps {
  project: Project
  onUpdate: (updated: Project) => void
}

export function EditableProjectHeader({ project, onUpdate }: EditableProjectHeaderProps) {
  // Name editing
  const [isEditingName, setIsEditingName] = useState(false)
  const [nameValue, setNameValue] = useState(project.name)
  const [originalName, setOriginalName] = useState(project.name)
  const nameInputRef = useRef<HTMLInputElement>(null)

  // Description editing
  const [isEditingDesc, setIsEditingDesc] = useState(false)
  const [descValue, setDescValue] = useState(project.description || '')
  const [originalDesc, setOriginalDesc] = useState(project.description || '')
  const descInputRef = useRef<HTMLInputElement>(null)

  const { toast } = useToast()

  // Sync if project changes externally
  useEffect(() => {
    setNameValue(project.name)
    setOriginalName(project.name)
    setDescValue(project.description || '')
    setOriginalDesc(project.description || '')
  }, [project.name, project.description])

  // Auto-focus + select on edit
  useEffect(() => {
    if (isEditingName && nameInputRef.current) {
      nameInputRef.current.focus()
      nameInputRef.current.select()
    }
  }, [isEditingName])

  useEffect(() => {
    if (isEditingDesc && descInputRef.current) {
      descInputRef.current.focus()
      descInputRef.current.select()
    }
  }, [isEditingDesc])

  const saveName = async () => {
    const trimmed = nameValue.trim()
    if (!trimmed) {
      setNameValue(originalName)
      setIsEditingName(false)
      return
    }
    if (trimmed === originalName) {
      setIsEditingName(false)
      return
    }

    // Optimistic update
    setOriginalName(trimmed)
    setNameValue(trimmed)
    setIsEditingName(false)

    try {
      const updated = await updateProject(project.project_id, { name: trimmed })
      onUpdate(updated)
    } catch {
      setNameValue(originalName)
      setOriginalName(originalName)
      toast({ title: 'Failed to rename project', variant: 'destructive' })
    }
  }

  const saveDesc = async () => {
    const trimmed = descValue.trim()
    if (trimmed === originalDesc) {
      setIsEditingDesc(false)
      return
    }

    setOriginalDesc(trimmed)
    setDescValue(trimmed)
    setIsEditingDesc(false)

    try {
      const updated = await updateProject(project.project_id, { description: trimmed || undefined })
      onUpdate(updated)
    } catch {
      setDescValue(originalDesc)
      setOriginalDesc(originalDesc)
      toast({ title: 'Failed to update description', variant: 'destructive' })
    }
  }

  const handleNameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') saveName()
    if (e.key === 'Escape') {
      setNameValue(originalName)
      setIsEditingName(false)
    }
  }

  const handleDescKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') saveDesc()
    if (e.key === 'Escape') {
      setDescValue(originalDesc)
      setIsEditingDesc(false)
    }
  }

  return (
    <div>
      {/* Project Name */}
      <div className="group">
        {isEditingName ? (
          <Input
            ref={nameInputRef}
            value={nameValue}
            onChange={(e) => setNameValue(e.target.value.slice(0, 200))}
            onBlur={saveName}
            onKeyDown={handleNameKeyDown}
            maxLength={200}
            className="text-2xl md:text-3xl font-bold
              border-transparent bg-transparent px-0 h-auto py-0 mb-2
              focus-visible:ring-0 focus-visible:ring-offset-0
              focus-visible:border-b-2 focus-visible:border-primary
              focus-visible:rounded-none transition-colors"
          />
        ) : (
          <div
            className="flex items-center gap-2 cursor-pointer"
            onClick={() => setIsEditingName(true)}
          >
            <h1 className="text-2xl md:text-3xl font-bold mb-2">
              {nameValue}
            </h1>
            <Pencil className="h-4 w-4 text-muted-foreground shrink-0 mb-2
              opacity-50 md:opacity-0 md:group-hover:opacity-100
              transition-opacity" />
          </div>
        )}
      </div>

      {/* Description */}
      <div className="group">
        {isEditingDesc ? (
          <Input
            ref={descInputRef}
            value={descValue}
            onChange={(e) => setDescValue(e.target.value)}
            onBlur={saveDesc}
            onKeyDown={handleDescKeyDown}
            placeholder="Add a description..."
            className="text-sm text-muted-foreground
              border-transparent bg-transparent px-0 h-auto py-0
              focus-visible:ring-0 focus-visible:ring-offset-0
              focus-visible:border-b focus-visible:border-primary/50
              focus-visible:rounded-none transition-colors"
          />
        ) : (
          <div
            className="flex items-center gap-1.5 cursor-pointer"
            onClick={() => setIsEditingDesc(true)}
          >
            <p className="text-muted-foreground text-sm">
              {descValue || 'Add a description...'}
            </p>
            <Pencil className="h-3 w-3 text-muted-foreground shrink-0
              opacity-0 group-hover:opacity-50
              transition-opacity" />
          </div>
        )}
      </div>
    </div>
  )
}
