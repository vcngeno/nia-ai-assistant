import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { childrenAPI } from '../../services/api';
import { Sparkles, AlertCircle } from 'lucide-react';

export default function PINLogin() {
  const [children, setChildren] = useState([]);
  const [selectedChild, setSelectedChild] = useState(null);
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    loadChildren();
  }, []);

  const loadChildren = async () => {
    try {
      const response = await childrenAPI.getAll();
      setChildren(response.data);
    } catch (error) {
      console.error('Failed to load children:', error);
    }
  };

  const handlePinInput = (digit) => {
    if (pin.length < 4) {
      setPin(pin + digit);
    }
  };

  const handleBackspace = () => {
    setPin(pin.slice(0, -1));
  };

  const handleSubmit = async () => {
    if (!selectedChild || pin.length !== 4) return;

    setLoading(true);
    setError('');

    try {
      const response = await childrenAPI.verifyPIN({
        child_id: selectedChild.id,
        pin: pin
      });

      if (response.data.verified) {
        // Store child session
        sessionStorage.setItem('current_child', JSON.stringify(response.data.child));
        navigate('/chat');
      }
    } catch (err) {
      setError('Incorrect PIN. Please try again.');
      setPin('');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (pin.length === 4) {
      handleSubmit();
    }
  }, [pin]);

  if (children.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-kid-purple via-kid-pink to-kid-yellow p-4">
        <div className="card text-center max-w-md">
          <p className="text-gray-600">No children profiles found. Please ask your parent to add you!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-kid-purple via-kid-pink to-kid-yellow p-4">
      <div className="max-w-md w-full">
        {!selectedChild ? (
          <div className="space-y-4">
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-20 h-20 bg-white rounded-full shadow-lg mb-4">
                <Sparkles className="w-10 h-10 text-kid-purple" />
              </div>
              <h1 className="text-4xl font-bold text-white mb-2 font-kid">
                Hi! I'm Nia! ✨
              </h1>
              <p className="text-white text-lg font-kid">Who are you?</p>
            </div>

            <div className="space-y-3">
              {children.map(child => (
                <button
                  key={child.id}
                  onClick={() => setSelectedChild(child)}
                  className="w-full bg-white hover:bg-gray-50 rounded-2xl p-6 transition-all transform hover:scale-105 shadow-lg"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-16 h-16 bg-gradient-to-br from-kid-purple to-kid-pink rounded-full flex items-center justify-center text-white font-bold text-2xl font-kid">
                      {child.display_name[0]}
                    </div>
                    <div className="text-left">
                      <p className="text-2xl font-bold text-gray-900 font-kid">
                        {child.display_name}
                      </p>
                      <p className="text-gray-600 font-kid">Grade {child.grade_level}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-3xl p-8 shadow-2xl">
            <button
              onClick={() => {
                setSelectedChild(null);
                setPin('');
                setError('');
              }}
              className="text-gray-600 hover:text-gray-900 mb-6 font-kid"
            >
              ← Back
            </button>

            <div className="text-center mb-8">
              <div className="w-20 h-20 bg-gradient-to-br from-kid-purple to-kid-pink rounded-full flex items-center justify-center text-white font-bold text-3xl mx-auto mb-4 font-kid">
                {selectedChild.display_name[0]}
              </div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2 font-kid">
                Hi, {selectedChild.display_name}! 👋
              </h2>
              <p className="text-gray-600 font-kid text-lg">
                Enter your PIN to start learning!
              </p>
            </div>

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-red-600" />
                <p className="text-sm text-red-600 font-kid">{error}</p>
              </div>
            )}

            {/* PIN Display */}
            <div className="flex justify-center gap-3 mb-8">
              {[0, 1, 2, 3].map(i => (
                <div
                  key={i}
                  className={`w-16 h-16 rounded-xl border-4 flex items-center justify-center text-3xl font-bold ${
                    pin.length > i
                      ? 'bg-kid-purple border-kid-purple text-white'
                      : 'bg-gray-100 border-gray-300 text-gray-300'
                  }`}
                >
                  {pin.length > i ? '●' : ''}
                </div>
              ))}
            </div>

            {/* Number Pad */}
            <div className="grid grid-cols-3 gap-3">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9].map(num => (
                <button
                  key={num}
                  onClick={() => handlePinInput(num.toString())}
                  disabled={loading}
                  className="h-16 bg-gray-100 hover:bg-gray-200 rounded-xl text-2xl font-bold text-gray-900 transition-colors disabled:opacity-50 font-kid"
                >
                  {num}
                </button>
              ))}
              <div /> {/* Empty cell */}
              <button
                onClick={() => handlePinInput('0')}
                disabled={loading}
                className="h-16 bg-gray-100 hover:bg-gray-200 rounded-xl text-2xl font-bold text-gray-900 transition-colors disabled:opacity-50 font-kid"
              >
                0
              </button>
              <button
                onClick={handleBackspace}
                disabled={loading}
                className="h-16 bg-red-100 hover:bg-red-200 rounded-xl text-xl font-bold text-red-600 transition-colors disabled:opacity-50 font-kid"
              >
                ←
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
