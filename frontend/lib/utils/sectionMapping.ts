/**
 * Maps affected_requirements strings (requirement IDs like "NFR-01" or
 * display names like "Functional Requirements") to BRD section keys.
 *
 * Used by ConflictPanel for section navigation — clicking a requirement
 * badge jumps to the corresponding BRD section tab.
 */

// Prefix-based mapping for requirement IDs like "FR-01", "NFR-02"
const PREFIX_MAP: Record<string, string> = {
  FR: 'functional_requirements',
  NFR: 'non_functional_requirements',
  SEC: 'non_functional_requirements',
  PERF: 'non_functional_requirements',
  BO: 'business_objectives',
  SM: 'success_metrics',
  TL: 'timeline',
  DEP: 'dependencies',
  RSK: 'risks',
}

// Substring-based mapping (case-insensitive) for display names
const SUBSTRING_MAP: [string, string][] = [
  ['executive summary', 'executive_summary'],
  ['business objective', 'business_objectives'],
  ['stakeholder', 'stakeholders'],
  ['project scope', 'project_scope'],
  ['scope', 'project_scope'],
  ['functional requirement', 'functional_requirements'],
  ['non-functional', 'non_functional_requirements'],
  ['non functional', 'non_functional_requirements'],
  ['assumption', 'assumptions'],
  ['success metric', 'success_metrics'],
  ['timeline', 'timeline'],
  ['project background', 'project_background'],
  ['background', 'project_background'],
  ['dependenc', 'dependencies'],
  ['risk', 'risks'],
  ['cost', 'cost_benefit'],
  ['benefit', 'cost_benefit'],
]

// All valid section keys (matching BRDSectionEnum on backend)
const VALID_KEYS = new Set([
  'executive_summary',
  'business_objectives',
  'stakeholders',
  'project_scope',
  'functional_requirements',
  'non_functional_requirements',
  'assumptions',
  'success_metrics',
  'timeline',
  'project_background',
  'dependencies',
  'risks',
  'cost_benefit',
])

export function requirementToSectionKey(requirement: string): string | null {
  const trimmed = requirement.trim()
  if (!trimmed) return null

  const lower = trimmed.toLowerCase()

  // 1. Direct section key match
  const asKey = lower.replace(/[\s-]+/g, '_')
  if (VALID_KEYS.has(asKey)) return asKey

  // 2. Prefix-based match (e.g., "NFR-01" → "non_functional_requirements")
  const prefix = trimmed.split('-')[0]?.toUpperCase()
  if (prefix && PREFIX_MAP[prefix]) return PREFIX_MAP[prefix]

  // 3. Substring match against known display names
  for (const [substr, sectionKey] of SUBSTRING_MAP) {
    if (lower.includes(substr)) return sectionKey
  }

  return null
}
