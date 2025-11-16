import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { conversationAPI } from '../../services/api';
import { Send, Sparkles, LogOut } from 'lucide-react';

export default function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [child, setChild] = useState(null);
  const messagesEndRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    const storedChild = sessionStorage.getItem('current_child');
    if (!storedChild) {
      navigate('/kid-login');
      return;
    }
    setChild(JSON.parse(storedChild));

    // Welcome message
    setMessages([{
      role: 'assistant',
      content: `Hi ${JSON.parse(storedChild).display_name}! 👋 I'm Nia, your learning buddy! What would you like to learn about today?`,
      timestamp: new Date().toISOString()
    }]);
  }, [navigate]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = {
      role: 'child',
      content: input.trim(),
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await conversationAPI.sendMessage({
        child_id: child.id.toString(),
        text: userMessage.content,
        grade_level: `${child.grade_level} grade`,
        current_depth: 1
      });

      const aiMessage = {
        role: 'assistant',
        content: response.data.text,
        sources: response.data.source_citations,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "Oops! I had trouble understanding that. Can you try asking again? 🤔",
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem('current_child');
    navigate('/kid-login');
  };

  if (!child) return null;

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-kid-purple via-kid-pink to-kid-yellow">
      {/* Header */}
      <div className="bg-white shadow-md px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-kid-purple to-kid-pink rounded-full flex items-center justify-center text-white font-bold">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <h1 className="font-bold text-gray-900 font-kid text-lg">
              Chat with Nia
            </h1>
            <p className="text-sm text-gray-600 font-kid">Learning is fun! 🌟</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="text-gray-600 hover:text-gray-900 transition-colors"
        >
          <LogOut className="w-5 h-5" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === 'child' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl p-4 ${
                message.role === 'child'
                  ? 'bg-white text-gray-900'
                  : 'bg-gradient-to-r from-kid-blue to-kid-green text-white'
              } shadow-lg`}
            >
              <p className="font-kid text-lg whitespace-pre-wrap">{message.content}</p>
              {message.sources && message.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-white/20">
                  <p className="text-sm opacity-90 font-kid">
                    📚 I found this in my learning materials!
                  </p>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gradient-to-r from-kid-blue to-kid-green text-white rounded-2xl p-4 shadow-lg">
              <div className="flex gap-2">
                <div className="w-3 h-3 bg-white rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-3 h-3 bg-white rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-3 h-3 bg-white rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-white border-t border-gray-200 p-4">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me anything! 🤔"
            className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-full focus:ring-2 focus:ring-kid-purple focus:border-transparent outline-none font-kid text-lg"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="kid-button disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-6 h-6" />
          </button>
        </form>
      </div>
    </div>
  );
}
