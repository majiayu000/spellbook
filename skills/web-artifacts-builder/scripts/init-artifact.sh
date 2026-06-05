#!/usr/bin/env bash
set -euo pipefail

project_name="${1:-}"
if [[ -z "$project_name" ]]; then
  echo "usage: bash scripts/init-artifact.sh <project-name>" >&2
  exit 2
fi
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -e "$project_name" ]]; then
  echo "error: target already exists: $project_name" >&2
  exit 1
fi

mkdir -p "$project_name/src/components/ui"
cd "$project_name"

cat > package.json <<'JSON'
{
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "vite build",
    "bundle": "bash scripts/bundle-artifact.sh"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "autoprefixer": "^10.4.19",
    "clsx": "^2.1.1",
    "lucide-react": "^0.468.0",
    "postcss": "^8.4.38",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "tailwind-merge": "^2.3.0",
    "tailwindcss": "^3.4.1",
    "typescript": "^5.4.5",
    "vite": "^5.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.66",
    "@types/react-dom": "^18.2.22",
    "html-inline": "^1.2.0",
    "parcel": "^2.12.0"
  }
}
JSON

cat > index.html <<'HTML'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Claude Artifact</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
HTML

cat > src/main.tsx <<'TSX'
import React from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
TSX

cat > src/App.tsx <<'TSX'
export function App() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-50">
      <section className="mx-auto flex min-h-screen max-w-5xl flex-col justify-center px-8">
        <p className="mb-4 text-sm uppercase tracking-[0.2em] text-cyan-300">Claude Artifact</p>
        <h1 className="max-w-3xl text-5xl font-semibold leading-tight">
          Replace this starter with the user's actual interactive experience.
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-zinc-300">
          Use React state, focused components, and Tailwind utilities. Keep the final artifact
          self-contained by running the bundle script from the project root.
        </p>
      </section>
    </main>
  );
}
TSX

cat > src/index.css <<'CSS'
@tailwind base;
@tailwind components;
@tailwind utilities;

* {
  box-sizing: border-box;
}

body {
  margin: 0;
}
CSS

cat > src/components/ui/README.md <<'MD'
# UI Components

Put small reusable shadcn/ui-style components here. Keep component APIs narrow
and prefer plain Tailwind classes unless a reusable abstraction removes real
duplication.
MD

cat > tsconfig.json <<'JSON'
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "references": []
}
JSON

cat > vite.config.ts <<'TS'
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
});
TS

cat > tailwind.config.js <<'JS'
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};
JS

cat > postcss.config.js <<'JS'
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
JS

cat > .parcelrc <<'JSON'
{
  "extends": "@parcel/config-default"
}
JSON

mkdir -p scripts
cp "$script_dir/bundle-artifact.sh" scripts/bundle-artifact.sh
chmod +x scripts/bundle-artifact.sh

echo "Created artifact project: $project_name"
echo "Next: cd $project_name && npm install && npm run dev"
