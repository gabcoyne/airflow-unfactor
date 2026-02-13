import { useWizard } from "../WizardProvider";
import { WizardStep } from "../WizardStep";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Package, Settings, X } from "lucide-react";
import { useState } from "react";
import type { ProjectConfig } from "@/types";

export function ProjectSetup() {
  const { state, dispatch } = useWizard();
  const { projectConfig, detectedDependencies } = state;
  const [newDep, setNewDep] = useState("");

  const handleConfigChange = (key: keyof ProjectConfig, value: string | boolean) => {
    dispatch({
      type: "SET_PROJECT_CONFIG",
      config: { [key]: value },
    });
  };

  const addDependency = () => {
    if (newDep.trim() && !projectConfig.dependencies.includes(newDep.trim())) {
      dispatch({
        type: "SET_PROJECT_CONFIG",
        config: {
          dependencies: [...projectConfig.dependencies, newDep.trim()],
        },
      });
      setNewDep("");
    }
  };

  const removeDependency = (dep: string) => {
    dispatch({
      type: "SET_PROJECT_CONFIG",
      config: {
        dependencies: projectConfig.dependencies.filter((d) => d !== dep),
      },
    });
  };

  // Generate pyproject.toml preview
  const pyprojectPreview = `[project]
name = "${projectConfig.projectName}"
version = "0.1.0"
description = "${projectConfig.description || "Prefect flows migrated from Airflow"}"
requires-python = ">=3.9"
dependencies = [
    "prefect>=3.0.0",
${projectConfig.dependencies.map((d) => `    "${d}",`).join("\n")}
]

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
asyncio_mode = "auto"
`;

  return (
    <WizardStep
      title="Project Setup"
      description="Configure the generated Prefect project structure."
    >
      <div className="space-y-6">
        {/* Project Identity */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Package className="w-5 h-5" />
            <h3 className="font-medium">Project Identity</h3>
          </div>

          <div className="grid grid-cols-2 gap-4 pl-7">
            <div className="space-y-2">
              <Label htmlFor="projectName">Project Name</Label>
              <Input
                id="projectName"
                value={projectConfig.projectName}
                onChange={(e) => handleConfigChange("projectName", e.target.value)}
                placeholder="my-prefect-flows"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="workspace">Workspace</Label>
              <Input
                id="workspace"
                value={projectConfig.workspace}
                onChange={(e) => handleConfigChange("workspace", e.target.value)}
                placeholder="default"
              />
            </div>
            <div className="space-y-2 col-span-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Input
                id="description"
                value={projectConfig.description}
                onChange={(e) => handleConfigChange("description", e.target.value)}
                placeholder="Prefect flows migrated from Airflow"
              />
            </div>
          </div>
        </div>

        <Separator />

        {/* Infrastructure Options */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            <h3 className="font-medium">Infrastructure Options</h3>
          </div>

          <div className="grid grid-cols-2 gap-3 pl-7">
            <div className="flex items-center gap-3">
              <Checkbox
                id="includePyproject"
                checked={projectConfig.includePyproject}
                onCheckedChange={(checked) =>
                  handleConfigChange("includePyproject", !!checked)
                }
              />
              <Label htmlFor="includePyproject" className="cursor-pointer">
                pyproject.toml
              </Label>
            </div>

            <div className="flex items-center gap-3">
              <Checkbox
                id="includeDockerfile"
                checked={projectConfig.includeDockerfile}
                onCheckedChange={(checked) =>
                  handleConfigChange("includeDockerfile", !!checked)
                }
              />
              <Label htmlFor="includeDockerfile" className="cursor-pointer">
                Dockerfile per flow
              </Label>
            </div>

            <div className="flex items-center gap-3">
              <Checkbox
                id="includeGithubActions"
                checked={projectConfig.includeGithubActions}
                onCheckedChange={(checked) =>
                  handleConfigChange("includeGithubActions", !!checked)
                }
              />
              <Label htmlFor="includeGithubActions" className="cursor-pointer">
                GitHub Actions CI
              </Label>
            </div>

            <div className="flex items-center gap-3">
              <Checkbox
                id="includePrecommit"
                checked={projectConfig.includePrecommit}
                onCheckedChange={(checked) =>
                  handleConfigChange("includePrecommit", !!checked)
                }
              />
              <Label htmlFor="includePrecommit" className="cursor-pointer">
                Pre-commit hooks
              </Label>
            </div>

            <div className="flex items-center gap-3">
              <Checkbox
                id="includeMise"
                checked={projectConfig.includeMise}
                onCheckedChange={(checked) =>
                  handleConfigChange("includeMise", !!checked)
                }
              />
              <Label htmlFor="includeMise" className="cursor-pointer">
                mise.toml (tool versions)
              </Label>
            </div>
          </div>
        </div>

        <Separator />

        {/* Dependencies */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">Dependencies</h3>
            <div className="flex items-center gap-2">
              <Input
                value={newDep}
                onChange={(e) => setNewDep(e.target.value)}
                placeholder="package-name"
                className="w-40 h-8"
                onKeyDown={(e) => e.key === "Enter" && addDependency()}
              />
              <Button size="sm" variant="outline" onClick={addDependency}>
                Add
              </Button>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {/* Core dependency */}
            <Badge variant="secondary" className="gap-1">
              prefect&gt;=3.0.0
            </Badge>

            {/* Detected dependencies */}
            {detectedDependencies.map((dep) => (
              <Badge key={dep} variant="outline" className="gap-1">
                {dep}
                <span className="text-xs text-muted-foreground">(detected)</span>
              </Badge>
            ))}

            {/* User-added dependencies */}
            {projectConfig.dependencies.map((dep) => (
              <Badge key={dep} variant="default" className="gap-1">
                {dep}
                <button
                  onClick={() => removeDependency(dep)}
                  className="ml-1 hover:bg-white/20 rounded-full"
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}
          </div>
        </div>

        <Separator />

        {/* pyproject.toml Preview */}
        {projectConfig.includePyproject && (
          <div className="space-y-2">
            <h3 className="font-medium">pyproject.toml Preview</h3>
            <ScrollArea className="h-[200px] rounded-md border">
              <pre className="p-4 text-xs font-mono">{pyprojectPreview}</pre>
            </ScrollArea>
          </div>
        )}
      </div>
    </WizardStep>
  );
}
