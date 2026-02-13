import React, { createContext, useContext, useReducer, useCallback, type ReactNode } from "react";
import type {
  WizardState,
  WizardAction,
  WizardStep,
  ConversionOptions,
  ProjectConfig,
  DeploymentConfig,
} from "@/types";

const defaultConversionOptions: ConversionOptions = {
  includeComments: true,
  generateTests: true,
  generateRunbook: true,
  preserveAirflowComments: false,
  outputStructure: "prefect-flows",
};

const defaultProjectConfig: ProjectConfig = {
  projectName: "prefect-flows",
  workspace: "default",
  description: "",
  includePyproject: true,
  includeDockerfile: true,
  includeGithubActions: false,
  includePrecommit: false,
  includeMise: false,
  dependencies: [],
};

const defaultDeploymentConfig: DeploymentConfig = {
  workPool: {
    name: "default-pool",
    type: "process",
  },
  deployments: [],
};

const initialState: WizardState = {
  currentStep: 1,
  completedSteps: new Set(),
  dagsDirectory: "",
  dagFiles: [],
  selectedDags: [],
  analyses: new Map(),
  analysisStatus: "idle",
  conversionOptions: defaultConversionOptions,
  dagOverrides: new Map(),
  conversions: new Map(),
  validations: new Map(),
  conversionStatus: "idle",
  conversionProgress: 0,
  projectConfig: defaultProjectConfig,
  detectedDependencies: [],
  deploymentConfig: defaultDeploymentConfig,
  generatedProject: null,
  exportStatus: "idle",
};

function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case "SET_STEP":
      return { ...state, currentStep: action.step };

    case "COMPLETE_STEP":
      return {
        ...state,
        completedSteps: new Set([...state.completedSteps, action.step]),
      };

    case "SET_DAGS_DIRECTORY":
      return { ...state, dagsDirectory: action.directory };

    case "SET_DAG_FILES":
      return { ...state, dagFiles: action.files };

    case "SELECT_DAGS":
      return {
        ...state,
        selectedDags: action.paths,
        dagFiles: state.dagFiles.map((f) => ({
          ...f,
          selected: action.paths.includes(f.path),
        })),
      };

    case "TOGGLE_DAG": {
      const isSelected = state.selectedDags.includes(action.path);
      const newSelected = isSelected
        ? state.selectedDags.filter((p) => p !== action.path)
        : [...state.selectedDags, action.path];
      return {
        ...state,
        selectedDags: newSelected,
        dagFiles: state.dagFiles.map((f) => ({
          ...f,
          selected: newSelected.includes(f.path),
        })),
      };
    }

    case "SET_ANALYSIS_STATUS":
      return {
        ...state,
        analysisStatus: action.status,
        analysisError: action.error,
      };

    case "SET_ANALYSES":
      return { ...state, analyses: action.analyses };

    case "SET_CONVERSION_OPTIONS":
      return {
        ...state,
        conversionOptions: { ...state.conversionOptions, ...action.options },
      };

    case "SET_DAG_OVERRIDE": {
      const newOverrides = new Map(state.dagOverrides);
      newOverrides.set(action.dagId, action.override);
      return { ...state, dagOverrides: newOverrides };
    }

    case "SET_CONVERSION_STATUS":
      return {
        ...state,
        conversionStatus: action.status,
        conversionProgress: action.progress ?? state.conversionProgress,
        conversionError: action.error,
      };

    case "SET_CONVERSION_RESULT": {
      const newConversions = new Map(state.conversions);
      newConversions.set(action.dagId, action.result);
      return { ...state, conversions: newConversions };
    }

    case "SET_VALIDATION_RESULT": {
      const newValidations = new Map(state.validations);
      newValidations.set(action.dagId, action.result);
      return { ...state, validations: newValidations };
    }

    case "SET_PROJECT_CONFIG":
      return {
        ...state,
        projectConfig: { ...state.projectConfig, ...action.config },
      };

    case "SET_DETECTED_DEPENDENCIES":
      return { ...state, detectedDependencies: action.dependencies };

    case "SET_DEPLOYMENT_CONFIG":
      return {
        ...state,
        deploymentConfig: { ...state.deploymentConfig, ...action.config },
      };

    case "SET_DEPLOYMENT_SPEC": {
      const newDeployments = [...state.deploymentConfig.deployments];
      newDeployments[action.index] = {
        ...newDeployments[action.index],
        ...action.spec,
      };
      return {
        ...state,
        deploymentConfig: { ...state.deploymentConfig, deployments: newDeployments },
      };
    }

    case "ADD_DEPLOYMENT":
      return {
        ...state,
        deploymentConfig: {
          ...state.deploymentConfig,
          deployments: [...state.deploymentConfig.deployments, action.spec],
        },
      };

    case "REMOVE_DEPLOYMENT": {
      const newDeployments = state.deploymentConfig.deployments.filter(
        (_, i) => i !== action.index
      );
      return {
        ...state,
        deploymentConfig: { ...state.deploymentConfig, deployments: newDeployments },
      };
    }

    case "SET_GENERATED_PROJECT":
      return { ...state, generatedProject: action.project };

    case "SET_EXPORT_STATUS":
      return { ...state, exportStatus: action.status };

    case "RESET":
      return initialState;

    default:
      return state;
  }
}

interface WizardContextValue {
  state: WizardState;
  dispatch: React.Dispatch<WizardAction>;
  goToStep: (step: WizardStep) => void;
  nextStep: () => void;
  prevStep: () => void;
  canGoNext: () => boolean;
  canGoPrev: () => boolean;
}

const WizardContext = createContext<WizardContextValue | null>(null);

export function WizardProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(wizardReducer, initialState);

  const goToStep = useCallback((step: WizardStep) => {
    dispatch({ type: "SET_STEP", step });
  }, []);

  const nextStep = useCallback(() => {
    if (state.currentStep < 7) {
      dispatch({ type: "COMPLETE_STEP", step: state.currentStep });
      dispatch({ type: "SET_STEP", step: (state.currentStep + 1) as WizardStep });
    }
  }, [state.currentStep]);

  const prevStep = useCallback(() => {
    if (state.currentStep > 1) {
      dispatch({ type: "SET_STEP", step: (state.currentStep - 1) as WizardStep });
    }
  }, [state.currentStep]);

  const canGoNext = useCallback(() => {
    switch (state.currentStep) {
      case 1:
        return state.selectedDags.length > 0;
      case 2:
        return state.analysisStatus === "complete" && state.analyses.size > 0;
      case 3:
        return true;
      case 4:
        return state.conversionStatus === "complete";
      case 5:
        return state.projectConfig.projectName.length > 0;
      case 6:
        return state.deploymentConfig.workPool.name.length > 0;
      case 7:
        return false; // Last step
      default:
        return false;
    }
  }, [state]);

  const canGoPrev = useCallback(() => {
    return state.currentStep > 1;
  }, [state.currentStep]);

  return (
    <WizardContext.Provider
      value={{ state, dispatch, goToStep, nextStep, prevStep, canGoNext, canGoPrev }}
    >
      {children}
    </WizardContext.Provider>
  );
}

export function useWizard(): WizardContextValue {
  const context = useContext(WizardContext);
  if (!context) {
    throw new Error("useWizard must be used within a WizardProvider");
  }
  return context;
}
