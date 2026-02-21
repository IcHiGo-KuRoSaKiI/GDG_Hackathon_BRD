'use client'

import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface Section {
  key: string
  label: string
}

const SECTIONS: Section[] = [
  { key: 'executive_summary', label: 'Executive Summary' },
  { key: 'project_background', label: 'Project Background' },
  { key: 'business_objectives', label: 'Business Objectives' },
  { key: 'stakeholders', label: 'Stakeholders' },
  { key: 'project_scope', label: 'Scope' },
  { key: 'functional_requirements', label: 'Functional Requirements' },
  { key: 'non_functional_requirements', label: 'Non-Functional Requirements' },
  { key: 'user_stories', label: 'User Stories' },
  { key: 'data_requirements', label: 'Data Requirements' },
  { key: 'integration_requirements', label: 'Integration Requirements' },
  { key: 'security_requirements', label: 'Security Requirements' },
  { key: 'assumptions', label: 'Assumptions' },
  { key: 'constraints', label: 'Constraints' },
  { key: 'success_metrics', label: 'Success Metrics' },
  { key: 'timeline', label: 'Timeline' },
  { key: 'dependencies', label: 'Dependencies' },
  { key: 'risks', label: 'Risks' },
  { key: 'cost_benefit', label: 'Cost-Benefit Analysis' },
]

interface BRDSectionTabsProps {
  activeSection: string
  onSectionChange: (section: string) => void
  availableSections: string[]
}

export function BRDSectionTabs({
  activeSection,
  onSectionChange,
  availableSections,
}: BRDSectionTabsProps) {
  return (
    <Tabs value={activeSection} onValueChange={onSectionChange}>
      <TabsList className="w-full justify-start overflow-x-auto flex-nowrap h-auto">
        {SECTIONS.filter((section) => availableSections.includes(section.key)).map((section) => (
          <TabsTrigger
            key={section.key}
            value={section.key}
            className="whitespace-nowrap text-xs md:text-sm"
          >
            {section.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  )
}
