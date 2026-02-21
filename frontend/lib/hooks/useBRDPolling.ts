import { useEffect, useState, useRef, useCallback } from 'react'
import { getBRDs, BRD } from '@/lib/api/brds'

interface UseBRDPollingOptions {
  projectId: string
  enabled: boolean
  onComplete?: (brd: BRD) => void
}

/**
 * Polls for BRD completion by detecting when a new BRD appears in the list.
 *
 * Since the backend only stores BRDs after generation finishes, the detection
 * strategy is: capture the set of known BRD IDs when polling starts, then
 * on each poll check if a new ID has appeared.
 */
export function useBRDPolling({ projectId, enabled, onComplete }: UseBRDPollingOptions) {
  const [brds, setBRDs] = useState<BRD[]>([])
  const [progress, setProgress] = useState(0)
  const [stage, setStage] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  const knownIdsRef = useRef<Set<string> | null>(null)
  const startTime = useRef<number>(Date.now())
  const onCompleteRef = useRef(onComplete)
  onCompleteRef.current = onComplete

  // Capture known BRD IDs once when polling is enabled
  const initKnownIds = useCallback(async () => {
    try {
      const data = await getBRDs(projectId)
      knownIdsRef.current = new Set(data.map((b) => b.id))
      setBRDs(data)
    } catch {
      knownIdsRef.current = new Set()
    }
  }, [projectId])

  useEffect(() => {
    if (!enabled) {
      knownIdsRef.current = null
      return
    }

    startTime.current = Date.now()
    setProgress(0)

    // First, snapshot the existing BRDs
    initKnownIds()

    const pollInterval = setInterval(async () => {
      // Don't poll until initial snapshot is taken
      if (!knownIdsRef.current) return

      try {
        const data = await getBRDs(projectId)
        setBRDs(data)

        // Detect a newly appeared BRD (ID not in our initial snapshot)
        const newBRD = data.find((brd) => !knownIdsRef.current!.has(brd.id))

        if (newBRD) {
          setProgress(100)
          setStage('Complete')
          onCompleteRef.current?.(newBRD)
          clearInterval(pollInterval)
          return
        }

        // Time-based progress estimation
        const elapsed = Date.now() - startTime.current
        const baseProgress = 30
        const timeBasedProgress = Math.min(95, baseProgress + (elapsed / 30000) * 65)
        setProgress(Math.floor(timeBasedProgress))
      } catch (err: any) {
        setError(err.message)
        // Continue polling even on error
      }
    }, 2000)

    return () => clearInterval(pollInterval)
  }, [enabled, projectId, initKnownIds])

  return { brds, progress, stage, error }
}
