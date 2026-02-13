// DAG and Analysis Types
export interface DagFile {
  path: string;
  name: string;
  complexity: "simple" | "medium" | "complex";
  selected: boolean;
}

export interface OperatorInfo {
  name: string;
  type: string;
  taskId: string;
  supported: boolean;
  prefectEquivalent?: string;
  notes?: string;
}

export interface DependencyInfo {
  taskCount: number;
  edgeCount: number;
  graphType: "linear" | "fan-out" | "fan-in" | "complex";
  edges: [string, string][];
}

export interface FeatureFlags {
  taskflow: boolean;
  datasets: boolean;
  sensors: boolean;
  customOperators: boolean;
  dynamicTasks: boolean;
  taskGroups: boolean;
  triggerRules: boolean;
  jinjaTemplates: boolean;
}

export interface Warning {
  severity: "warning" | "error";
  message: string;
  line?: number;
  suggestion?: string;
}

export interface DagAnalysis {
  dagId: string;
  filePath: string;
  operators: OperatorInfo[];
  dependencies: DependencyInfo;
  features: FeatureFlags;
  complexityScore: number;
  warnings: Warning[];
  airflowVersion?: string;
}

// Conversion Types
export interface ConversionOptions {
  includeComments: boolean;
  generateTests: boolean;
  generateRunbook: boolean;
  preserveAirflowComments: boolean;
  outputStructure: "flat" | "prefect-flows" | "custom";
  customTemplate?: string;
}

export interface ConversionResult {
  dagId: string;
  success: boolean;
  flowCode: string;
  testCode?: string;
  runbook?: string;
  warnings: string[];
  error?: string;
}

// Validation Types
export interface ValidationIssue {
  type: "task_count" | "dependency" | "xcom" | "other";
  severity: "error" | "warning";
  message: string;
  details?: string;
}

export interface ValidationResult {
  dagId: string;
  isValid: boolean;
  confidenceScore: number;
  taskCountMatch: boolean;
  dependencyPreserved: boolean;
  issues: ValidationIssue[];
  dagTasks: string[];
  flowTasks: string[];
  dagEdges: [string, string][];
  flowEdges: [string, string][];
}

// Project Types
export interface ProjectConfig {
  projectName: string;
  workspace: string;
  description: string;
  includePyproject: boolean;
  includeDockerfile: boolean;
  includeGithubActions: boolean;
  includePrecommit: boolean;
  includeMise: boolean;
  dependencies: string[];
}

export interface DeploymentSpec {
  flowId: string;
  name: string;
  description: string;
  schedule?: {
    cron: string;
    timezone: string;
  };
  parameters?: Record<string, unknown>;
  concurrencyLimit?: number;
  concurrencyOptions?: {
    collisionStrategy: "ENQUEUE" | "CANCEL_NEW";
  };
}

export interface DeploymentConfig {
  workPool: {
    name: string;
    type: "process" | "docker" | "kubernetes";
  };
  docker?: {
    registry: string;
    imageTemplate: string;
  };
  deployments: DeploymentSpec[];
}

// Project Tree Types
export interface ProjectTreeNode {
  name: string;
  type: "directory" | "file";
  path: string;
  children?: ProjectTreeNode[];
  content?: string;
}

// Wizard State
export type WizardStep = 1 | 2 | 3 | 4 | 5 | 6 | 7;

export interface WizardState {
  // Navigation
  currentStep: WizardStep;
  completedSteps: Set<number>;

  // Step 1: DAG Selection
  dagsDirectory: string;
  dagFiles: DagFile[];
  selectedDags: string[];

  // Step 2: Analysis Results
  analyses: Map<string, DagAnalysis>;
  analysisStatus: "idle" | "loading" | "complete" | "error";
  analysisError?: string;

  // Step 3: Conversion Config
  conversionOptions: ConversionOptions;
  dagOverrides: Map<string, Partial<ConversionOptions>>;

  // Step 4: Validation
  conversions: Map<string, ConversionResult>;
  validations: Map<string, ValidationResult>;
  conversionStatus: "idle" | "converting" | "validating" | "complete" | "error";
  conversionProgress: number;
  conversionError?: string;

  // Step 5: Project Setup
  projectConfig: ProjectConfig;
  detectedDependencies: string[];

  // Step 6: Deployment Config
  deploymentConfig: DeploymentConfig;

  // Step 7: Export
  generatedProject: ProjectTreeNode | null;
  exportStatus: "idle" | "generating" | "complete" | "error";
}

export type WizardAction =
  | { type: "SET_STEP"; step: WizardStep }
  | { type: "COMPLETE_STEP"; step: number }
  | { type: "SET_DAGS_DIRECTORY"; directory: string }
  | { type: "SET_DAG_FILES"; files: DagFile[] }
  | { type: "SELECT_DAGS"; paths: string[] }
  | { type: "TOGGLE_DAG"; path: string }
  | { type: "SET_ANALYSIS_STATUS"; status: WizardState["analysisStatus"]; error?: string }
  | { type: "SET_ANALYSES"; analyses: Map<string, DagAnalysis> }
  | { type: "SET_CONVERSION_OPTIONS"; options: Partial<ConversionOptions> }
  | { type: "SET_DAG_OVERRIDE"; dagId: string; override: Partial<ConversionOptions> }
  | { type: "SET_CONVERSION_STATUS"; status: WizardState["conversionStatus"]; progress?: number; error?: string }
  | { type: "SET_CONVERSION_RESULT"; dagId: string; result: ConversionResult }
  | { type: "SET_VALIDATION_RESULT"; dagId: string; result: ValidationResult }
  | { type: "SET_PROJECT_CONFIG"; config: Partial<ProjectConfig> }
  | { type: "SET_DETECTED_DEPENDENCIES"; dependencies: string[] }
  | { type: "SET_DEPLOYMENT_CONFIG"; config: Partial<DeploymentConfig> }
  | { type: "SET_DEPLOYMENT_SPEC"; index: number; spec: Partial<DeploymentSpec> }
  | { type: "ADD_DEPLOYMENT"; spec: DeploymentSpec }
  | { type: "REMOVE_DEPLOYMENT"; index: number }
  | { type: "SET_GENERATED_PROJECT"; project: ProjectTreeNode }
  | { type: "SET_EXPORT_STATUS"; status: WizardState["exportStatus"] }
  | { type: "RESET" };
