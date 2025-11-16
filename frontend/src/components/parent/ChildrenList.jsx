import { useState, useEffect } from 'react';
import { childrenAPI } from '../../services/api';
import { Plus, Calendar, GraduationCap, Shield, Edit2, Trash2 } from 'lucide-react';
import AddChildModal from './AddChildModal';

export default function ChildrenList() {
  const [children, setChildren] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);

  useEffect(() => {
    loadChildren();
  }, []);

  const loadChildren = async () => {
    try {
      const response = await childrenAPI.getAll();
      setChildren(response.data);
    } catch (error) {
      console.error('Failed to load children:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleChildAdded = () => {
    setShowAddModal(false);
    loadChildren();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Children</h1>
          <p className="text-gray-600 mt-1">Manage your children's profiles and settings</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          Add Child
        </button>
      </div>

      {children.length === 0 ? (
        <div className="card text-center py-12">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Plus className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No children yet</h3>
          <p className="text-gray-600 mb-6">Add your first child to get started with Nia</p>
          <button
            onClick={() => setShowAddModal(true)}
            className="btn-primary inline-flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Add Child
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {children.map((child) => (
            <ChildCard key={child.id} child={child} onUpdate={loadChildren} />
          ))}
        </div>
      )}

      {showAddModal && (
        <AddChildModal
          onClose={() => setShowAddModal(false)}
          onChildAdded={handleChildAdded}
        />
      )}
    </div>
  );
}

function ChildCard({ child, onUpdate }) {
  return (
    <div className="card hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-gradient-to-br from-primary-400 to-primary-600 rounded-full flex items-center justify-center text-white font-bold text-lg">
            {child.display_name[0]}
          </div>
          <div>
            <h3 className="text-lg font-bold text-gray-900">{child.display_name}</h3>
            <p className="text-sm text-gray-600">{child.first_name}</p>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <Calendar className="w-4 h-4" />
          <span>Age: {child.age} years old</span>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <GraduationCap className="w-4 h-4" />
          <span>Grade: {child.grade_level}</span>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <Shield className="w-4 h-4" />
          <span className="capitalize">Filter: {child.content_filter_level}</span>
        </div>
      </div>

      <div className="mt-6 pt-4 border-t border-gray-200 flex items-center gap-2">
        <button className="flex-1 btn-secondary flex items-center justify-center gap-2 text-sm">
          <Edit2 className="w-4 h-4" />
          Edit
        </button>
        <button className="btn-secondary text-red-600 hover:bg-red-50 flex items-center justify-center gap-2 text-sm">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
