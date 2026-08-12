# frontend/

Next.js 14 application — chat interface, document management UI, and analytics dashboard.

**Planned Sprint:** Sprint 5

## Responsibilities

- Real-time chat interface with SSE token streaming
- Document upload and knowledge base management
- Session history and conversation management
- Authentication UI (login, register, logout)

## Structure (Sprint 5)

```
frontend/
├── app/                  # Next.js 14 App Router
│   ├── (auth)/           # Login, register pages
│   ├── (dashboard)/      # Chat, documents, settings
│   └── layout.tsx        # Root layout with providers
├── components/
│   ├── chat/             # ChatWindow, MessageBubble, InputBar
│   ├── documents/        # DocumentList, UploadModal
│   └── ui/               # Shared design system components
├── lib/
│   ├── api.ts            # Type-safe API client
│   └── store.ts          # Zustand client state
├── public/
├── package.json
└── .env.example
```

## Key Design Decisions

- **App Router** (Next.js 14) for React Server Components support
- **Zustand** for client state; **React Query** for server state
- **SSE** (`EventSource`) for streaming — no WebSocket complexity
- **shadcn/ui** component library on top of Tailwind CSS

> See [`docs/architecture.md`](../docs/architecture.md) for full component specification.
