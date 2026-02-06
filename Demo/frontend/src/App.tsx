/**
 * Main App Component
 */
import { useState, useEffect } from 'react';
import { Activity, AlertCircle } from 'lucide-react';
import ChatInterface from './components/ChatInterface';
import MetricsPanel from './components/MetricsPanel';
import { healthCheck } from './api/agent';

function App() {
  const [healthStatus, setHealthStatus] = useState<'checking' | 'healthy' | 'degraded'>('checking');

  useEffect(() => {
    checkHealth();
    // Check health every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
    try {
      const health = await healthCheck();
      setHealthStatus(health.status === 'healthy' ? 'healthy' : 'degraded');
    } catch (error) {
      setHealthStatus('degraded');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">AI-Agentic Architecture Demo</h1>
              <p className="text-sm text-gray-600 mt-1">
                Showcasing intelligent routing, caching, and clarification
              </p>
            </div>

            {/* Health indicator */}
            <div className="flex items-center gap-2">
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
                healthStatus === 'healthy'
                  ? 'bg-green-100 text-green-800'
                  : healthStatus === 'degraded'
                  ? 'bg-yellow-100 text-yellow-800'
                  : 'bg-gray-100 text-gray-600'
              }`}>
                {healthStatus === 'checking' ? (
                  <>
                    <Activity className="w-4 h-4 animate-pulse" />
                    <span>Checking...</span>
                  </>
                ) : healthStatus === 'healthy' ? (
                  <>
                    <Activity className="w-4 h-4" />
                    <span>Healthy</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-4 h-4" />
                    <span>Degraded</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Chat interface (2/3 width on large screens) */}
          <div className="lg:col-span-2 h-[calc(100vh-200px)]">
            <ChatInterface />
          </div>

          {/* Metrics panel (1/3 width on large screens) */}
          <div className="lg:col-span-1">
            <MetricsPanel />

            {/* Info card */}
            <div className="mt-6 bg-white rounded-lg shadow-md p-6 border border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">
                Demo Scenarios
              </h3>
              <div className="space-y-3 text-sm">
                <DemoScenario
                  title="Ambiguous Query"
                  example="Find claims for John"
                  description="Shows clarification widget with 3 patients"
                />
                <DemoScenario
                  title="Multi-Step Reasoning"
                  example="What is the total for John Smith?"
                  description="Agent chains 3 tools: query → get_claims → calculate"
                />
                <DemoScenario
                  title="Direct Query"
                  example="Get claims for patient PAT-12345"
                  description="No ambiguity, direct answer"
                />
              </div>
            </div>

            {/* Architecture highlights */}
            <div className="mt-6 bg-gradient-to-br from-primary-50 to-blue-50 rounded-lg shadow-md p-6 border border-primary-200">
              <h3 className="text-lg font-semibold text-primary-900 mb-3">
                Key Differentiators
              </h3>
              <div className="space-y-3">
                <FeatureHighlight
                  emoji="🧠"
                  title="LLM Gateway"
                  description="Intelligent routing, 90% cost savings via caching"
                />
                <FeatureHighlight
                  emoji="💬"
                  title="Clarification Engine"
                  description="Turns errors into conversations, no dead ends"
                />
                <FeatureHighlight
                  emoji="🔄"
                  title="Iterative Reasoning"
                  description="Agent adapts and self-corrects via tool chains"
                />
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-12 pb-6 text-center text-sm text-gray-500">
        <p>AI-Agentic Architecture Demo • Built with FastAPI + React + PostgreSQL</p>
      </footer>
    </div>
  );
}

interface DemoScenarioProps {
  title: string;
  example: string;
  description: string;
}

function DemoScenario({ title, example, description }: DemoScenarioProps) {
  return (
    <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
      <h4 className="font-medium text-gray-900 mb-1">{title}</h4>
      <p className="text-primary-600 font-mono text-xs mb-2">"{example}"</p>
      <p className="text-gray-600 text-xs">{description}</p>
    </div>
  );
}

interface FeatureHighlightProps {
  emoji: string;
  title: string;
  description: string;
}

function FeatureHighlight({ emoji, title, description }: FeatureHighlightProps) {
  return (
    <div className="flex items-start gap-3">
      <span className="text-2xl">{emoji}</span>
      <div>
        <h4 className="font-semibold text-primary-900 text-sm">{title}</h4>
        <p className="text-primary-700 text-xs mt-1">{description}</p>
      </div>
    </div>
  );
}

export default App;
