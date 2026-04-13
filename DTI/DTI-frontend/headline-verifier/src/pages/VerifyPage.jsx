import { useEffect, useState, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';
import { useVerification } from '../hooks/useVerification';
import { useImageVerification } from '../hooks/useImageVerification';
import { ClaimInput } from '../components/verify/ClaimInput';
import { ImageUpload } from '../components/verify/ImageUpload';
import { LoadingState } from '../components/verify/LoadingState';
import { ErrorState } from '../components/verify/ErrorState';
import { VerdictCard } from '../components/verify/VerdictCard';
import { ExplanationBlock } from '../components/verify/ExplanationBlock';
import { ConfidenceBreakdownPanel } from '../components/verify/ConfidenceBreakdownPanel';
import { AgreementSignalPanel } from '../components/verify/AgreementSignalPanel';
import { EvidenceList } from '../components/verify/EvidenceList';
import { ImageVerificationResult } from '../components/verify/ImageVerificationResult';

export const VerifyPage = () => {
  const location = useLocation();
  const initialClaim = location.state?.claim || '';
  
  // Track the current claim and verification mode
  const [currentClaim, setCurrentClaim] = useState(initialClaim);
  const [activeTab, setActiveTab] = useState('text'); // 'text' or 'image'
  const resultRef = useRef(null);

  const {
    mutate: verifyClaim,
    isPending: isTextPending,
    isError: isTextError,
    isSuccess: isTextSuccess,
    data: textResult,
    error: textError,
    reset: resetText,
  } = useVerification();

  const {
    mutate: verifyImageFile,
    isPending: isImagePending,
    isError: isImageError,
    isSuccess: isImageSuccess,
    data: imageResult,
    error: imageError,
    reset: resetImage,
  } = useImageVerification();

  const handleTextVerifySubmit = (claimText) => {
    setCurrentClaim(claimText);
    resetText();
    verifyClaim(claimText);
  };

  const handleImageVerifySubmit = (file) => {
    resetImage();
    verifyImageFile({ file, claim: null });
  };

  const handleRetry = () => {
    if (activeTab === 'text' && currentClaim) {
      resetText();
      verifyClaim(currentClaim);
    }
  };

  // Auto-submit if we navigated here with a sample claim
  useEffect(() => {
    if (initialClaim && !isTextPending) {
      resetText();
      verifyClaim(initialClaim);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Accessibility polish: Scroll to results when they finish loading
  useEffect(() => {
    if ((textResult || imageResult) && !isTextPending && !isImagePending && resultRef.current) {
      resultRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [textResult, imageResult, isTextPending, isImagePending]);

  const isTextLoading = isTextPending;
  const isImageLoading = isImagePending;

  return (
    <div className="flex flex-col w-full max-w-4xl mx-auto px-4 sm:px-6 py-8 md:py-12 animate-in fade-in duration-500">
      
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl md:text-3xl font-bold text-text-primary flex items-center gap-3">
          <ShieldCheck className="h-8 w-8 text-accent-blue" />
          Verification Engine
        </h1>
        <p className="text-text-secondary mt-2 text-sm md:text-base">
          Verify text claims or analyze images for manipulation.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="mb-8 relative z-20 flex gap-2 border-b border-border-default">
        <button
          onClick={() => {
            setActiveTab('text');
            resetText();
            resetImage();
          }}
          className={`px-4 py-2 font-medium border-b-2 transition-colors ${
            activeTab === 'text'
              ? 'border-accent-blue text-accent-blue'
              : 'border-transparent text-text-secondary hover:text-text-primary'
          }`}
        >
          Text Verification
        </button>
        <button
          onClick={() => {
            setActiveTab('image');
            resetText();
            resetImage();
          }}
          className={`px-4 py-2 font-medium border-b-2 transition-colors ${
            activeTab === 'image'
              ? 'border-accent-blue text-accent-blue'
              : 'border-transparent text-text-secondary hover:text-text-primary'
          }`}
        >
          Image Analysis
        </button>
      </div>

      {/* Input Section */}
      <div className="mb-8 relative z-20">
        {activeTab === 'text' && (
          <ClaimInput 
            initialClaim={initialClaim} 
            onSubmit={handleTextVerifySubmit} 
            isLoading={isTextLoading} 
          />
        )}
        {activeTab === 'image' && (
          <ImageUpload 
            onImageSelected={handleImageVerifySubmit}
            isLoading={isImageLoading}
          />
        )}
      </div>

      {/* Dynamic Content Area */}
      <div className="flex flex-col gap-6" ref={resultRef}>
        
        {/* Empty State */}
        {activeTab === 'text' && !isTextLoading && !isTextError && !textResult && (
          <div className="text-center py-20 px-4 border border-border-dim border-dashed rounded-xl bg-background-secondary/30 transition-all">
            <p className="text-text-muted text-sm">Awaiting your query. Results will appear here.</p>
          </div>
        )}

        {activeTab === 'image' && !isImageLoading && !isImageError && !imageResult && (
          <div className="text-center py-20 px-4 border border-border-dim border-dashed rounded-xl bg-background-secondary/30 transition-all">
            <p className="text-text-muted text-sm">Upload an image to analyze. Results will appear here.</p>
          </div>
        )}

        {/* Loading State */}
        {(isTextLoading || isImageLoading) && <LoadingState />}

        {/* Error State */}
        {isTextError && <ErrorState error={textError} onRetry={handleRetry} />}
        {isImageError && <ErrorState error={imageError} onRetry={() => resetImage()} />}

        {/* Text Verification Result Dashboard */}
        {isTextSuccess && textResult && !isTextLoading && !isTextError && (
          <div className="flex flex-col gap-6 w-full">
            <VerdictCard 
              claim={textResult.claim}
              verdict={textResult.verdict}
              confidence={textResult.confidence}
              summary={textResult.summary}
              conflictingSources={textResult.conflicting_sources}
            />
            {textResult.confidence_breakdown && (
              <ConfidenceBreakdownPanel breakdown={textResult.confidence_breakdown} />
            )}
            {textResult.agreement_signal && (
              <AgreementSignalPanel signal={textResult.agreement_signal} conflicting={textResult.conflicting_sources} />
            )}
            {textResult.explanation && (
              <ExplanationBlock explanation={textResult.explanation} />
            )}
            {textResult.sources && textResult.sources.length > 0 && (
              <div className="mt-2">
                <EvidenceList sources={textResult.sources} />
              </div>
            )}
          </div>
        )}

        {/* Image Verification Result */}
        {isImageSuccess && imageResult && !isImageLoading && !isImageError && (
          <div className="flex flex-col gap-6 w-full">
            <ImageVerificationResult result={imageResult.image_result} />
            {/* If text claim was also provided, show text results */}
            {imageResult.verdict && (
              <>
                <VerdictCard 
                  claim={imageResult.claim}
                  verdict={imageResult.verdict}
                  confidence={imageResult.confidence}
                  summary={imageResult.summary}
                />
                {imageResult.explanation && (
                  <ExplanationBlock explanation={imageResult.explanation} />
                )}
              </>
            )}
          </div>
        )}

      </div>
    </div>
  );
};


