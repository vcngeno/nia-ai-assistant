import { useState, useEffect } from 'react';
import { dashboardAPI } from '../../services/api';
import { Users, MessageSquare, Clock, TrendingUp, Activity } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Dashboard() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadOverview();
  }, []);

  const loadOverview = async () => {
    try {
      const response = await dashboardAPI.getOverview();
      setOverview(response.data);
    } catch (error) {
      console.error('Failed to load overview:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">Failed to load dashboard data</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-1">Welcome back! Here's what's happening with your children's learning.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          icon={<Users className="w-6 h-6" />}
          label="Active Children"
          value={overview.active_children}
          total={overview.total_children}
          color="blue"
        />
        <StatCard
          icon={<MessageSquare className="w-6 h-6" />}
          label="Conversations"
          value={overview.total_conversations}
          color="green"
        />
        <StatCard
          icon={<Activity className="w-6 h-6" />}
          label="Questions Asked"
          value={overview.total_questions}
          color="purple"
        />
        <StatCard
          icon={<Clock className="w-6 h-6" />}
          label="Hours Learning"
          value={overview.hours_learning.toFixed(1)}
          color="orange"
        />
      </div>

      {/* Most Active Child */}
      {overview.most_active_child && (
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <TrendingUp className="w-6 h-6 text-primary-600" />
            <h2 className="text-xl font-bold text-gray-900">Most Active Learner</h2>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {overview.most_active_child.name}
              </p>
              <p className="text-gray-600 mt-1">
                {overview.most_active_child.questions} questions asked
              </p>
            </div>
            <Link
              to={`/children/${overview.most_active_child.id}`}
              className="btn-primary"
            >
              View Progress
            </Link>
          </div>
        </div>
      )}

      {/* Recent Activity */}
      <div className="card">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Recent Activity</h2>
        
        {overview.recent_activity.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>No recent activity yet</p>
            <p className="text-sm mt-1">Questions will appear here as children interact with Nia</p>
          </div>
        ) : (
          <div className="space-y-4">
            {overview.recent_activity.map((activity, index) => (
              <div
                key={index}
                className="flex items-start gap-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex-shrink-0 w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                  <span className="text-primary-600 font-medium">
                    {activity.child_name[0]}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">
                    {activity.child_name}
                  </p>
                  <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                    {activity.question}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(activity.timestamp).toLocaleString()}
                  </p>
                </div>
                <Link
                  to={`/conversations/${activity.conversation_id}`}
                  className="flex-shrink-0 text-primary-600 hover:text-primary-700 text-sm font-medium"
                >
                  View
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link to="/children" className="card hover:shadow-lg transition-shadow text-center">
          <Users className="w-8 h-8 text-primary-600 mx-auto mb-2" />
          <h3 className="font-medium text-gray-900">Manage Children</h3>
          <p className="text-sm text-gray-600 mt-1">Add or edit child profiles</p>
        </Link>
        
        <Link to="/conversations" className="card hover:shadow-lg transition-shadow text-center">
          <MessageSquare className="w-8 h-8 text-primary-600 mx-auto mb-2" />
          <h3 className="font-medium text-gray-900">View Conversations</h3>
          <p className="text-sm text-gray-600 mt-1">See all learning discussions</p>
        </Link>
        
        <Link to="/analytics" className="card hover:shadow-lg transition-shadow text-center">
          <Activity className="w-8 h-8 text-primary-600 mx-auto mb-2" />
          <h3 className="font-medium text-gray-900">Learning Analytics</h3>
          <p className="text-sm text-gray-600 mt-1">Detailed insights and trends</p>
        </Link>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, total, color }) {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    purple: 'bg-purple-100 text-purple-600',
    orange: 'bg-orange-100 text-orange-600',
  };

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
      <div className="mt-4">
        <p className="text-sm text-gray-600">{label}</p>
        <p className="text-3xl font-bold text-gray-900 mt-1">
          {value}
          {total && <span className="text-lg text-gray-500">/{total}</span>}
        </p>
      </div>
    </div>
  );
}
