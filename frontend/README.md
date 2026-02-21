# BRD Generator - Frontend

Next.js frontend for the BRD Generator system.

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **UI Library:** Shadcn UI + Tailwind CSS
- **Language:** TypeScript
- **Deployment:** Vercel

## Local Development

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env.local
# Edit .env.local with your backend API URL
```

### 3. Run Development Server

```bash
npm run dev
```

Server runs at: http://localhost:3000

## Deployment to Vercel

### Via Vercel CLI

```bash
npm install -g vercel
vercel
```

### Via GitHub Integration

1. Push to GitHub
2. Connect repo to Vercel
3. Set Root Directory: `frontend`
4. Deploy automatically on push

## Project Structure (Planned)

```
frontend/
├── app/                # Next.js 14 App Router
│   ├── page.tsx       # Home page
│   ├── layout.tsx     # Root layout
│   ├── projects/      # Projects pages
│   └── brds/          # BRD pages
├── components/        # React components
├── lib/              # Utilities
├── public/           # Static assets
└── styles/           # Global styles
```

## Features

- Upload documents (drag & drop)
- View document metadata
- Generate BRD
- View BRD with citations
- Conflict resolution UI
- Sentiment dashboard
