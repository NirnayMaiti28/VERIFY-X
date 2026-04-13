import { Routes, Route } from 'react-router-dom';
import { Navbar } from './components/layout/Navbar';
import { Footer } from './components/layout/Footer';
import {HomePage} from './pages/HomePage'; // Temporarily default imports if you haven't changed them yet
import {VerifyPage} from './pages/VerifyPage';

export const App = () => {
  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <main className="flex-1 flex flex-col">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/verify" element={<VerifyPage />} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
};

export default App; // Keeping default export here just for standard Vite entrypoint