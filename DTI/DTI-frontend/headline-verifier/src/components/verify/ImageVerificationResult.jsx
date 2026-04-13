import { ShieldCheck, AlertTriangle } from 'lucide-react';
import { Badge } from '../ui/Badge';

export const ImageVerificationResult = ({ result }) => {
  if (!result) return null;

  const { is_fake, confidence, probabilities, explanation, error } = result;

  if (error) {
    return (
      <div className="w-full bg-background-card border border-verdict-false/30 rounded-xl p-6">
        <div className="flex items-start gap-4">
          <AlertTriangle className="h-6 w-6 text-verdict-false flex-shrink-0 mt-1" />
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              Image Analysis Failed
            </h3>
            <p className="text-text-secondary">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (is_fake === null) {
    return (
      <div className="w-full bg-background-card border border-text-muted/30 rounded-xl p-6">
        <p className="text-text-secondary text-center">
          {explanation || 'Unable to analyze the image.'}
        </p>
      </div>
    );
  }

  const statusColor = is_fake ? 'verdict-false' : 'verdict-true';
  const statusText = is_fake ? 'Manipulated/Fake' : 'Authentic/Real';
  const confidencePercent = (confidence * 100).toFixed(1);

  return (
    <div className={`w-full bg-background-card border border-${statusColor}/30 rounded-xl p-6`}>
      <div className="flex items-start gap-4">
        <div className={`h-12 w-12 rounded-lg bg-${statusColor}/20 flex items-center justify-center flex-shrink-0`}>
          {is_fake ? (
            <AlertTriangle className={`h-6 w-6 text-${statusColor}`} />
          ) : (
            <ShieldCheck className={`h-6 w-6 text-${statusColor}`} />
          )}
        </div>

        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-lg font-semibold text-text-primary">
              Image Detection
            </h3>
            <Badge variant={is_fake ? 'false' : 'true'}>
              {statusText}
            </Badge>
          </div>

          <p className="text-text-secondary mb-4">
            {explanation}
          </p>

          {/* Confidence bars */}
          <div className="space-y-2">
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-xs font-medium text-text-secondary">Fake</span>
                <span className="text-xs font-semibold text-text-primary">
                  {(probabilities.fake * 100).toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-background-secondary h-2 rounded-full overflow-hidden">
                <div
                  className="h-full bg-verdict-false transition-all duration-300"
                  style={{ width: `${probabilities.fake * 100}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-1">
                <span className="text-xs font-medium text-text-secondary">Real</span>
                <span className="text-xs font-semibold text-text-primary">
                  {(probabilities.real * 100).toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-background-secondary h-2 rounded-full overflow-hidden">
                <div
                  className="h-full bg-verdict-true transition-all duration-300"
                  style={{ width: `${probabilities.real * 100}%` }}
                />
              </div>
            </div>
          </div>

          <div className="mt-4 text-center">
            <span className="text-sm font-semibold text-text-primary">
              Confidence: {confidencePercent}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
