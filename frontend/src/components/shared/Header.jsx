import { useAuth } from '../../context/AuthContext';
import { LogOut, User } from 'lucide-react';

export default function Header() {
  const { user, logout } = useAuth();

  return (
    <header className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <h1 className="text-2xl font-bold text-primary-600">Nia</h1>
            <span className="ml-2 text-sm text-gray-500">AI Learning Assistant</span>
          </div>
          
          {user && (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <User className="w-5 h-5 text-gray-600" />
                <span className="text-sm font-medium">{user.full_name}</span>
              </div>
              <button
                onClick={logout}
                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
              >
                <LogOut className="w-5 h-5" />
                <span className="text-sm">Logout</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
