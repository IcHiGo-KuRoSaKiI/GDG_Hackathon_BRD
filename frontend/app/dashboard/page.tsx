'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import { ProjectCard } from '@/components/projects/ProjectCard'
import { CreateProjectModal } from '@/components/projects/CreateProjectModal'
import { getProjects } from '@/lib/api/projects'
import { Project } from '@/lib/api/projects'

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

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

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Your Projects</h1>
        <p className="text-muted-foreground">
          Manage your BRD generation projects
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
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
              key={project.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <ProjectCard project={project} />
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
    </div>
  )
}
