import { useEffect, useState } from "react";
import { useWizard } from "../WizardProvider";
import { WizardStep } from "../WizardStep";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Folder,
  File,
  ChevronRight,
  ChevronDown,
  Download,
  Copy,
  Check,
  FileCode,
} from "lucide-react";
import type { ProjectTreeNode } from "@/types";
import JSZip from "jszip";

// Generate mock project tree from state
function generateProjectTree(state: ReturnType<typeof useWizard>["state"]): ProjectTreeNode {
  const { projectConfig, conversions, conversionOptions } = state;

  const flowDirs: ProjectTreeNode[] = Array.from(conversions.entries()).map(([_path, conv]) => {
    const flowName = conv.dagId.replace(/_/g, "-");
    const children: ProjectTreeNode[] = [
      {
        name: "flow.py",
        type: "file",
        path: `deployments/${projectConfig.workspace}/${flowName}/flow.py`,
        content: conv.flowCode,
      },
      {
        name: "requirements.txt",
        type: "file",
        path: `deployments/${projectConfig.workspace}/${flowName}/requirements.txt`,
        content: "prefect>=3.0.0\n",
      },
    ];

    if (conversionOptions.generateTests && conv.testCode) {
      children.push({
        name: "test_flow.py",
        type: "file",
        path: `deployments/${projectConfig.workspace}/${flowName}/test_flow.py`,
        content: conv.testCode,
      });
    }

    if (projectConfig.includeDockerfile) {
      children.push({
        name: "Dockerfile",
        type: "file",
        path: `deployments/${projectConfig.workspace}/${flowName}/Dockerfile`,
        content: `FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "flow.py"]
`,
      });
    }

    return {
      name: flowName,
      type: "directory",
      path: `deployments/${projectConfig.workspace}/${flowName}`,
      children,
    };
  });

  // Workspace directory
  const workspaceDir: ProjectTreeNode = {
    name: projectConfig.workspace,
    type: "directory",
    path: `deployments/${projectConfig.workspace}`,
    children: [
      {
        name: "prefect.yaml",
        type: "file",
        path: `deployments/${projectConfig.workspace}/prefect.yaml`,
        content: generatePrefectYaml(state),
      },
      ...flowDirs,
    ],
  };

  // Root project
  const root: ProjectTreeNode = {
    name: projectConfig.projectName,
    type: "directory",
    path: projectConfig.projectName,
    children: [
      {
        name: ".gitignore",
        type: "file",
        path: `${projectConfig.projectName}/.gitignore`,
        content: `__pycache__/
*.py[cod]
.venv/
venv/
.prefect/
.env
.env.local
`,
      },
      {
        name: ".prefectignore",
        type: "file",
        path: `${projectConfig.projectName}/.prefectignore`,
        content: `**/test_*.py
**/*_test.py
**/tests/
.git/
__pycache__/
`,
      },
      {
        name: "README.md",
        type: "file",
        path: `${projectConfig.projectName}/README.md`,
        content: `# ${projectConfig.projectName}

${projectConfig.description || "Prefect flows migrated from Airflow."}

## Setup

\`\`\`bash
pip install -r requirements.txt
\`\`\`

## Deployment

\`\`\`bash
prefect deploy --all --prefect-file deployments/${projectConfig.workspace}/prefect.yaml
\`\`\`
`,
      },
      {
        name: "deployments",
        type: "directory",
        path: `${projectConfig.projectName}/deployments`,
        children: [workspaceDir],
      },
    ],
  };

  if (projectConfig.includePyproject) {
    root.children?.unshift({
      name: "pyproject.toml",
      type: "file",
      path: `${projectConfig.projectName}/pyproject.toml`,
      content: `[project]
name = "${projectConfig.projectName}"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = [
    "prefect>=3.0.0",
]
`,
    });
  }

  return root;
}

function generatePrefectYaml(state: ReturnType<typeof useWizard>["state"]): string {
  const { projectConfig, deploymentConfig, conversions } = state;

  const deployments = Array.from(conversions.entries()).map(([_, conv]) => {
    const flowName = conv.dagId.replace(/_/g, "-");
    return `  - name: ${flowName}
    entrypoint: deployments/${projectConfig.workspace}/${flowName}/flow.py:${conv.dagId}
    work_pool:
      name: ${deploymentConfig.workPool.name}`;
  });

  return `name: ${projectConfig.projectName}
prefect-version: 3.0.0

pull:
  - prefect.deployments.steps.git_clone:
      repository: https://github.com/your-org/${projectConfig.projectName}
      branch: main

deployments:
${deployments.join("\n\n")}
`;
}

interface TreeNodeProps {
  node: ProjectTreeNode;
  selectedPath: string | null;
  onSelect: (node: ProjectTreeNode) => void;
  level: number;
}

function TreeNode({ node, selectedPath, onSelect, level }: TreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(level < 2);
  const isSelected = selectedPath === node.path;

  if (node.type === "file") {
    return (
      <button
        onClick={() => onSelect(node)}
        className={`flex items-center gap-2 w-full px-2 py-1 text-left text-sm hover:bg-muted/50 rounded ${
          isSelected ? "bg-muted" : ""
        }`}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
      >
        <File className="w-4 h-4 text-muted-foreground flex-shrink-0" />
        <span className="truncate">{node.name}</span>
      </button>
    );
  }

  return (
    <div>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 w-full px-2 py-1 text-left text-sm hover:bg-muted/50 rounded"
        style={{ paddingLeft: `${level * 16 + 8}px` }}
      >
        {isExpanded ? (
          <ChevronDown className="w-4 h-4 text-muted-foreground flex-shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
        )}
        <Folder className="w-4 h-4 text-blue-500 flex-shrink-0" />
        <span className="truncate font-medium">{node.name}</span>
      </button>
      {isExpanded && node.children && (
        <div>
          {node.children.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              selectedPath={selectedPath}
              onSelect={onSelect}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function ExportView() {
  const { state } = useWizard();
  const [projectTree, setProjectTree] = useState<ProjectTreeNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<ProjectTreeNode | null>(null);
  const [copiedPath, setCopiedPath] = useState<string | null>(null);

  useEffect(() => {
    const tree = generateProjectTree(state);
    setProjectTree(tree);
  }, [state]);

  const handleCopyFile = async (node: ProjectTreeNode) => {
    if (node.content) {
      await navigator.clipboard.writeText(node.content);
      setCopiedPath(node.path);
      setTimeout(() => setCopiedPath(null), 2000);
    }
  };

  const handleDownloadZip = async () => {
    if (!projectTree) return;

    const zip = new JSZip();

    const addToZip = (node: ProjectTreeNode, parentPath: string = "") => {
      const currentPath = parentPath ? `${parentPath}/${node.name}` : node.name;

      if (node.type === "file" && node.content) {
        zip.file(currentPath, node.content);
      } else if (node.children) {
        node.children.forEach((child) => addToZip(child, currentPath));
      }
    };

    addToZip(projectTree);

    const blob = await zip.generateAsync({ type: "blob" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${state.projectConfig.projectName}.zip`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const fileCount = (() => {
    let count = 0;
    const countFiles = (node: ProjectTreeNode) => {
      if (node.type === "file") count++;
      node.children?.forEach(countFiles);
    };
    if (projectTree) countFiles(projectTree);
    return count;
  })();

  return (
    <WizardStep
      title="Export Project"
      description="Review and download your generated Prefect project."
      hideNav
    >
      <div className="space-y-4">
        {/* Summary */}
        <div className="flex items-center justify-between p-4 rounded-lg border bg-muted/30">
          <div className="flex items-center gap-4">
            <div>
              <p className="font-medium">{state.projectConfig.projectName}</p>
              <p className="text-sm text-muted-foreground">
                {fileCount} files, {state.conversions.size} flows
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={handleDownloadZip}>
              <Download className="w-4 h-4 mr-2" />
              Download ZIP
            </Button>
          </div>
        </div>

        {/* File browser */}
        <div className="grid grid-cols-2 gap-4 h-[400px]">
          {/* Tree view */}
          <div className="border rounded-lg overflow-hidden">
            <div className="px-3 py-2 bg-muted/50 border-b">
              <span className="text-sm font-medium">Project Files</span>
            </div>
            <ScrollArea className="h-[356px]">
              {projectTree && (
                <div className="py-2">
                  <TreeNode
                    node={projectTree}
                    selectedPath={selectedNode?.path || null}
                    onSelect={setSelectedNode}
                    level={0}
                  />
                </div>
              )}
            </ScrollArea>
          </div>

          {/* File preview */}
          <div className="border rounded-lg overflow-hidden">
            <div className="px-3 py-2 bg-muted/50 border-b flex items-center justify-between">
              <span className="text-sm font-medium">
                {selectedNode?.name || "Select a file"}
              </span>
              {selectedNode?.type === "file" && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleCopyFile(selectedNode)}
                >
                  {copiedPath === selectedNode.path ? (
                    <>
                      <Check className="w-4 h-4 mr-1" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4 mr-1" />
                      Copy
                    </>
                  )}
                </Button>
              )}
            </div>
            <ScrollArea className="h-[356px]">
              {selectedNode?.type === "file" && selectedNode.content ? (
                <pre className="p-4 text-xs font-mono whitespace-pre-wrap">
                  {selectedNode.content}
                </pre>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                  <FileCode className="w-12 h-12 mb-2 opacity-50" />
                  <p>Select a file to preview</p>
                </div>
              )}
            </ScrollArea>
          </div>
        </div>

        {/* Actions */}
        <Separator />
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Your project is ready! Download the ZIP file or copy individual files.
          </p>
          <div className="flex items-center gap-2">
            <Badge variant="success">Migration Complete</Badge>
          </div>
        </div>
      </div>
    </WizardStep>
  );
}
