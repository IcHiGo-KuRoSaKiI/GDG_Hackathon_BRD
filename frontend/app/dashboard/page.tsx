'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { ProjectCard } from '@/components/projects/ProjectCard'
import { CreateProjectModal } from '@/components/projects/CreateProjectModal'
import { DeleteProjectDialog } from '@/components/projects/DeleteProjectDialog'
import { Skeleton } from '@/components/ui/skeleton'
import { getProjects } from '@/lib/api/projects'
import { Project } from '@/lib/api/projects'

export default function DashboardPage() {
  const router = useRouter()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null)

  const loadProjects = async () => {
    try {
      setLoading(true)
      const data = await getProjects()
      setProjects(data)
      setError('')
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to load projects'
      if (errorMsg.includes('token') || errorMsg.includes('authenticated')) {
        setError('Your session has expired. Please logout and login again.')
      } else {
        setError(errorMsg)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProjects()
  }, [])

  const handleDeleteProject = (project: Project) => {
    setProjectToDelete(project)
    setDeleteDialogOpen(true)
  }

  const handleProjectDeleted = () => {
    loadProjects()
  }

  return (
    <div className="p-4 md:p-8">
      <div className="mb-6 md:mb-8">
        <h1 className="text-2xl md:text-3xl font-bold mb-2">Your Projects</h1>
        <p className="text-muted-foreground">
          Manage your BRD generation projects
        </p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-border p-6 space-y-4">
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-4 w-56" />
              <div className="flex gap-4 pt-2">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-20" />
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="space-y-4">
          <div className="p-4 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
            {error}
          </div>
          <div className="flex justify-center">
            <button
              onClick={() => {
                localStorage.clear()
                window.location.href = '/login'
              }}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              Go to Login
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project, index) => (
            <motion.div
              key={project.project_id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: Math.min(index * 0.06, 0.3) }}
            >
              <ProjectCard project={project} onDelete={handleDeleteProject} />
            </motion.div>
          ))}
          <CreateProjectModal onSuccess={loadProjects} />
        </div>
      )}

      {!loading && !error && projects.length === 0 && (
        <div className="text-center py-20">
          <p className="text-muted-foreground mb-4">No projects yet</p>
          <CreateProjectModal onSuccess={loadProjects} />
        </div>
      )}

      <DeleteProjectDialog
        project={projectToDelete}
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        onDeleted={handleProjectDeleted}
      />
    </div>
  )
}
