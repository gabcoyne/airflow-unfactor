import { useEffect } from "react";
import { useWizard } from "../WizardProvider";
import { WizardStep } from "../WizardStep";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Server, Container, Trash2 } from "lucide-react";
import type { DeploymentSpec, DeploymentConfig } from "@/types";

export function DeploymentConfigStep() {
  const { state, dispatch } = useWizard();
  const { deploymentConfig, conversions, projectConfig } = state;

  // Initialize deployments from conversions if empty
  useEffect(() => {
    if (deploymentConfig.deployments.length === 0 && conversions.size > 0) {
      const initialDeployments: DeploymentSpec[] = Array.from(conversions.entries()).map(
        ([path, conv]) => ({
          flowId: path,
          name: conv.dagId.replace(/_/g, "-"),
          description: `Converted from ${conv.dagId}`,
          schedule: undefined,
          parameters: {},
          concurrencyLimit: 1,
          concurrencyOptions: { collisionStrategy: "ENQUEUE" },
        })
      );
      dispatch({
        type: "SET_DEPLOYMENT_CONFIG",
        config: { deployments: initialDeployments },
      });
    }
  }, [conversions]);

  const handleWorkPoolChange = (key: keyof DeploymentConfig["workPool"], value: string) => {
    dispatch({
      type: "SET_DEPLOYMENT_CONFIG",
      config: {
        workPool: { ...deploymentConfig.workPool, [key]: value },
      },
    });
  };

  const handleDockerChange = (key: keyof NonNullable<DeploymentConfig["docker"]>, value: string) => {
    dispatch({
      type: "SET_DEPLOYMENT_CONFIG",
      config: {
        docker: { ...deploymentConfig.docker, registry: "", imageTemplate: "", [key]: value },
      },
    });
  };

  const handleDeploymentChange = (index: number, spec: Partial<DeploymentSpec>) => {
    dispatch({ type: "SET_DEPLOYMENT_SPEC", index, spec });
  };

  const removeDeployment = (index: number) => {
    dispatch({ type: "REMOVE_DEPLOYMENT", index });
  };

  // Generate prefect.yaml preview
  const prefectYamlPreview = `name: ${projectConfig.projectName}
prefect-version: 3.0.0

pull:
  - prefect.deployments.steps.git_clone:
      repository: https://github.com/your-org/${projectConfig.projectName}
      branch: main

definitions:
  work_pools:
    default: &default_work_pool
      name: ${deploymentConfig.workPool.name}
      ${deploymentConfig.workPool.type !== "process" ? `job_variables:
        image: "{{ image }}"` : ""}

  ${deploymentConfig.workPool.type !== "process" ? `docker_build:
    - prefect.deployments.steps.run_shell_script: &git_sha
        id: get-commit-hash
        script: git rev-parse --short HEAD
        stream_output: false
    - prefect_docker.deployments.steps.build_docker_image: &docker_build
        tag: "{{ get-commit-hash.stdout }}"
        platform: linux/amd64` : ""}

deployments:
${deploymentConfig.deployments
  .map(
    (dep) => `  - name: ${dep.name}
    description: |
      ${dep.description}
    entrypoint: deployments/${projectConfig.workspace}/${dep.name}/flow.py:${dep.name.replace(/-/g, "_")}
    work_pool: *default_work_pool
    ${dep.schedule ? `schedule:
      cron: "${dep.schedule.cron}"
      timezone: "${dep.schedule.timezone}"` : ""}
    ${dep.concurrencyLimit ? `concurrency_limit: ${dep.concurrencyLimit}
    concurrency_options:
      collision_strategy: ${dep.concurrencyOptions?.collisionStrategy || "ENQUEUE"}` : ""}`
  )
  .join("\n\n")}
`;

  return (
    <WizardStep
      title="Deployment Configuration"
      description="Configure work pools and deployment settings for Prefect Cloud."
    >
      <div className="space-y-6">
        {/* Work Pool */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Server className="w-5 h-5" />
            <h3 className="font-medium">Work Pool</h3>
          </div>

          <div className="pl-7 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="workPoolName">Work Pool Name</Label>
              <Input
                id="workPoolName"
                value={deploymentConfig.workPool.name}
                onChange={(e) => handleWorkPoolChange("name", e.target.value)}
                placeholder="default-pool"
              />
            </div>

            <div className="space-y-2">
              <Label>Work Pool Type</Label>
              <RadioGroup
                value={deploymentConfig.workPool.type}
                onValueChange={(value) =>
                  handleWorkPoolChange("type", value as DeploymentConfig["workPool"]["type"])
                }
                className="flex gap-4"
              >
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="process" id="process" />
                  <Label htmlFor="process">Process</Label>
                </div>
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="docker" id="docker" />
                  <Label htmlFor="docker">Docker</Label>
                </div>
                <div className="flex items-center gap-2">
                  <RadioGroupItem value="kubernetes" id="kubernetes" />
                  <Label htmlFor="kubernetes">Kubernetes</Label>
                </div>
              </RadioGroup>
            </div>
          </div>
        </div>

        {/* Docker Config (if not process) */}
        {deploymentConfig.workPool.type !== "process" && (
          <>
            <Separator />
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Container className="w-5 h-5" />
                <h3 className="font-medium">Docker Configuration</h3>
              </div>

              <div className="pl-7 space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="registry">Docker Registry</Label>
                  <Input
                    id="registry"
                    value={deploymentConfig.docker?.registry || ""}
                    onChange={(e) => handleDockerChange("registry", e.target.value)}
                    placeholder="us-docker.pkg.dev/my-project/flows"
                  />
                </div>
              </div>
            </div>
          </>
        )}

        <Separator />

        {/* Deployments */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">Deployments</h3>
          </div>

          <ScrollArea className="h-[200px]">
            <Accordion type="multiple" className="space-y-2">
              {deploymentConfig.deployments.map((dep, index) => (
                <AccordionItem
                  key={dep.flowId}
                  value={dep.flowId}
                  className="border rounded-lg px-4"
                >
                  <AccordionTrigger className="hover:no-underline">
                    <div className="flex items-center justify-between w-full pr-4">
                      <span className="font-mono text-sm">{dep.name}</span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={(e) => {
                          e.stopPropagation();
                          removeDeployment(index);
                        }}
                      >
                        <Trash2 className="w-4 h-4 text-muted-foreground" />
                      </Button>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent className="pt-4 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Name</Label>
                        <Input
                          value={dep.name}
                          onChange={(e) =>
                            handleDeploymentChange(index, { name: e.target.value })
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Concurrency Limit</Label>
                        <Input
                          type="number"
                          value={dep.concurrencyLimit || ""}
                          onChange={(e) =>
                            handleDeploymentChange(index, {
                              concurrencyLimit: parseInt(e.target.value) || undefined,
                            })
                          }
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label>Description</Label>
                      <Input
                        value={dep.description}
                        onChange={(e) =>
                          handleDeploymentChange(index, { description: e.target.value })
                        }
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Cron Schedule (optional)</Label>
                        <Input
                          value={dep.schedule?.cron || ""}
                          placeholder="0 2 * * *"
                          onChange={(e) =>
                            handleDeploymentChange(index, {
                              schedule: e.target.value
                                ? { cron: e.target.value, timezone: dep.schedule?.timezone || "UTC" }
                                : undefined,
                            })
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Timezone</Label>
                        <Input
                          value={dep.schedule?.timezone || "UTC"}
                          onChange={(e) =>
                            handleDeploymentChange(index, {
                              schedule: dep.schedule
                                ? { ...dep.schedule, timezone: e.target.value }
                                : undefined,
                            })
                          }
                          disabled={!dep.schedule?.cron}
                        />
                      </div>
                    </div>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </ScrollArea>
        </div>

        <Separator />

        {/* prefect.yaml Preview */}
        <div className="space-y-2">
          <h3 className="font-medium">prefect.yaml Preview</h3>
          <ScrollArea className="h-[200px] rounded-md border">
            <pre className="p-4 text-xs font-mono whitespace-pre">{prefectYamlPreview}</pre>
          </ScrollArea>
        </div>
      </div>
    </WizardStep>
  );
}
