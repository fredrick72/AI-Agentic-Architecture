/**
 * Metrics Panel - Display real-time agent metrics
 */
import { useEffect, useState } from 'react';
import { TrendingUp, DollarSign, Zap, Database } from 'lucide-react';
import { getAgentStats } from '../api/agent';
import type { AgentStats } from '../types';

export default function MetricsPanel() {
  const [stats, setStats] = useState<AgentStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
    // Refresh every 10 seconds
    const interval = setInterval(loadStats, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadStats = async () => {
    try {
      const data = await getAgentStats();
      setStats(data);
      setError(null);
    } catch (err) {
      setError('Failed to load stats');
      console.error('Stats error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="space-y-3">
            <div className="h-8 bg-gray-200 rounded"></div>
            <div className="h-8 bg-gray-200 rounded"></div>
            <div className="h-8 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 rounded-lg p-4 border border-red-200">
        <p className="text-red-800 text-sm">{error}</p>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200">
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-primary-600" />
          Live Metrics
        </h3>
      </div>

      <div className="p-4 space-y-4">
        {/* Total Cost */}
        <MetricCard
          icon={<DollarSign className="w-5 h-5 text-green-600" />}
          label="Total Cost (7 days)"
          value={`$${stats.cost_summary.total_cost.toFixed(4)}`}
          subtitle={`${stats.cost_summary.conversation_count} conversations`}
          trend={stats.cost_trends.avg_daily_cost > 0 ? 'up' : 'neutral'}
        />

        {/* Monthly Estimate */}
        <MetricCard
          icon={<DollarSign className="w-5 h-5 text-blue-600" />}
          label="Estimated Monthly"
          value={`$${stats.monthly_estimate.estimated_monthly_cost.toFixed(2)}`}
          subtitle={`Based on ${stats.monthly_estimate.based_on_days} days`}
          trend="neutral"
        />

        {/* Total Tokens */}
        <MetricCard
          icon={<Zap className="w-5 h-5 text-yellow-600" />}
          label="Total Tokens"
          value={stats.cost_summary.total_tokens.toLocaleString()}
          subtitle={`Avg $${stats.cost_summary.avg_cost_per_conversation.toFixed(4)}/conv`}
          trend="neutral"
        />

        {/* Conversations */}
        <MetricCard
          icon={<Database className="w-5 h-5 text-purple-600" />}
          label="Conversations"
          value={stats.total_conversations.toString()}
          subtitle="All time"
          trend="neutral"
        />
      </div>

      {/* Daily Trend (last 3 days) */}
      {stats.cost_trends.daily_breakdown.length > 0 && (
        <div className="p-4 border-t border-gray-200">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Daily Cost Trend</h4>
          <div className="space-y-2">
            {stats.cost_trends.daily_breakdown.slice(-3).reverse().map((day) => (
              <div key={day.date} className="flex items-center justify-between text-sm">
                <span className="text-gray-600">
                  {new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-gray-900 font-medium">${day.cost.toFixed(4)}</span>
                  <span className="text-gray-500 text-xs">({day.turn_count} turns)</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  subtitle: string;
  trend: 'up' | 'down' | 'neutral';
}

function MetricCard({ icon, label, value, subtitle, trend }: MetricCardProps) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 border border-gray-100">
      <div className="flex-shrink-0 mt-1">{icon}</div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-gray-600 font-medium mb-1">{label}</p>
        <p className="text-xl font-bold text-gray-900 mb-1">{value}</p>
        <p className="text-xs text-gray-500">{subtitle}</p>
      </div>
      {trend !== 'neutral' && (
        <div className={`flex-shrink-0 text-xs font-medium ${
          trend === 'up' ? 'text-green-600' : 'text-red-600'
        }`}>
          {trend === 'up' ? '↑' : '↓'}
        </div>
      )}
    </div>
  );
}
