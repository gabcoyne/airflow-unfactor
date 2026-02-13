import { useEffect, useState } from "react";
import { useWizard } from "../WizardProvider";
import { WizardStep } from "../WizardStep";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import type { ConversionResult, ValidationResult } from "@/types";
import * as mcp from "@/lib/mcp";

// Mock conversion result
const mockConversion: ConversionResult = {
  dagId: "etl_daily",
  success: true,
  flowCode: `from prefect import flow, task

@task
def extract():
    """Extract data from source."""
    return {"data": [1, 2, 3]}

@task
def transform(data):
    """Transform the extracted data."""
    return [x * 2 for x in data["data"]]

@task
def load(transformed):
    """Load transformed data to destination."""
    print(f"Loading {len(transformed)} records")

@flow(name="etl-daily")
def etl_daily():
    data = extract()
    transformed = transform(data)
    load(transformed)

if __name__ == "__main__":
    etl_daily()
`,
  testCode: `import pytest
from flow import etl_daily, extract, transform, load

def test_extract():
    result = extract.fn()
    assert "data" in result

def test_transform():
    result = transform.fn({"data": [1, 2, 3]})
    assert result == [2, 4, 6]
`,
  runbook: "# Migration Runbook\n\n## Steps\n1. Deploy to Prefect Cloud",
  warnings: ["XCom converted to return values"],
};

// Mock validation result
const mockValidation: ValidationResult = {
  dagId: "etl_daily",
  isValid: true,
  confidenceScore: 92,
  taskCountMatch: true,
  dependencyPreserved: true,
  issues: [],
  dagTasks: ["extract", "transform", "load"],
  flowTasks: ["extract", "transform", "load"],
  dagEdges: [["extract", "transform"], ["transform", "load"]],
  flowEdges: [["extract", "transform"], ["transform", "load"]],
};

export function ValidationView() {
  const { state, dispatch } = useWizard();
  const [phase, setPhase] = useState<"converting" | "validating" | "complete">("converting");
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (state.conversionStatus === "idle") {
      runConversionAndValidation();
    }
  }, []);

  const runConversionAndValidation = async () => {
    dispatch({ type: "SET_CONVERSION_STATUS", status: "converting", progress: 0 });
    setPhase("converting");

    const dagCount = state.selectedDags.length;
    const useMcp = mcp.isMcpAppContext();

    // Phase 1: Convert
    for (let i = 0; i < dagCount; i++) {
      const dagPath = state.selectedDags[i];
      const dagName = dagPath.split("/").pop()?.replace(".py", "") || "unknown";

      setProgress(((i + 1) / dagCount) * 50);

      try {
        if (useMcp) {
          const result = await mcp.convertDag(dagPath, state.conversionOptions);
          dispatch({
            type: "SET_CONVERSION_RESULT",
            dagId: dagPath,
            result,
          });
        } else {
          await new Promise((resolve) => setTimeout(resolve, 400));
          dispatch({
            type: "SET_CONVERSION_RESULT",
            dagId: dagPath,
            result: { ...mockConversion, dagId: dagName },
          });
        }
      } catch (error) {
        console.error(`Failed to convert ${dagPath}:`, error);
        dispatch({
          type: "SET_CONVERSION_RESULT",
          dagId: dagPath,
          result: { ...mockConversion, dagId: dagName, success: false, warnings: ["Conversion failed - using mock data"] },
        });
      }
    }

    // Phase 2: Validate
    setPhase("validating");
    dispatch({ type: "SET_CONVERSION_STATUS", status: "validating", progress: 50 });

    for (let i = 0; i < dagCount; i++) {
      const dagPath = state.selectedDags[i];
      const dagName = dagPath.split("/").pop()?.replace(".py", "") || "unknown";
      const conversion = state.conversions.get(dagPath);

      setProgress(50 + ((i + 1) / dagCount) * 50);

      try {
        if (useMcp && conversion?.flowCode) {
          const result = await mcp.validateConversion(dagPath, conversion.flowCode);
          dispatch({
            type: "SET_VALIDATION_RESULT",
            dagId: dagPath,
            result,
          });
        } else {
          await new Promise((resolve) => setTimeout(resolve, 300));
          dispatch({
            type: "SET_VALIDATION_RESULT",
            dagId: dagPath,
            result: { ...mockValidation, dagId: dagName },
          });
        }
      } catch (error) {
        console.error(`Failed to validate ${dagPath}:`, error);
        dispatch({
          type: "SET_VALIDATION_RESULT",
          dagId: dagPath,
          result: { ...mockValidation, dagId: dagName, isValid: false, issues: [{ type: "other", severity: "error", message: "Validation failed - using mock data" }] },
        });
      }
    }

    setPhase("complete");
    dispatch({ type: "SET_CONVERSION_STATUS", status: "complete", progress: 100 });
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 80) return "text-wizard-success";
    if (score >= 60) return "text-wizard-warning";
    return "text-wizard-error";
  };

  const getConfidenceBg = (score: number) => {
    if (score >= 80) return "bg-wizard-success";
    if (score >= 60) return "bg-wizard-warning";
    return "bg-wizard-error";
  };

  if (phase !== "complete") {
    return (
      <WizardStep
        title={phase === "converting" ? "Converting DAGs" : "Validating Conversions"}
        description="Please wait while we process your DAGs."
        hideNav
      >
        <div className="space-y-6 py-8">
          <Progress value={progress} />
          <p className="text-center text-muted-foreground">
            {phase === "converting" ? "Converting" : "Validating"}{" "}
            {Math.ceil((progress / (phase === "converting" ? 50 : 100)) * state.selectedDags.length)} of{" "}
            {state.selectedDags.length} DAGs...
          </p>

          {/* Show completed items */}
          <div className="space-y-2 max-w-md mx-auto">
            {state.selectedDags.map((dagPath) => {
              const dagName = dagPath.split("/").pop()?.replace(".py", "") || "unknown";
              const isConverted = state.conversions.has(dagPath);
              const isValidated = state.validations.has(dagPath);

              return (
                <div
                  key={dagPath}
                  className="flex items-center justify-between p-2 rounded border"
                >
                  <span className="font-mono text-sm">{dagName}</span>
                  <div className="flex items-center gap-2">
                    {isConverted && (
                      <Badge variant="success" className="text-xs">
                        Converted
                      </Badge>
                    )}
                    {isValidated && (
                      <Badge variant="success" className="text-xs">
                        Validated
                      </Badge>
                    )}
                    {!isConverted && !isValidated && (
                      <span className="text-xs text-muted-foreground">Pending</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </WizardStep>
    );
  }

  return (
    <WizardStep
      title="Validation Results"
      description="Review the conversion results and validation scores."
    >
      {/* Summary */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="p-4 rounded-lg border bg-muted/30">
          <p className="text-sm text-muted-foreground mb-1">Converted</p>
          <p className="text-2xl font-bold">
            {Array.from(state.conversions.values()).filter((c) => c.success).length}/
            {state.conversions.size}
          </p>
        </div>
        <div className="p-4 rounded-lg border bg-muted/30">
          <p className="text-sm text-muted-foreground mb-1">Valid</p>
          <p className="text-2xl font-bold">
            {Array.from(state.validations.values()).filter((v) => v.isValid).length}/
            {state.validations.size}
          </p>
        </div>
        <div className="p-4 rounded-lg border bg-muted/30">
          <p className="text-sm text-muted-foreground mb-1">Avg Confidence</p>
          <p className="text-2xl font-bold">
            {state.validations.size > 0
              ? Math.round(
                  Array.from(state.validations.values()).reduce(
                    (sum, v) => sum + v.confidenceScore,
                    0
                  ) / state.validations.size
                )
              : 0}
            %
          </p>
        </div>
      </div>

      {/* Per-DAG results */}
      <ScrollArea className="h-[350px]">
        <Accordion type="multiple" className="space-y-2">
          {state.selectedDags.map((dagPath) => {
            const dagName = dagPath.split("/").pop()?.replace(".py", "") || "unknown";
            const conversion = state.conversions.get(dagPath);
            const validation = state.validations.get(dagPath);

            if (!conversion || !validation) return null;

            return (
              <AccordionItem key={dagPath} value={dagPath} className="border rounded-lg px-4">
                <AccordionTrigger className="hover:no-underline">
                  <div className="flex items-center justify-between w-full pr-4">
                    <div className="flex items-center gap-3">
                      {validation.isValid ? (
                        <CheckCircle className="w-5 h-5 text-wizard-success" />
                      ) : (
                        <XCircle className="w-5 h-5 text-wizard-error" />
                      )}
                      <span className="font-mono text-sm">{dagName}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      {conversion.warnings.length > 0 && (
                        <Badge variant="warning">
                          {conversion.warnings.length} warnings
                        </Badge>
                      )}
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground">Confidence:</span>
                        <span className={`font-bold ${getConfidenceColor(validation.confidenceScore)}`}>
                          {validation.confidenceScore}%
                        </span>
                      </div>
                    </div>
                  </div>
                </AccordionTrigger>
                <AccordionContent className="pt-4 space-y-4">
                  {/* Task comparison */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 rounded-lg border">
                      <h4 className="font-medium mb-2 text-sm">DAG Tasks</h4>
                      <div className="space-y-1">
                        {validation.dagTasks.map((task) => (
                          <div
                            key={task}
                            className="text-xs font-mono p-1 bg-muted rounded"
                          >
                            {task}
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="p-3 rounded-lg border">
                      <h4 className="font-medium mb-2 text-sm">Flow Tasks</h4>
                      <div className="space-y-1">
                        {validation.flowTasks.map((task) => (
                          <div
                            key={task}
                            className="text-xs font-mono p-1 bg-muted rounded"
                          >
                            {task}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Validation checks */}
                  <div className="space-y-2">
                    <h4 className="font-medium text-sm">Validation Checks</h4>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="flex items-center gap-2 text-sm">
                        {validation.taskCountMatch ? (
                          <CheckCircle className="w-4 h-4 text-wizard-success" />
                        ) : (
                          <XCircle className="w-4 h-4 text-wizard-error" />
                        )}
                        Task count match
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        {validation.dependencyPreserved ? (
                          <CheckCircle className="w-4 h-4 text-wizard-success" />
                        ) : (
                          <XCircle className="w-4 h-4 text-wizard-error" />
                        )}
                        Dependencies preserved
                      </div>
                    </div>
                  </div>

                  {/* Warnings */}
                  {conversion.warnings.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="font-medium text-sm">Warnings</h4>
                      {conversion.warnings.map((warning, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-2 p-2 rounded bg-wizard-warning/10 border border-wizard-warning/30"
                        >
                          <AlertTriangle className="w-4 h-4 text-wizard-warning mt-0.5" />
                          <span className="text-sm">{warning}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Confidence breakdown */}
                  <div className="space-y-2">
                    <h4 className="font-medium text-sm">Confidence Score</h4>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-3 bg-muted rounded-full overflow-hidden">
                        <div
                          className={`h-full ${getConfidenceBg(validation.confidenceScore)}`}
                          style={{ width: `${validation.confidenceScore}%` }}
                        />
                      </div>
                      <span className="font-mono text-sm font-bold">
                        {validation.confidenceScore}%
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {validation.confidenceScore >= 80
                        ? "High confidence - conversion is reliable"
                        : validation.confidenceScore >= 60
                        ? "Medium confidence - review recommended"
                        : "Low confidence - manual review required"}
                    </p>
                  </div>
                </AccordionContent>
              </AccordionItem>
            );
          })}
        </Accordion>
      </ScrollArea>
    </WizardStep>
  );
}
