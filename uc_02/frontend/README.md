# ORCA — Frontend

A role-based prior authorization / claims management system built with React, TypeScript, Vite, and Tailwind CSS.

---

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173** in your browser.

---

## How It Works

1. **Open the app** — you land on a Role Select screen.
2. **Choose a role** — Hospital or Insurance. No login required.
3. **Hospital portal** lets you submit claims, upload documents, track status, and manage resubmissions.
4. **Insurance portal** lets you review incoming claims, check policy evidence, render decisions (Accept / Reject / More Info / Human Review), and manage the human review queue.

---

## Project Structure

```
src/
├── context/       # RoleContext — stores selected role (hospital/insurance)
├── mock/          # All sample data — never imported by pages/components
├── services/      # API layer — swap these to connect a real backend
├── types/         # TypeScript types for claims, decisions, etc.
├── components/
│   ├── common/    # Shared UI (Sidebar, Header, StatusBadge, etc.)
│   ├── shared/    # Claim-detail building blocks (PolicyEvidencePanel, ClaimTimeline, etc.)
│   ├── hospital/  # Hospital-specific components (ClaimForm, ResubmissionAnalysis, etc.)
│   └── insurance/ # Insurance-specific components (DecisionPanel, ReviewQueueTable, etc.)
└── pages/
    ├── hospital/  # Hospital pages
    └── insurance/ # Insurance pages
```

---

## Connecting a Real Backend

All mock data lives in `src/mock/`. The service files in `src/services/` read from those mocks.

**To point at a real API:**

1. Create a `.env` file in the `frontend/` folder:
   ```
   VITE_API_BASE_URL=https://your-api.example.com
   ```

2. In each `src/services/*Api.ts` file, replace the `mockRequest(...)` calls with `apiFetch(...)` from `src/services/api.ts`. For example:

   ```ts
   // Before (mock)
   return mockRequest(mockClaims);

   // After (real API)
   return apiFetch<Claim[]>('/api/claims');
   ```

3. No page or component code needs to change — the service files are the only integration boundary.

See `FRONTEND_API_CONTRACT.md` for the full list of endpoints, request/response shapes, and polling behavior.

---

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start the dev server (hot reload) |
| `npm run build` | Build for production |
| `npm run preview` | Preview the production build locally |
| `npm run lint` | Run the linter |

---

## Tech Stack

- **React 19** + **TypeScript**
- **Vite 8** (build tool)
- **Tailwind CSS 4** (styling)
- **React Router 7** (routing)
- **lucide-react** (icons)
- **react-dropzone** (file uploads)
- **recharts** (charts, available for future use)
