// ─── VERIFY-X 2.0 — Main Application ───

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/common/Navbar';
import Home from './pages/Home';
import Results from './pages/Results';
import History from './pages/History';
import About from './pages/About';
import './index.css';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Navbar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/results/:id" element={<Results />} />
            <Route path="/history" element={<History />} />
            <Route path="/about" element={<About />} />
          </Routes>
        </main>
        <footer className="app-footer">
          <div className="footer-content">
            <span>VERIFY-X 2.0</span>
            <span className="footer-sep">·</span>
            <span>Multimodal AI Fact Verification</span>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}
