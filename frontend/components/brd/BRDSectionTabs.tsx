'use client'

import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface Section {
  key: string
  label: string
}

const SECTIONS: Section[] = [
  { key: 'executive_summary', label: 'Executive Summary' },
  { key: 'business_objectives', label: 'Business Objectives' },
  { key: 'stakeholders', label: 'Stakeholders' },
  { key: 'scope', label: 'Scope' },
  { key: 'functional_requirements', label: 'Functional Requirements' },
  { key: 'non_functional_requirements', label: 'Non-Functional Requirements' },
  { key: 'user_stories', label: 'User Stories' },
  { key: 'data_requirements', label: 'Data Requirements' },
  { key: 'integration_requirements', label: 'Integration Requirements' },
  { key: 'security_requirements', label: 'Security Requirements' },
  { key: 'assumptions', label: 'Assumptions' },
  { key: 'constraints', label: 'Constraints' },
  { key: 'risks', label: 'Risks' },
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
            className="whitespace-nowrap"
          >
            {section.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  )
}
