# Foundation Spec

## Overview

Set up the MCP App project structure with TypeScript, Vite, React, and shadcn. Create the MCP server with UI resource registration and basic wizard scaffolding.

## Requirements

### Project Setup

1. **Package configuration**
   - `package.json` with MCP SDK dependencies
   - TypeScript configuration for ESNext modules
   - Vite config with single-file bundling
   - React 18+ with TypeScript

2. **Dependencies**
   ```json
   {
     "dependencies": {
       "@modelcontextprotocol/sdk": "^1.0.0",
       "@modelcontextprotocol/ext-apps": "^1.0.0",
       "react": "^18.3.0",
       "react-dom": "^18.3.0"
     },
     "devDependencies": {
       "typescript": "^5.0.0",
       "vite": "^6.0.0",
       "vite-plugin-singlefile": "^2.0.0",
       "@types/react": "^18.3.0",
       "@types/react-dom": "^18.3.0",
       "tailwindcss": "^3.4.0",
       "autoprefixer": "^10.0.0",
       "postcss": "^8.0.0"
     }
   }
   ```

### MCP Server

1. **Server entry point** (`server.ts`)
   - Initialize McpServer with name and version
   - Register `migration-wizard` tool with UI metadata
   - Register UI resource serving bundled HTML
   - Express server on configurable port (default 3002)
   - CORS enabled for development

2. **Tool registration**
   ```typescript
   registerAppTool(server, "migration-wizard", {
     title: "Airflow Migration Wizard",
     description: "Interactive wizard to migrate Airflow DAGs to Prefect flows",
     inputSchema: {
       type: "object",
       properties: {
         dags_directory: { type: "string" }
       }
     },
     _meta: { ui: { resourceUri: "ui://migration-wizard/app.html" } }
   }, handler);
   ```

3. **Proxy tools for Python server**
   - `wizard/analyze` — forwards to Python `analyze` tool
   - `wizard/convert` — forwards to Python `convert` tool
   - `wizard/validate` — forwards to Python `validate` tool
   - `wizard/scaffold` — forwards to Python `scaffold` tool

### shadcn Setup

1. **Initialize shadcn**
   - Configure with New York style
   - CSS variables for theming
   - Tailwind integration

2. **Core components to install**
   - `button`, `card`, `checkbox`, `input`, `label`
   - `progress`, `tabs`, `accordion`
   - `alert`, `alert-dialog`, `badge`
   - `select`, `radio-group`, `switch`
   - `separator`, `scroll-area`

### Wizard Scaffolding

1. **WizardProvider**
   - React context for wizard state
   - useReducer for state management
   - Step navigation logic
   - Validation before step transitions

2. **WizardNavigation**
   - Horizontal step indicator
   - Clickable completed steps
   - Current step highlight
   - Step labels and icons

3. **WizardStep wrapper**
   - Consistent card layout
   - Title and description
   - Back/Next button bar
   - Loading states

## Acceptance Criteria

- [ ] `npm install && npm run build` succeeds
- [ ] `npm run serve` starts MCP server on port 3002
- [ ] Server responds to MCP initialization
- [ ] `migration-wizard` tool registered with UI metadata
- [ ] UI resource returns bundled HTML
- [ ] Wizard renders with 7 step indicators
- [ ] Navigation between steps works
- [ ] shadcn components render correctly

## Files to Create

```
mcp-app/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── components.json          # shadcn config
├── server.ts
├── index.html
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css
    ├── lib/
    │   ├── utils.ts         # shadcn cn() helper
    │   └── mcp.ts           # MCP client wrapper
    ├── components/
    │   ├── ui/              # shadcn components
    │   └── wizard/
    │       ├── WizardProvider.tsx
    │       ├── WizardNavigation.tsx
    │       └── WizardStep.tsx
    ├── hooks/
    │   └── useWizard.ts
    └── types/
        └── index.ts
```
