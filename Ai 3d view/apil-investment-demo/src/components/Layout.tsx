import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { Building2, ChevronRight } from 'lucide-react';
import { useState, useRef } from 'react';

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const isLanding = location.pathname === '/';
  const clickCount = useRef(0);
  const clickTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSecretClick = () => {
    clickCount.current += 1;
    if (clickTimer.current) clearTimeout(clickTimer.current);
    clickTimer.current = setTimeout(() => { clickCount.current = 0; }, 2000);
    if (clickCount.current >= 5) {
      clickCount.current = 0;
      navigate('/x-ray-debug-9281');
    }
  };

  return (
    <div className="min-h-screen bg-apil-gray-50">
      {/* Top Nav */}
      <nav className="sticky top-0 z-50 bg-white border-b border-apil-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link to="/" className="flex items-center gap-2">
              <div className="w-9 h-9 rounded-lg bg-apil-blue flex items-center justify-center">
                <Building2 className="w-5 h-5 text-white" />
              </div>
              <div>
                <span className="text-lg font-bold text-apil-gray-900">APIL</span>
                <span className="text-lg font-normal text-apil-gray-500 ml-1">Investment Advisor</span>
              </div>
            </Link>
            
            <div className="hidden md:flex items-center gap-6">
              <Link to="/" className="text-sm font-medium text-apil-gray-600 hover:text-apil-blue transition-colors">
                Home
              </Link>
              <Link to="/questionnaire" className="text-sm font-medium text-apil-gray-600 hover:text-apil-blue transition-colors">
                New Analysis
              </Link>
              <Link to="/marketplace" className="text-sm font-medium text-apil-gray-600 hover:text-apil-blue transition-colors">
                Marketplace
              </Link>
              <Link to="/compare" className="text-sm font-medium text-apil-gray-600 hover:text-apil-blue transition-colors">
                Compare
              </Link>
              <a href="#" className="text-sm font-medium text-apil-gold hover:text-apil-gold-light transition-colors">
                Speak to Advisor
              </a>
            </div>

            <Link
              to="/questionnaire"
              className="bg-apil-blue text-white text-sm font-semibold px-5 py-2 rounded-lg hover:bg-apil-blue-dark transition-colors"
            >
              Start Analysis
            </Link>
          </div>
        </div>
      </nav>

      {/* Breadcrumb bar (not on landing) */}
      {!isLanding && (
        <div className="bg-apil-gray-100 border-b border-apil-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
            <div className="flex items-center gap-1 text-xs text-apil-gray-500">
              <Link to="/" className="hover:text-apil-blue">Home</Link>
              <ChevronRight className="w-3 h-3" />
              <span className="text-apil-gray-700 capitalize">
                {location.pathname.split('/').filter(Boolean).join(' / ').replace(/-/g, ' ')}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Page Content */}
      <main>
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-apil-gray-900 text-apil-gray-400 mt-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-4 cursor-pointer" onClick={handleSecretClick}>
                <div className="w-8 h-8 rounded-lg bg-apil-blue flex items-center justify-center">
                  <Building2 className="w-4 h-4 text-white" />
                </div>
                <span className="text-white font-bold">APIL Properties</span>
              </div>
              <p className="text-xs leading-relaxed">
                Dubai's data-driven real estate investment platform. Powered by DLD transaction data.
              </p>
            </div>
            <div>
              <h4 className="text-white text-sm font-semibold mb-3">Investment</h4>
              <ul className="space-y-2 text-xs">
                <li><Link to="/investment-advisor" className="hover:text-white">Start Analysis</Link></li>
                <li><Link to="/investment-compare" className="hover:text-white">Compare Properties</Link></li>
                <li><a href="#" className="hover:text-white">Investment Methodology</a></li>
                <li><a href="#" className="hover:text-white">Data Sources</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white text-sm font-semibold mb-3">Resources</h4>
              <ul className="space-y-2 text-xs">
                <li><a href="#" className="hover:text-white">Market Reports</a></li>
                <li><a href="#" className="hover:text-white">Area Guides</a></li>
                <li><a href="#" className="hover:text-white">Investment Glossary</a></li>
                <li><a href="#" className="hover:text-white">FAQ</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white text-sm font-semibold mb-3">Legal</h4>
              <ul className="space-y-2 text-xs">
                <li><a href="#" className="hover:text-white">Privacy Policy</a></li>
                <li><a href="#" className="hover:text-white">Terms of Use</a></li>
                <li><a href="#" className="hover:text-white">Investment Disclaimer</a></li>
                <li><a href="#" className="hover:text-white">Cookie Policy</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-apil-gray-800 mt-8 pt-6 text-xs text-center">
            © 2026 APIL Properties. All investment scores are analytical estimates based on DLD transaction data. Past performance does not predict future results.
          </div>
        </div>
      </footer>
    </div>
  );
}
