# Integration Spec

## Overview

Connect the MCP App UI to the existing Python MCP server tools, handle communication between the TypeScript server and Python server, and ensure smooth data flow throughout the wizard.

## Requirements

### Python Server Communication

1. **Architecture options**

   **Option A: HTTP Proxy (Recommended)**
   ```
   UI ──postMessage──> TS Server ──HTTP──> Python Server
   ```
   - TypeScript server proxies tool calls to Python server via HTTP
   - Python server already supports HTTP transport
   - Clean separation of concerns

   **Option B: Subprocess**
   ```
   UI ──postMessage──> TS Server ──subprocess──> Python CLI
   ```
   - TypeScript server spawns Python process for each tool call
   - Simpler but slower

2. **HTTP Proxy implementation**
   ```typescript
   // mcp-app/src/proxy.ts
   import { spawn } from "child_process";

   let pythonServerProcess: ChildProcess | null = null;
   const PYTHON_SERVER_PORT = 3001;

   export async function startPythonServer(): Promise<void> {
     if (pythonServerProcess) return;

     pythonServerProcess = spawn("uvx", ["airflow-unfactor"], {
       env: { ...process.env, PORT: String(PYTHON_SERVER_PORT) }
     });

     // Wait for server to be ready
     await waitForServer(`http://localhost:${PYTHON_SERVER_PORT}/health`);
   }

   export async function callPythonTool(
     toolName: string,
     args: Record<string, unknown>
   ): Promise<unknown> {
     const response = await fetch(`http://localhost:${PYTHON_SERVER_PORT}/mcp`, {
       method: "POST",
       headers: { "Content-Type": "application/json" },
       body: JSON.stringify({
         jsonrpc: "2.0",
         method: "tools/call",
         params: { name: toolName, arguments: args },
         id: Date.now()
       })
     });

     const result = await response.json();
     if (result.error) throw new Error(result.error.message);
     return result.result;
   }
   ```

3. **Tool mapping**
   | UI Tool | Python Tool | Description |
   |---------|-------------|-------------|
   | `wizard/analyze` | `analyze` | Analyze DAG files |
   | `wizard/convert` | `convert` | Convert DAG to flow |
   | `wizard/validate` | `validate` | Validate conversion |
   | `wizard/scaffold` | `scaffold` | Generate project |
   | `wizard/batch` | `batch` | Batch convert |

### Data Flow

1. **Step 1 → Step 2: DAG Selection to Analysis**
   ```typescript
   // User selects DAGs and clicks "Analyze"
   const dags = state.selectedDags;

   // Call analyze for each DAG (parallel)
   const analyses = await Promise.all(
     dags.map(dag => mcpClient.analyzeDag(dag))
   );

   // Update state with results
   dispatch({ type: 'SET_ANALYSES', analyses: new Map(
     analyses.map(a => [a.dagId, a])
   )});
   ```

2. **Step 3 → Step 4: Configuration to Conversion**
   ```typescript
   // Get configuration
   const options = state.conversionOptions;

   // Convert each DAG sequentially (for progress tracking)
   for (const [index, dag] of state.selectedDags.entries()) {
     dispatch({ type: 'SET_CONVERSION_PROGRESS', progress: (index / total) * 50 });

     const result = await mcpClient.convertDag(dag, options);
     dispatch({ type: 'SET_CONVERSION_RESULT', dagId: dag, result });
   }

   // Validate each conversion
   for (const [index, dag] of state.selectedDags.entries()) {
     dispatch({ type: 'SET_CONVERSION_PROGRESS', progress: 50 + (index / total) * 50 });

     const validation = await mcpClient.validateConversion(
       dag,
       state.conversions.get(dag)!.flowCode
     );
     dispatch({ type: 'SET_VALIDATION_RESULT', dagId: dag, result: validation });
   }
   ```

3. **Step 6 → Step 7: Deployment Config to Export**
   ```typescript
   // Generate project structure
   const projectConfig = {
     ...state.projectConfig,
     ...state.deploymentConfig,
     flows: Array.from(state.conversions.entries()).map(([id, conv]) => ({
       dagId: id,
       flowCode: conv.flowCode,
       testCode: conv.testCode,
       runbook: conv.runbook
     }))
   };

   const project = await mcpClient.scaffoldProject(projectConfig);
   dispatch({ type: 'SET_GENERATED_PROJECT', project });
   ```

### Error Handling

1. **Network errors**
   ```typescript
   try {
     const result = await mcpClient.analyzeDag(dag);
     // ...
   } catch (error) {
     if (error instanceof NetworkError) {
       toast.error("Failed to connect to server. Is airflow-unfactor running?");
       dispatch({ type: 'SET_STATUS', status: 'error', error: error.message });
     } else {
       throw error;
     }
   }
   ```

2. **Tool errors**
   ```typescript
   const result = await mcpClient.convertDag(dag, options);
   if (!result.success) {
     // Store error but continue with other DAGs
     dispatch({
       type: 'SET_CONVERSION_RESULT',
       dagId: dag,
       result: { ...result, error: result.error }
     });
   }
   ```

3. **Validation failures**
   - Show warning but allow proceeding
   - Display issues prominently
   - Require user acknowledgment for low confidence

### State Persistence

1. **Session storage**
   ```typescript
   // Save state on changes
   useEffect(() => {
     sessionStorage.setItem('wizard-state', JSON.stringify(state));
   }, [state]);

   // Restore on mount
   const initialState = useMemo(() => {
     const saved = sessionStorage.getItem('wizard-state');
     return saved ? JSON.parse(saved) : defaultState;
   }, []);
   ```

2. **Recovery handling**
   - Detect incomplete state
   - Offer to resume or start fresh
   - Clear stale data after successful export

### Testing

1. **Mock MCP client**
   ```typescript
   // mcp-app/src/lib/__mocks__/mcp.ts
   export const mockAnalyze = jest.fn().mockResolvedValue({
     dagId: 'test_dag',
     operators: [...],
     complexityScore: 75
   });

   export const mockConvert = jest.fn().mockResolvedValue({
     success: true,
     flowCode: '...',
     testCode: '...'
   });
   ```

2. **Integration test with basic-host**
   ```typescript
   describe('Migration Wizard Integration', () => {
     beforeAll(async () => {
       // Start Python server
       await startPythonServer();
       // Start TS server
       await startMcpAppServer();
     });

     it('completes full migration flow', async () => {
       // Use basic-host to test full flow
       const host = new BasicHost('http://localhost:3002/mcp');
       await host.connect();

       const result = await host.callTool('migration-wizard', {
         dags_directory: './test-dags'
       });

       // Verify UI resource returned
       expect(result.ui).toBeDefined();
     });
   });
   ```

### Startup Coordination

1. **Package scripts**
   ```json
   {
     "scripts": {
       "dev": "concurrently \"npm run dev:python\" \"npm run dev:ts\"",
       "dev:python": "uvx airflow-unfactor",
       "dev:ts": "tsx watch server.ts",
       "build": "vite build",
       "serve": "npm run build && tsx server.ts",
       "test": "vitest"
     }
   }
   ```

2. **Server coordination**
   - TypeScript server starts Python server as subprocess
   - Health check before accepting requests
   - Graceful shutdown of both servers

## Acceptance Criteria

- [ ] TypeScript server can start Python server
- [ ] Tool calls forwarded correctly
- [ ] Response parsing works for all tools
- [ ] Error handling covers network and tool errors
- [ ] Progress tracking updates correctly
- [ ] State persists across page refreshes
- [ ] Mock client enables unit testing
- [ ] Integration tests pass with real servers
