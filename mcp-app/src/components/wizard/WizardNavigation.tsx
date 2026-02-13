import { useWizard } from "./WizardProvider";
import { cn } from "@/lib/utils";
import {
  FolderOpen,
  Search,
  Settings,
  CheckCircle,
  Package,
  Rocket,
  Download,
} from "lucide-react";
import type { WizardStep } from "@/types";

interface Step {
  number: WizardStep;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const steps: Step[] = [
  { number: 1, label: "Select", icon: FolderOpen },
  { number: 2, label: "Analysis", icon: Search },
  { number: 3, label: "Configure", icon: Settings },
  { number: 4, label: "Validate", icon: CheckCircle },
  { number: 5, label: "Project", icon: Package },
  { number: 6, label: "Deploy", icon: Rocket },
  { number: 7, label: "Export", icon: Download },
];

export function WizardNavigation() {
  const { state, goToStep } = useWizard();

  return (
    <nav className="mb-8">
      <ol className="flex items-center justify-between">
        {steps.map((step, index) => {
          const isActive = state.currentStep === step.number;
          const isCompleted = state.completedSteps.has(step.number);
          const isClickable = isCompleted || step.number < state.currentStep;
          const Icon = step.icon;

          return (
            <li key={step.number} className="flex items-center flex-1">
              <button
                onClick={() => isClickable && goToStep(step.number)}
                disabled={!isClickable}
                className={cn(
                  "flex flex-col items-center gap-1 group w-full",
                  isClickable && "cursor-pointer",
                  !isClickable && "cursor-default"
                )}
              >
                <div
                  className={cn(
                    "w-10 h-10 rounded-full flex items-center justify-center border-2 transition-colors",
                    isActive && "border-primary bg-primary text-primary-foreground",
                    isCompleted && !isActive && "border-wizard-success bg-wizard-success text-white",
                    !isActive && !isCompleted && "border-muted-foreground/30 text-muted-foreground"
                  )}
                >
                  {isCompleted && !isActive ? (
                    <CheckCircle className="w-5 h-5" />
                  ) : (
                    <Icon className="w-5 h-5" />
                  )}
                </div>
                <span
                  className={cn(
                    "text-xs font-medium transition-colors",
                    isActive && "text-foreground",
                    !isActive && "text-muted-foreground"
                  )}
                >
                  {step.label}
                </span>
              </button>
              {index < steps.length - 1 && (
                <div
                  className={cn(
                    "flex-1 h-0.5 mx-2",
                    state.completedSteps.has(step.number)
                      ? "bg-wizard-success"
                      : "bg-muted-foreground/20"
                  )}
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
