import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginForm from './components/auth/LoginForm';
import RegisterForm from './components/auth/RegisterForm';
import Dashboard from './components/parent/Dashboard';
import ChildrenList from './components/parent/ChildrenList';
import PINLogin from './components/child/PINLogin';
import ChatInterface from './components/child/ChatInterface';
import Header from './components/shared/Header';

function PrivateRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return user ? children : <Navigate to="/login" />;
}

function AppContent() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50">
      {user && <Header />}
      
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={user ? <Navigate to="/dashboard" /> : <LoginForm />} />
        <Route path="/register" element={user ? <Navigate to="/dashboard" /> : <RegisterForm />} />
        
        {/* Kid Routes (No Auth Required) */}
        <Route path="/kid-login" element={<PINLogin />} />
        <Route path="/chat" element={<ChatInterface />} />
        
        {/* Parent Routes (Auth Required) */}
        <Route path="/dashboard" element={
          <PrivateRoute>
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              <Dashboard />
            </div>
          </PrivateRoute>
        } />
        
        <Route path="/children" element={
          <PrivateRoute>
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              <ChildrenList />
            </div>
          </PrivateRoute>
        } />
        
        {/* Default Route */}
        <Route path="/" element={<Navigate to={user ? "/dashboard" : "/login"} />} />
      </Routes>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
