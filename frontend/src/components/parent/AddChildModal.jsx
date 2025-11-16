import { useState } from 'react';
import { childrenAPI } from '../../services/api';
import { X, AlertCircle } from 'lucide-react';

export default function AddChildModal({ onClose, onChildAdded }) {
  const [formData, setFormData] = useState({
    first_name: '',
    nickname: '',
    date_of_birth: '',
    grade_level: '',
    pin: '',
    confirmPin: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const grades = [
    'Kindergarten', '1st', '2nd', '3rd', '4th', '5th',
    '6th', '7th', '8th', '9th', '10th', '11th', '12th'
  ];

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validate PIN
    if (formData.pin !== formData.confirmPin) {
      setError('PINs do not match');
      return;
    }

    if (!/^\d{4}$/.test(formData.pin)) {
      setError('PIN must be exactly 4 digits');
      return;
    }

    setLoading(true);
    try {
      const { confirmPin, ...childData } = formData;
      await childrenAPI.create(childData);
      onChildAdded();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add child');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Add Child</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              First Name *
            </label>
            <input
              type="text"
              name="first_name"
              value={formData.first_name}
              onChange={handleChange}
              className="input"
              placeholder="Emma"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nickname (Optional)
            </label>
            <input
              type="text"
              name="nickname"
              value={formData.nickname}
              onChange={handleChange}
              className="input"
              placeholder="Em"
            />
            <p className="text-xs text-gray-500 mt-1">
              This will be displayed throughout the app
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Date of Birth *
            </label>
            <input
              type="date"
              name="date_of_birth"
              value={formData.date_of_birth}
              onChange={handleChange}
              className="input"
              max={new Date().toISOString().split('T')[0]}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Grade Level *
            </label>
            <select
              name="grade_level"
              value={formData.grade_level}
              onChange={handleChange}
              className="input"
              required
            >
              <option value="">Select grade...</option>
              {grades.map(grade => (
                <option key={grade} value={grade}>{grade}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              4-Digit PIN *
            </label>
            <input
              type="password"
              name="pin"
              value={formData.pin}
              onChange={handleChange}
              className="input"
              placeholder="1234"
              maxLength="4"
              pattern="\d{4}"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Child will use this PIN to access their account
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confirm PIN *
            </label>
            <input
              type="password"
              name="confirmPin"
              value={formData.confirmPin}
              onChange={handleChange}
              className="input"
              placeholder="1234"
              maxLength="4"
              pattern="\d{4}"
              required
            />
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 btn-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 btn-primary disabled:opacity-50"
            >
              {loading ? 'Adding...' : 'Add Child'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
