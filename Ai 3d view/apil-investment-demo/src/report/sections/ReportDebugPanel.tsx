import { useState } from 'react';
import { MessageSquare, Send, Loader2, ChevronDown, ChevronUp } from 'lucide-react';

interface ReportDebugPanelProps {
  topRec: any;
  property: any;
  investorStrategy?: any;
}

export function ReportDebugPanel({ topRec, property, investorStrategy }: ReportDebugPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<{role: 'user' | 'bot'; text: string}[]>([]);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<any[]>([]);

  // Extract report context from current report data
  const reportContext = buildReportContext(topRec, property, investorStrategy);

  async function ask(q: string) {
    if (!q.trim()) return;
    setMessages(prev => [...prev, { role: 'user', text: q }]);
    setQuestion('');
    setLoading(true);

    try {
      const res = await fetch('http://localhost:8765/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: q, history, report_context: reportContext }),
      });
      const data = await res.json();
      if (data.error) {
        setMessages(prev => [...prev, { role: 'bot', text: 'Error: ' + data.error }]);
      } else {
        setMessages(prev => [...prev, { role: 'bot', text: data.reply }]);
        setHistory(data.history || []);
      }
    } catch (e: any) {
      setMessages(prev => [...prev, { role: 'bot', text: 'Error: ' + e.message }]);
    }
    setLoading(false);
  }

  const presets = [
    'Why is the score ' + (topRec?.investmentScore ?? '—') + '?',
    'Why is exit strategy "' + (investorStrategy?.exit_strategy ?? '—') + '"?',
    'Where does fair value come from?',
    'What is the ROE formula for this property?',
    'Why is future value N/A?',
  ];

  return (
    <div className="premium-card p-5 mt-6 border-l-4 border-purple-500">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
            <MessageSquare className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <h3 className="font-semibold text-apil-gray-900">Debug This Report</h3>
            <p className="text-xs text-apil-gray-500">
              {expanded ? 'Ask anything about this specific report' : 'Ask the AI why any number is what it is'}
            </p>
          </div>
        </div>
        {expanded ? <ChevronUp className="w-5 h-5 text-apil-gray-400" /> : <ChevronDown className="w-5 h-5 text-apil-gray-400" />}
      </button>

      {expanded && (
        <div className="mt-4 pt-4 border-t border-apil-gray-100">
          {/* Chat messages */}
          <div className="bg-gray-50 rounded-lg p-3 max-h-[400px] overflow-y-auto space-y-3 mb-3">
            {messages.length === 0 && (
              <div className="text-xs text-apil-gray-500 italic">
                👋 Ask about this specific report. The bot knows every number shown above.
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`text-sm ${m.role === 'user' ? 'text-right' : 'text-left'}`}>
                <div
                  className={`inline-block px-3 py-2 rounded-lg whitespace-pre-wrap leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-apil-blue text-white max-w-[85%]'
                      : 'bg-white border border-gray-200 text-apil-gray-800 max-w-[95%]'
                  }`}
                >
                  {m.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="text-left">
                <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white border border-gray-200 text-apil-gray-500 text-sm">
                  <Loader2 className="w-3 h-3 animate-spin" /> Thinking...
                </div>
              </div>
            )}
          </div>

          {/* Preset questions */}
          <div className="flex flex-wrap gap-2 mb-3">
            {presets.map((p, i) => (
              <button
                key={i}
                onClick={() => ask(p)}
                className="px-3 py-1.5 bg-purple-50 text-purple-700 text-xs rounded-full border border-purple-100 hover:bg-purple-100 transition-colors"
              >
                {p}
              </button>
            ))}
          </div>

          {/* Input */}
          <div className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && ask(question)}
              placeholder="Ask about this report..."
              className="flex-1 px-3 py-2 text-sm border border-apil-gray-200 rounded-lg focus:outline-none focus:border-purple-500"
            />
            <button
              onClick={() => ask(question)}
              disabled={loading || !question.trim()}
              className="px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function buildReportContext(topRec: any, property: any, strategy: any) {
  const tp = topRec || {};
  const prop = property || {};
  const strat = strategy || {};
  const val = tp.valuation || {};
  const risk = tp.risk || {};
  const future = tp.futureAppreciation || {};
  const evidence = tp.evidence || {};
  const fit = tp.investorFit || {};
  const returns = tp.returns || {};

  return {
    property: {
      name: prop.title || tp.title || '—',
      project: prop.project || tp.project || '—',
      area: prop.area || tp.area || '—',
      developer: prop.developerName || tp.developer || '—',
      status: prop.status || tp.propertyType || '—',
      askingPrice: prop.askingPrice || tp.askingPrice || null,
      sizeSqft: prop.sizeSqft || tp.sizeSqft || null,
      bedType: prop.bedType || tp.bedType || '—',
    },
    scores: {
      investmentScore: tp.investmentScore ?? null,
      readyScore: tp.readyScore ?? null,
      offplanScore: tp.offplanScore ?? null,
      recommendation: tp.recommendation || '—',
      scoreLabel: tp.scoreLabel || '—',
    },
    components: tp.scoreComponents || {},
    valuation: {
      fairValue: val.fairValue || val.fairValuePointEstimate || null,
      priceDiffPct: val.priceDifferencePct ?? tp.priceDifferencePct ?? null,
      comparableSales: evidence.comparableSalesCount ?? evidence.projectSalesCount ?? null,
      method: val.method || '—',
    },
    risk: {
      overallRisk: risk.overallRisk ?? null,
      riskLevel: risk.riskLevel || tp.riskLevel || '—',
      components: risk.components || {},
    },
    futureAppreciation: {
      futureValue: future.futureValue ?? null,
      capitalGainPct: future.capitalGainPct ?? future.potentialGainPct ?? null,
      growthRate: future.growthRate ?? null,
      holdingYears: future.holdingYears ?? null,
      completionYears: future.completionYears ?? null,
      growthSource: future.growthSource || 'none',
    },
    returns: {
      netYield: returns.netYield ?? returns.netYieldPct ?? null,
      grossYield: returns.grossYield ?? returns.grossYieldPct ?? null,
      roePct: returns.totalReturn?.roePct ?? null,
      totalReturnPct: returns.totalReturn?.totalReturnPct ?? null,
    },
    exitStrategy: strat.exit_strategy || '—',
    strategySummary: strat.strategy_summary || '—',
    investorFit: {
      fitScore: fit.fitScore ?? null,
      fitLabel: fit.fitLabel || '—',
      matchReasons: fit.matchReasons || [],
      mismatchReasons: fit.mismatchReasons || [],
    },
    evidence: {
      ...evidence,
      comparableSales: evidence.comparableSalesCount ?? evidence.projectSalesCount ?? null,
      comparableRentals: evidence.comparableRentalsCount ?? evidence.areaRentalsCount ?? null,
      evidenceLevel: evidence.evidenceLevel || '—',
      confidenceLevel: evidence.confidenceLevel || '—',
      hasRentalEvidence: evidence.hasRentalEvidence ?? null,
    },
    fullReport: tp,
  };
}
