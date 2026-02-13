import { useState } from "react";
import { useWizard } from "../WizardProvider";
import { WizardStep } from "../WizardStep";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FolderOpen, Search, FileCode } from "lucide-react";
import type { DagFile } from "@/types";
import * as mcp from "@/lib/mcp";

// Mock data for standalone testing
const mockDagFiles: DagFile[] = [
  { path: "/dags/etl_daily.py", name: "etl_daily.py", complexity: "simple", selected: false },
  { path: "/dags/ml_training.py", name: "ml_training.py", complexity: "medium", selected: false },
  { path: "/dags/data_pipeline.py", name: "data_pipeline.py", complexity: "simple", selected: false },
  { path: "/dags/complex_workflow.py", name: "complex_workflow.py", complexity: "complex", selected: false },
  { path: "/dags/analytics_job.py", name: "analytics_job.py", complexity: "medium", selected: false },
];

export function DagSelector() {
  const { state, dispatch } = useWizard();
  const [searchFilter, setSearchFilter] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Use mock data if no dag files loaded
  const dagFiles = state.dagFiles.length > 0 ? state.dagFiles : mockDagFiles;

  const filteredDags = dagFiles.filter((dag) =>
    dag.name.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const handleDirectoryChange = (directory: string) => {
    dispatch({ type: "SET_DAGS_DIRECTORY", directory });
  };

  const handleScan = async () => {
    setIsLoading(true);
    try {
      if (mcp.isMcpAppContext()) {
        // Call MCP tool to list DAGs
        const files = await mcp.listDagFiles(state.dagsDirectory);
        const dagFiles: DagFile[] = files.map((f) => ({
          path: f.path,
          name: f.name,
          complexity: "medium", // Will be determined by analysis
          selected: false,
        }));
        dispatch({ type: "SET_DAG_FILES", files: dagFiles });
      } else {
        // Use mock data for standalone testing
        await new Promise((resolve) => setTimeout(resolve, 500));
        dispatch({ type: "SET_DAG_FILES", files: mockDagFiles });
      }
    } catch (error) {
      console.error("Failed to scan DAGs:", error);
      // Fall back to mock data on error
      dispatch({ type: "SET_DAG_FILES", files: mockDagFiles });
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleDag = (path: string) => {
    dispatch({ type: "TOGGLE_DAG", path });
  };

  const handleSelectAll = () => {
    const allPaths = filteredDags.map((d) => d.path);
    dispatch({ type: "SELECT_DAGS", paths: allPaths });
  };

  const handleDeselectAll = () => {
    dispatch({ type: "SELECT_DAGS", paths: [] });
  };

  const complexityBadge = (complexity: DagFile["complexity"]) => {
    const variants = {
      simple: "success" as const,
      medium: "warning" as const,
      complex: "error" as const,
    };
    const labels = {
      simple: "Simple",
      medium: "Medium",
      complex: "Complex",
    };
    return <Badge variant={variants[complexity]}>{labels[complexity]}</Badge>;
  };

  return (
    <WizardStep
      title="Select DAGs"
      description="Choose which Airflow DAG files to migrate to Prefect flows."
      nextLabel="Analyze"
    >
      <div className="space-y-4">
        {/* Directory input */}
        <div className="space-y-2">
          <Label htmlFor="dags-directory">DAGs Directory</Label>
          <div className="flex gap-2">
            <Input
              id="dags-directory"
              placeholder="/path/to/dags"
              value={state.dagsDirectory}
              onChange={(e) => handleDirectoryChange(e.target.value)}
            />
            <Button variant="outline" onClick={handleScan} disabled={isLoading}>
              <FolderOpen className="w-4 h-4 mr-2" />
              {isLoading ? "Scanning..." : "Scan"}
            </Button>
          </div>
        </div>

        {/* Search filter */}
        <div className="space-y-2">
          <Label htmlFor="search">Search DAGs</Label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              id="search"
              placeholder="Filter by name..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {/* Selection actions */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            {state.selectedDags.length} of {dagFiles.length} DAGs selected
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleSelectAll}>
              Select All
            </Button>
            <Button variant="outline" size="sm" onClick={handleDeselectAll}>
              Deselect All
            </Button>
          </div>
        </div>

        {/* DAG list */}
        <ScrollArea className="h-[300px] border rounded-md p-4">
          {filteredDags.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <FileCode className="w-12 h-12 mb-2 opacity-50" />
              <p>No DAG files found</p>
              <p className="text-sm">Enter a directory path and click Scan</p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredDags.map((dag) => (
                <div
                  key={dag.path}
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Checkbox
                      id={dag.path}
                      checked={state.selectedDags.includes(dag.path)}
                      onCheckedChange={() => handleToggleDag(dag.path)}
                    />
                    <Label
                      htmlFor={dag.path}
                      className="cursor-pointer font-mono text-sm"
                    >
                      {dag.name}
                    </Label>
                  </div>
                  {complexityBadge(dag.complexity)}
                </div>
              ))}
            </div>
          )}
        </ScrollArea>

        {/* Complexity legend */}
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span className="font-medium">Complexity:</span>
          <span className="flex items-center gap-1">
            <Badge variant="success" className="h-5">Simple</Badge>
            Automated
          </span>
          <span className="flex items-center gap-1">
            <Badge variant="warning" className="h-5">Medium</Badge>
            Review needed
          </span>
          <span className="flex items-center gap-1">
            <Badge variant="error" className="h-5">Complex</Badge>
            Manual work
          </span>
        </div>
      </div>
    </WizardStep>
  );
}
