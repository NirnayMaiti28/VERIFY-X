import { HeroSection } from '../components/home/HeroSection';
import { HowItWorksSection } from '../components/home/HowItWorksSection';
import { StatsSection } from '../components/home/StatsSection';
import { SampleClaimsSection } from '../components/home/SampleClaimsSection';

export const HomePage = () => {
  return (
    <div className="flex flex-col w-full animate-in fade-in duration-500">
      <HeroSection />
      <StatsSection />
      <HowItWorksSection />
      <SampleClaimsSection />
    </div>
  );
};

export default HomePage; // Keeping default export here just for standard routing, though named export is provided.