import { useEffect, useState } from "react";
import { useWizard } from "../WizardProvider";
import { WizardStep } from "../WizardStep";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Workflow,
  Boxes,
  Clock,
} from "lucide-react";
import type { DagAnalysis, OperatorInfo, Warning } from "@/types";
import * as mcp from "@/lib/mcp";

// Mock analysis data for standalone testing
const mockAnalysis: DagAnalysis = {
  dagId: "etl_daily",
  filePath: "/dags/etl_daily.py",
  operators: [
    { name: "extract_data", type: "PythonOperator", taskId: "extract", supported: true, prefectEquivalent: "@task" },
    { name: "transform_data", type: "PythonOperator", taskId: "transform", supported: true, prefectEquivalent: "@task" },
    { name: "load_data", type: "PostgresOperator", taskId: "load", supported: true, prefectEquivalent: "execute_sql" },
    { name: "custom_op", type: "CustomOperator", taskId: "custom", supported: false, notes: "Requires manual conversion" },
  ],
  dependencies: {
    taskCount: 4,
    edgeCount: 3,
    graphType: "linear",
    edges: [["extract", "transform"], ["transform", "load"], ["load", "custom"]],
  },
  features: {
    taskflow: true,
    datasets: false,
    sensors: false,
    customOperators: true,
    dynamicTasks: false,
    taskGroups: false,
    triggerRules: false,
    jinjaTemplates: false,
  },
  complexityScore: 75,
  warnings: [
    { severity: "warning", message: "CustomOperator requires manual conversion", line: 45 },
    { severity: "error", message: "XCom pattern may need review", suggestion: "Convert to return values" },
  ],
};

export function AnalysisView() {
  const { state, dispatch } = useWizard();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);

  // Run analysis when component mounts
  useEffect(() => {
    if (state.analysisStatus === "idle" && state.selectedDags.length > 0) {
      runAnalysis();
    }
  }, []);

  const runAnalysis = async () => {
    setIsAnalyzing(true);
    dispatch({ type: "SET_ANALYSIS_STATUS", status: "loading" });

    const dagCount = state.selectedDags.length;
    const analyses = new Map<string, DagAnalysis>();

    for (let i = 0; i < dagCount; i++) {
      setProgress(((i + 1) / dagCount) * 100);
      const dagPath = state.selectedDags[i];
      const dagName = dagPath.split("/").pop()?.replace(".py", "") || "unknown";

      try {
        if (mcp.isMcpAppContext()) {
          // Call MCP analyze tool
          const analysis = await mcp.analyzeDag(dagPath);
          analyses.set(dagPath, analysis);
        } else {
          // Use mock data for standalone testing
          await new Promise((resolve) => setTimeout(resolve, 300));
          analyses.set(dagPath, {
            ...mockAnalysis,
            dagId: dagName,
            filePath: dagPath,
          });
        }
      } catch (error) {
        console.error(`Failed to analyze ${dagPath}:`, error);
        // Use mock data on error
        analyses.set(dagPath, {
          ...mockAnalysis,
          dagId: dagName,
          filePath: dagPath,
          warnings: [...mockAnalysis.warnings, { severity: "error", message: "Analysis failed - using mock data" }],
        });
      }
    }

    dispatch({ type: "SET_ANALYSES", analyses });
    dispatch({ type: "SET_ANALYSIS_STATUS", status: "complete" });
    setIsAnalyzing(false);
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 80) return "text-wizard-success";
    if (score >= 60) return "text-wizard-warning";
    return "text-wizard-error";
  };

  const renderOperatorTable = (operators: OperatorInfo[]) => (
    <div className="rounded-md border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="p-2 text-left font-medium">Task ID</th>
            <th className="p-2 text-left font-medium">Operator</th>
            <th className="p-2 text-left font-medium">Prefect Equivalent</th>
            <th className="p-2 text-center font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {operators.map((op) => (
            <tr key={op.taskId} className="border-b last:border-0">
              <td className="p-2 font-mono text-xs">{op.taskId}</td>
              <td className="p-2">{op.type}</td>
              <td className="p-2 font-mono text-xs">
                {op.prefectEquivalent || "-"}
              </td>
              <td className="p-2 text-center">
                {op.supported ? (
                  <CheckCircle className="w-4 h-4 text-wizard-success inline" />
                ) : (
                  <XCircle className="w-4 h-4 text-wizard-error inline" />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const renderWarnings = (warnings: Warning[]) => (
    <div className="space-y-2">
      {warnings.map((warning, i) => (
        <div
          key={i}
          className={`p-3 rounded-md ${
            warning.severity === "error"
              ? "bg-wizard-error/10 border border-wizard-error/30"
              : "bg-wizard-warning/10 border border-wizard-warning/30"
          }`}
        >
          <div className="flex items-start gap-2">
            <AlertTriangle
              className={`w-4 h-4 mt-0.5 ${
                warning.severity === "error"
                  ? "text-wizard-error"
                  : "text-wizard-warning"
              }`}
            />
            <div>
              <p className="font-medium text-sm">{warning.message}</p>
              {warning.line && (
                <p className="text-xs text-muted-foreground">Line {warning.line}</p>
              )}
              {warning.suggestion && (
                <p className="text-xs text-muted-foreground mt-1">
                  Suggestion: {warning.suggestion}
                </p>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );

  const renderFeatures = (features: DagAnalysis["features"]) => {
    const featureList = [
      { key: "taskflow", label: "TaskFlow API", enabled: features.taskflow },
      { key: "datasets", label: "Datasets", enabled: features.datasets },
      { key: "sensors", label: "Sensors", enabled: features.sensors },
      { key: "customOperators", label: "Custom Operators", enabled: features.customOperators },
      { key: "dynamicTasks", label: "Dynamic Tasks", enabled: features.dynamicTasks },
      { key: "taskGroups", label: "Task Groups", enabled: features.taskGroups },
      { key: "triggerRules", label: "Trigger Rules", enabled: features.triggerRules },
      { key: "jinjaTemplates", label: "Jinja Templates", enabled: features.jinjaTemplates },
    ];

    return (
      <div className="grid grid-cols-2 gap-2">
        {featureList.map((f) => (
          <div key={f.key} className="flex items-center gap-2">
            {f.enabled ? (
              <CheckCircle className="w-4 h-4 text-wizard-success" />
            ) : (
              <span className="w-4 h-4 rounded-full border border-muted-foreground/30" />
            )}
            <span className={f.enabled ? "" : "text-muted-foreground"}>
              {f.label}
            </span>
          </div>
        ))}
      </div>
    );
  };

  if (isAnalyzing) {
    return (
      <WizardStep title="Analyzing DAGs" description="Please wait while we analyze your Airflow DAGs.">
        <div className="space-y-4 py-8">
          <Progress value={progress} />
          <p className="text-center text-muted-foreground">
            Analyzing {Math.ceil((progress / 100) * state.selectedDags.length)} of{" "}
            {state.selectedDags.length} DAGs...
          </p>
        </div>
      </WizardStep>
    );
  }

  return (
    <WizardStep
      title="Analysis Results"
      description="Review the analysis of your Airflow DAGs before conversion."
    >
      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="p-4 rounded-lg border bg-muted/30">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Boxes className="w-4 h-4" />
            Total DAGs
          </div>
          <p className="text-2xl font-bold">{state.analyses.size}</p>
        </div>
        <div className="p-4 rounded-lg border bg-muted/30">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Workflow className="w-4 h-4" />
            Total Operators
          </div>
          <p className="text-2xl font-bold">
            {Array.from(state.analyses.values()).reduce(
              (sum, a) => sum + a.operators.length,
              0
            )}
          </p>
        </div>
        <div className="p-4 rounded-lg border bg-muted/30">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Clock className="w-4 h-4" />
            Avg Complexity
          </div>
          <p className="text-2xl font-bold">
            {state.analyses.size > 0
              ? Math.round(
                  Array.from(state.analyses.values()).reduce(
                    (sum, a) => sum + a.complexityScore,
                    0
                  ) / state.analyses.size
                )
              : 0}
          </p>
        </div>
      </div>

      {/* Per-DAG analysis */}
      <ScrollArea className="h-[400px]">
        <Accordion type="multiple" className="space-y-2">
          {Array.from(state.analyses.entries()).map(([path, analysis]) => {
            const supportedCount = analysis.operators.filter((o) => o.supported).length;
            const warningCount = analysis.warnings.filter((w) => w.severity === "warning").length;
            const errorCount = analysis.warnings.filter((w) => w.severity === "error").length;

            return (
              <AccordionItem key={path} value={path} className="border rounded-lg px-4">
                <AccordionTrigger className="hover:no-underline">
                  <div className="flex items-center justify-between w-full pr-4">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-sm">{analysis.dagId}</span>
                      <span className="text-xs text-muted-foreground">
                        {analysis.operators.length} tasks, {supportedCount} supported
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {errorCount > 0 && (
                        <Badge variant="error">{errorCount} errors</Badge>
                      )}
                      {warningCount > 0 && (
                        <Badge variant="warning">{warningCount} warnings</Badge>
                      )}
                      <span className={`font-bold ${getConfidenceColor(analysis.complexityScore)}`}>
                        {analysis.complexityScore}%
                      </span>
                    </div>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="pt-4 space-y-4">
                  {/* Operators */}
                  <div>
                    <h4 className="font-medium mb-2">Operators</h4>
                    {renderOperatorTable(analysis.operators)}
                  </div>

                  <Separator />

                  {/* Dependencies */}
                  <div>
                    <h4 className="font-medium mb-2">Dependencies</h4>
                    <div className="text-sm space-y-1">
                      <p>
                        <span className="text-muted-foreground">Graph type:</span>{" "}
                        <span className="capitalize">{analysis.dependencies.graphType}</span>
                      </p>
                      <p>
                        <span className="text-muted-foreground">Tasks:</span>{" "}
                        {analysis.dependencies.taskCount}
                      </p>
                      <p>
                        <span className="text-muted-foreground">Edges:</span>{" "}
                        {analysis.dependencies.edgeCount}
                      </p>
                    </div>
                  </div>

                  <Separator />

                  {/* Features */}
                  <div>
                    <h4 className="font-medium mb-2">Features Detected</h4>
                    {renderFeatures(analysis.features)}
                  </div>

                  {/* Warnings */}
                  {analysis.warnings.length > 0 && (
                    <>
                      <Separator />
                      <div>
                        <h4 className="font-medium mb-2">Issues</h4>
                        {renderWarnings(analysis.warnings)}
                      </div>
                    </>
                  )}
                </AccordionContent>
              </AccordionItem>
            );
          })}
        </Accordion>
      </ScrollArea>
    </WizardStep>
  );
}
