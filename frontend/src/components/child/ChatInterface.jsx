import { useState, useEffect, useRef } from 'react';
import { conversationAPI } from '../../services/api';
import { ThumbsUp, ThumbsDown } from 'lucide-react';

export default function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const messagesEndRef = useRef(null);

  const childId = "1";
  const gradeLevel = "3rd Grade";

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleFeedback = async (messageId, rating) => {
    try {
      await conversationAPI.submitFeedback(messageId, rating);
      setMessages(messages.map(msg => 
        msg.id === messageId ? { ...msg, feedbackGiven: rating } : msg
      ));
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = {
      id: Date.now(),
      role: 'child',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await conversationAPI.sendMessage({
        conversation_id: conversationId,
        child_id: childId,
        text: input,
        grade_level: gradeLevel,
        current_depth: 1
      });

      setConversationId(response.conversation_id);

      const aiMessage = {
        id: response.message_id,
        role: 'assistant',
        content: response.text,
        sourceLabel: response.source_label,
        visualContent: response.visual_content,
        timestamp: new Date(),
        feedbackGiven: null
      };

      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [...prev, {
        id: Date.now(),
        role: 'assistant',
        content: "Oops! I had trouble understanding that. Can you try asking again? 🤔",
        timestamp: new Date()
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-purple-50 to-blue-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-purple-100">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
            Chat with Nia
          </h1>
          <p className="text-sm text-gray-600 mt-1">Your AI Learning Assistant</p>
        </div>
      </div>

      {/* Messages Container */}
      <div className="max-w-4xl mx-auto px-6 py-6">
        <div className="bg-white rounded-xl shadow-md p-6 mb-4 min-h-[500px] max-h-[600px] overflow-y-auto">
          {messages.length === 0 ? (
            <div className="text-center text-gray-400 py-12">
              <p className="text-lg mb-2">👋 Hi there!</p>
              <p className="text-sm">Ask me anything you're curious about!</p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message, index) => (
                <div key={message.id || index} className={`flex ${message.role === 'child' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[75%] rounded-2xl px-4 py-3 ${
                    message.role === 'child' 
                      ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white' 
                      : 'bg-gray-50 text-gray-900 border border-gray-200'
                  }`}>
                    {/* Source Label */}
                    {message.role === 'assistant' && message.sourceLabel && (
                      <div className="text-xs mb-2 text-gray-500 font-medium">
                        {message.sourceLabel}
                      </div>
                    )}
                    
                    {/* Message Content */}
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>

                    {/* DALL-E Image */}
                    {message.visualContent?.type === 'dalle_image' && (
                      <div className="mt-3">
                        <img
                          src={message.visualContent.image_url}
                          alt={message.visualContent.prompt}
                          className="rounded-lg max-w-full border-2 border-purple-200"
                        />
                        <p className="text-xs mt-2 text-gray-500">
                          🎨 Generated image
                        </p>
                      </div>
                    )}

                    {/* Emoji Visual */}
                    {message.visualContent?.type === 'emoji_visual' && (
                      <div className="mt-2 text-xl">
                        {message.visualContent.emojis?.join(' ')}
                      </div>
                    )}

                    {/* Feedback Buttons */}
                    {message.role === 'assistant' && (
                      <div className="mt-3 pt-3 border-t border-gray-200 flex gap-2">
                        <button
                          onClick={() => handleFeedback(message.id, 1)}
                          className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                            message.feedbackGiven === 1
                              ? 'bg-green-100 text-green-700 border-2 border-green-300'
                              : 'bg-white border-2 border-gray-200 hover:border-green-300 hover:bg-green-50'
                          }`}
                          disabled={message.feedbackGiven !== null}
                        >
                          <ThumbsUp size={14} />
                          {message.feedbackGiven === 1 ? 'Helpful!' : 'Helpful'}
                        </button>
                        <button
                          onClick={() => handleFeedback(message.id, -1)}
                          className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                            message.feedbackGiven === -1
                              ? 'bg-red-100 text-red-700 border-2 border-red-300'
                              : 'bg-white border-2 border-gray-200 hover:border-red-300 hover:bg-red-50'
                          }`}
                          disabled={message.feedbackGiven !== null}
                        >
                          <ThumbsDown size={14} />
                          {message.feedbackGiven === -1 ? 'Not helpful' : 'Not helpful'}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-50 rounded-2xl px-4 py-3 border border-gray-200">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-md p-4">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask me anything..."
              className="flex-1 px-4 py-3 border-2 border-purple-200 rounded-lg focus:outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-100"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-6 py-3 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-lg font-semibold hover:from-purple-600 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm"
            >
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
