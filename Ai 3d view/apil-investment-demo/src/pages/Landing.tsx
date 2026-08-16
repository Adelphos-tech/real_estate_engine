import { Link } from 'react-router-dom';
import { ArrowRight, Shield, UserCheck, BarChart3 } from 'lucide-react';

export default function Landing() {
  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden bg-apil-blue">
        <div className="absolute inset-0 opacity-20" style={{ backgroundImage: "url('https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=1800&q=80')", backgroundSize: 'cover', backgroundPosition: 'center' }} />
        <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/30" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-28">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm rounded-full px-4 py-1.5 mb-6">
              <Shield className="w-4 h-4 text-apil-gold" />
              <span className="text-white text-xs font-medium">Objective investment decisions locked by verified DLD data</span>
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white leading-tight">
              Find Your Best Dubai Property Investment
            </h1>
            <p className="mt-4 text-lg text-white/90 leading-relaxed max-w-2xl">
              APIL separates objective investment signal from personal fit. We rank opportunities using verified DLD transaction benchmarks — then match them to your goals.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row gap-3">
              <Link to="/questionnaire" className="inline-flex items-center justify-center gap-2 bg-apil-gold text-white font-semibold px-7 py-3.5 rounded-xl hover:bg-apil-gold-light transition-colors text-base">
                Start Investment Analysis <ArrowRight className="w-4 h-4" />
              </Link>
              <Link to="/marketplace" className="inline-flex items-center justify-center gap-2 bg-white/10 backdrop-blur-sm border border-white/20 text-white font-semibold px-7 py-3.5 rounded-xl hover:bg-white/15 transition-colors text-base">
                Browse Marketplace
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-16 lg:py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-apil-gray-900">How APIL Works</h2>
            <p className="mt-2 text-apil-gray-500">Two independent layers — objective signal first, your fit second</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="premium-card p-6">
              <div className="w-12 h-12 rounded-xl bg-apil-blue/10 text-apil-blue flex items-center justify-center mb-4">
                <BarChart3 className="w-6 h-6" />
              </div>
              <h3 className="font-semibold text-apil-gray-900 mb-2">1. Objective Signal</h3>
              <p className="text-sm text-apil-gray-500 leading-relaxed">
                Every property is scored against verified DLD transaction benchmarks. Price advantage, evidence strength, and developer grade are locked — never modified by preferences.
              </p>
            </div>
            <div className="premium-card p-6">
              <div className="w-12 h-12 rounded-xl bg-apil-blue/10 text-apil-blue flex items-center justify-center mb-4">
                <UserCheck className="w-6 h-6" />
              </div>
              <h3 className="font-semibold text-apil-gray-900 mb-2">2. Your Investor Fit</h3>
              <p className="text-sm text-apil-gray-500 leading-relaxed">
                Complete a short questionnaire. We compute a 0-100 fit score based on budget, location, risk tolerance, and property preferences — without changing the objective decision.
              </p>
            </div>
            <div className="premium-card p-6">
              <div className="w-12 h-12 rounded-xl bg-apil-blue/10 text-apil-blue flex items-center justify-center mb-4">
                <Shield className="w-6 h-6" />
              </div>
              <h3 className="font-semibold text-apil-gray-900 mb-2">3. Safe Ranking</h3>
              <p className="text-sm text-apil-gray-500 leading-relaxed">
                Ranked by: decision tier → fit score → best usable advantage → evidence strength → developer grade → price. AVOID never outranks OPPORTUNITY, regardless of fit.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Safety rules */}
      <section className="bg-apil-gray-100 py-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold text-apil-gray-900">Safety First</h2>
            <p className="mt-2 text-apil-gray-500">What you see is what the data says. No manipulation.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              'Objective decisions are immutable — your profile cannot upgrade AVOID to OPPORTUNITY.',
              'Price advantage is hidden when benchmarks are not usable for investment.',
              'INSUFFICIENT_EVIDENCE properties are excluded from the default marketplace view.',
              'Fit score (0-100) is computed independently from the locked investment decision.',
              'Developer grade is based on historical DLD delivery and resale premium data.',
              'Area-level benchmarks are never presented as project-level evidence.',
            ].map((text, i) => (
              <div key={i} className="bg-white rounded-xl p-4 flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">✓</div>
                <p className="text-sm text-apil-gray-700">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold text-apil-gray-900">Ready to find your next investment?</h2>
          <p className="mt-3 text-apil-gray-500">Get a personalised opportunity ranking in 2 minutes. No phone number required.</p>
          <Link to="/questionnaire" className="mt-6 inline-flex items-center gap-2 bg-apil-blue text-white font-semibold px-8 py-4 rounded-xl hover:bg-apil-blue-dark transition-colors text-lg">
            Start Investment Analysis <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>
    </div>
  );
}
