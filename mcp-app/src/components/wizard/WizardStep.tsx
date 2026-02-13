import type { ReactNode } from "react";
import { useWizard } from "./WizardProvider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface WizardStepProps {
  title: string;
  description?: string;
  children: ReactNode;
  nextLabel?: string;
  onNext?: () => void | Promise<void>;
  isNextLoading?: boolean;
  hideNav?: boolean;
}

export function WizardStep({
  title,
  description,
  children,
  nextLabel = "Next",
  onNext,
  isNextLoading = false,
  hideNav = false,
}: WizardStepProps) {
  const { state, nextStep, prevStep, canGoNext, canGoPrev } = useWizard();

  const handleNext = async () => {
    if (onNext) {
      await onNext();
    }
    nextStep();
  };

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-6">
        {children}

        {!hideNav && (
          <div className="flex justify-between pt-4 border-t">
            <Button
              variant="outline"
              onClick={prevStep}
              disabled={!canGoPrev()}
            >
              <ChevronLeft className="w-4 h-4 mr-2" />
              Back
            </Button>

            {state.currentStep < 7 && (
              <Button
                onClick={handleNext}
                disabled={!canGoNext() || isNextLoading}
              >
                {isNextLoading ? (
                  <>
                    <span className="animate-spin mr-2">⏳</span>
                    Processing...
                  </>
                ) : (
                  <>
                    {nextLabel}
                    <ChevronRight className="w-4 h-4 ml-2" />
                  </>
                )}
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
