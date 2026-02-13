import { useWizard } from "../WizardProvider";
import { WizardStep } from "../WizardStep";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Separator } from "@/components/ui/separator";
import { FileCode, FolderTree, Settings2 } from "lucide-react";
import type { ConversionOptions } from "@/types";

export function ConversionConfig() {
  const { state, dispatch } = useWizard();
  const { conversionOptions } = state;

  const handleOptionChange = (key: keyof ConversionOptions, value: boolean | string) => {
    dispatch({
      type: "SET_CONVERSION_OPTIONS",
      options: { [key]: value },
    });
  };

  return (
    <WizardStep
      title="Conversion Configuration"
      description="Configure how your DAGs will be converted to Prefect flows."
      nextLabel="Convert"
    >
      <div className="space-y-6">
        {/* Output Options */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Settings2 className="w-5 h-5" />
            <h3 className="font-medium">Output Options</h3>
          </div>

          <div className="space-y-3 pl-7">
            <div className="flex items-center gap-3">
              <Checkbox
                id="includeComments"
                checked={conversionOptions.includeComments}
                onCheckedChange={(checked) =>
                  handleOptionChange("includeComments", !!checked)
                }
              />
              <Label htmlFor="includeComments" className="cursor-pointer">
                <span className="font-medium">Include educational comments</span>
                <p className="text-sm text-muted-foreground">
                  Add comments explaining Prefect concepts and best practices
                </p>
              </Label>
            </div>

            <div className="flex items-center gap-3">
              <Checkbox
                id="generateTests"
                checked={conversionOptions.generateTests}
                onCheckedChange={(checked) =>
                  handleOptionChange("generateTests", !!checked)
                }
              />
              <Label htmlFor="generateTests" className="cursor-pointer">
                <span className="font-medium">Generate pytest tests</span>
                <p className="text-sm text-muted-foreground">
                  Create test files to verify your converted flows
                </p>
              </Label>
            </div>

            <div className="flex items-center gap-3">
              <Checkbox
                id="generateRunbook"
                checked={conversionOptions.generateRunbook}
                onCheckedChange={(checked) =>
                  handleOptionChange("generateRunbook", !!checked)
                }
              />
              <Label htmlFor="generateRunbook" className="cursor-pointer">
                <span className="font-medium">Generate migration runbook</span>
                <p className="text-sm text-muted-foreground">
                  Create a guide with deployment steps and manual review items
                </p>
              </Label>
            </div>

            <div className="flex items-center gap-3">
              <Checkbox
                id="preserveAirflowComments"
                checked={conversionOptions.preserveAirflowComments}
                onCheckedChange={(checked) =>
                  handleOptionChange("preserveAirflowComments", !!checked)
                }
              />
              <Label htmlFor="preserveAirflowComments" className="cursor-pointer">
                <span className="font-medium">Preserve Airflow comments</span>
                <p className="text-sm text-muted-foreground">
                  Keep original comments from the Airflow DAG files
                </p>
              </Label>
            </div>
          </div>
        </div>

        <Separator />

        {/* Output Structure */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <FolderTree className="w-5 h-5" />
            <h3 className="font-medium">Output Structure</h3>
          </div>

          <RadioGroup
            value={conversionOptions.outputStructure}
            onValueChange={(value) =>
              handleOptionChange("outputStructure", value)
            }
            className="pl-7 space-y-3"
          >
            <div className="flex items-start gap-3">
              <RadioGroupItem value="flat" id="flat" className="mt-1" />
              <Label htmlFor="flat" className="cursor-pointer">
                <span className="font-medium">Flat</span>
                <p className="text-sm text-muted-foreground">
                  All flows in a single directory
                </p>
                <pre className="mt-2 p-2 bg-muted rounded text-xs font-mono">
{`flows/
  etl_daily.py
  ml_training.py`}
                </pre>
              </Label>
            </div>

            <div className="flex items-start gap-3">
              <RadioGroupItem value="prefect-flows" id="prefect-flows" className="mt-1" />
              <Label htmlFor="prefect-flows" className="cursor-pointer">
                <span className="font-medium">PrefectHQ/flows style</span>
                <span className="ml-2 text-xs text-wizard-success">(Recommended)</span>
                <p className="text-sm text-muted-foreground">
                  Production-ready structure with workspace organization
                </p>
                <pre className="mt-2 p-2 bg-muted rounded text-xs font-mono">
{`deployments/
  {workspace}/
    prefect.yaml
    etl-daily/
      flow.py
      requirements.txt
      Dockerfile
      test_flow.py`}
                </pre>
              </Label>
            </div>

            <div className="flex items-start gap-3">
              <RadioGroupItem value="custom" id="custom" className="mt-1" />
              <Label htmlFor="custom" className="cursor-pointer">
                <span className="font-medium">Custom</span>
                <p className="text-sm text-muted-foreground">
                  Define your own directory structure
                </p>
              </Label>
            </div>
          </RadioGroup>
        </div>

        <Separator />

        {/* Preview */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <FileCode className="w-5 h-5" />
            <h3 className="font-medium">What will be generated</h3>
          </div>

          <div className="pl-7 grid grid-cols-2 gap-4 text-sm">
            <div className="p-3 rounded-lg border bg-muted/30">
              <p className="font-medium mb-2">Per Flow</p>
              <ul className="space-y-1 text-muted-foreground">
                <li>• flow.py - Converted Prefect flow</li>
                {conversionOptions.generateTests && (
                  <li>• test_flow.py - Pytest tests</li>
                )}
                <li>• requirements.txt - Dependencies</li>
                {conversionOptions.outputStructure === "prefect-flows" && (
                  <li>• Dockerfile - Container config</li>
                )}
              </ul>
            </div>

            <div className="p-3 rounded-lg border bg-muted/30">
              <p className="font-medium mb-2">Project-wide</p>
              <ul className="space-y-1 text-muted-foreground">
                {conversionOptions.outputStructure === "prefect-flows" && (
                  <>
                    <li>• prefect.yaml - Deployment config</li>
                    <li>• .gitignore - Git ignore rules</li>
                    <li>• .prefectignore - Deploy ignore rules</li>
                    <li>• README.md - Documentation</li>
                  </>
                )}
                {conversionOptions.generateRunbook && (
                  <li>• MIGRATION_RUNBOOK.md - Guide</li>
                )}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </WizardStep>
  );
}
