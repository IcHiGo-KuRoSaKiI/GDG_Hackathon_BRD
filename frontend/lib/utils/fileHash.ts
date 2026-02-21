/**
 * Calculate SHA-256 hash of a file using Web Crypto API
 */
export async function calculateFileHash(file: File): Promise<string> {
  const buffer = await file.arrayBuffer()
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
}

/**
 * Extract hash from storage path (assuming format: uploads/{projectId}/{hash}_{filename})
 */
export function extractHashFromPath(storagePath: string): string | null {
  const parts = storagePath.split('/')
  const filename = parts[parts.length - 1]
  const hashMatch = filename.match(/^([a-f0-9]{64})_/)
  return hashMatch ? hashMatch[1] : null
}
