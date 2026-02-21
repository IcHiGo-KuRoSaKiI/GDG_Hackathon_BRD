# BRD Generator - Frontend

Next.js 14 frontend for the BRD Generator. Features a full BRD viewer with inline AI-powered text refinement, conflict resolution, and document management.

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **UI Library:** shadcn/ui + Tailwind CSS
- **Language:** TypeScript
- **State:** Zustand (auth, theme)
- **Markdown:** react-markdown + remark-gfm
- **Deployment:** Vercel

## Local Development

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Set Up Environment Variables

```bash
cp .env.local.example .env.local
```

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend API URL (default: `http://localhost:8080`) |

### 3. Run Development Server

```bash
npm run dev
```

Server runs at http://localhost:3000

## Features

### Authentication
- JWT-based login/register with token refresh
- Protected routes with auth middleware

### Projects
- Create, view, and delete projects
- Project cards with document/BRD counts

### Document Management
- Drag-and-drop multi-file upload (PDF, DOCX, TXT, CSV, PPTX)
- Document viewer with metadata
- Duplicate detection via file hashing

### BRD Viewer
- 13-section tabbed viewer with markdown rendering (tables, lists, code)
- Citation badges linking back to source documents
- BRD generation progress dialog with polling

### AI Chat Panel
- Persistent sidebar chat for each BRD
- **Text refinement:** Select text in any BRD section, refine via chat
- **General Q&A:** Ask questions about the BRD or project
- **Trigger generation:** Request BRD generation from chat
- Conversation history with visual update indicators

### Conflict Resolution
- Conflict panel showing detected requirement conflicts
- Accept/reject resolution with status persistence
- Green/amber indicators based on resolution progress

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx                    # Root layout + providers
│   ├── page.tsx                      # Landing / redirect
│   ├── login/                        # Login page
│   ├── register/                     # Register page
│   ├── dashboard/                    # Dashboard
│   ├── projects/
│   │   └── [projectId]/
│   │       ├── page.tsx              # Project detail (docs + BRDs)
│   │       └── brds/[brdId]/
│   │           └── page.tsx          # BRD viewer + chat panel
│   └── settings/                     # User settings
├── components/
│   ├── brd/
│   │   ├── BRDListCard.tsx           # BRD card with conflict badges
│   │   ├── BRDSection.tsx            # Single section renderer
│   │   ├── BRDSectionTabs.tsx        # Tabbed section navigation
│   │   ├── CitationBadge.tsx         # Source citation badge
│   │   ├── ConflictPanel.tsx         # Conflict resolution UI
│   │   ├── RefineChatPanel.tsx       # AI chat sidebar
│   │   ├── RefineToolbar.tsx         # Text selection toolbar
│   │   ├── GenerationProgressDialog.tsx  # BRD generation progress
│   │   └── DeleteBRDDialog.tsx       # Delete confirmation
│   ├── documents/
│   │   ├── DocumentViewer.tsx        # Document list + viewer
│   │   └── DeleteDocumentDialog.tsx  # Delete confirmation
│   ├── layout/
│   │   └── Sidebar.tsx               # App sidebar navigation
│   ├── projects/
│   │   ├── ProjectCard.tsx           # Project card
│   │   ├── CreateProjectModal.tsx    # New project modal
│   │   └── DeleteProjectDialog.tsx   # Delete confirmation
│   └── ui/                           # shadcn/ui primitives
├── hooks/
│   ├── useRefineText.ts              # AI chat state machine
│   ├── useTextSelection.ts           # Text selection detection
│   └── use-toast.ts                  # Toast notifications
├── lib/
│   ├── api/
│   │   ├── client.ts                 # Axios instance + interceptors
│   │   ├── auth.ts                   # Auth API calls
│   │   ├── brds.ts                   # BRD API + transform layer
│   │   ├── documents.ts             # Document API calls
│   │   └── projects.ts              # Project API calls
│   ├── store/
│   │   ├── authStore.ts             # Zustand auth store
│   │   └── themeStore.ts            # Zustand theme store
│   ├── hooks/
│   │   └── useBRDPolling.ts         # BRD generation polling
│   └── utils/
│       ├── cn.ts                    # Tailwind class merge
│       ├── fileHash.ts              # Document dedup hashing
│       └── sectionMapping.ts        # BRD section key mapping
└── public/                          # Static assets
```

## Deployment (Vercel)

1. Import repo on [vercel.com/new](https://vercel.com/new)
2. Set **Root Directory** to `frontend`
3. Add env var: `NEXT_PUBLIC_API_URL` = your Cloud Run backend URL
4. Deploy

Auto-deploys on push to `main`.
