# AutoExpense Frontend

Next.js dashboard for AutoExpense receipt management.

## Getting Started

1. Install dependencies:
```bash
npm install
```

2. Configure environment variables:
```bash
cp .env.example .env.local
# Edit .env.local with your Supabase credentials
```

3. Run development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx       # Root layout
│   ├── page.tsx         # Home page
│   ├── login/           # Auth pages
│   ├── receipts/        # Receipt list & detail
│   └── export/          # Export functionality
├── components/          # Reusable components
├── lib/                 # Utilities & helpers
│   └── supabase.ts      # Supabase client
└── public/              # Static assets
```

## Features

- User authentication (Supabase Auth)
- Receipt list view
- Search & filtering
- Manual sync
- CSV export

## Tech Stack

- Next.js 15 (App Router)
- TypeScript
- Tailwind CSS
- Supabase (Auth & API)
