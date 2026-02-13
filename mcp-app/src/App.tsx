import { useEffect } from "react";
import { WizardProvider, useWizard } from "./components/wizard/WizardProvider";
import { WizardNavigation } from "./components/wizard/WizardNavigation";
import { DagSelector } from "./components/wizard/steps/DagSelector";
import { AnalysisView } from "./components/wizard/steps/AnalysisView";
import { ConversionConfig } from "./components/wizard/steps/ConversionConfig";
import { ValidationView } from "./components/wizard/steps/ValidationView";
import { ProjectSetup } from "./components/wizard/steps/ProjectSetup";
import { DeploymentConfigStep } from "./components/wizard/steps/DeploymentConfig";
import { ExportView } from "./components/wizard/steps/ExportView";
import * as mcp from "./lib/mcp";

function WizardContent() {
  const { state } = useWizard();

  // Initialize MCP connection
  useEffect(() => {
    if (mcp.isMcpAppContext()) {
      mcp.connect();

      // Handle initial tool result (e.g., if wizard was invoked with a directory)
      mcp.onToolResult((result: unknown) => {
        console.log("Initial tool result:", result);
        // Could set initial directory from result
      });
    }
  }, []);

  const renderStep = () => {
    switch (state.currentStep) {
      case 1:
        return <DagSelector />;
      case 2:
        return <AnalysisView />;
      case 3:
        return <ConversionConfig />;
      case 4:
        return <ValidationView />;
      case 5:
        return <ProjectSetup />;
      case 6:
        return <DeploymentConfigStep />;
      case 7:
        return <ExportView />;
      default:
        return <DagSelector />;
    }
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-4xl mx-auto">
        <header className="mb-8 text-center">
          <h1 className="text-2xl font-bold mb-2">Airflow Migration Wizard</h1>
          <p className="text-muted-foreground">
            Convert your Airflow DAGs to production-ready Prefect flows
          </p>
        </header>

        <WizardNavigation />

        <main>{renderStep()}</main>

        <footer className="mt-8 text-center text-sm text-muted-foreground">
          Powered by airflow-unfactor
        </footer>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <WizardProvider>
      <WizardContent />
    </WizardProvider>
  );
}
