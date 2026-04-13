import { NavLink, Link } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';

export const Navbar = () => {
  return (
    <nav className="sticky top-0 z-50 w-full border-b border-border-default bg-background-primary/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          
          {/* Logo Section */}
          <Link to="/" className="flex items-center gap-2 group">
            <ShieldCheck className="h-6 w-6 text-accent-blue transition-transform group-hover:scale-110" />
            <span className="font-bold text-lg tracking-tight text-text-primary">
              Headline<span className="text-accent-blue">Verifier</span>
            </span>
          </Link>

          {/* Navigation Links */}
          <div className="flex gap-6">
            <NavLink
              to="/"
              className={({ isActive }) =>
                `text-sm font-medium transition-colors hover:text-text-primary ${
                  isActive ? 'text-text-primary' : 'text-text-secondary'
                }`
              }
            >
              Home
            </NavLink>
            <NavLink
              to="/verify"
              className={({ isActive }) =>
                `text-sm font-medium transition-colors hover:text-text-primary ${
                  isActive ? 'text-text-primary' : 'text-text-secondary'
                }`
              }
            >
              Verify
            </NavLink>
          </div>

        </div>
      </div>
    </nav>
  );
};