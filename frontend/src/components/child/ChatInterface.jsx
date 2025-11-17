import { useState, useEffect, useRef } from 'react';
import { conversationAPI } from '../../services/api';
import { ThumbsUp, ThumbsDown } from 'lucide-react';

export default function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const messagesEndRef = useRef(null);

  // Mock child data - in production, this would come from kid login
  const childId = "1"; // This should come from authentication
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
      
      // Update the message to show feedback was given
      setMessages(messages.map(msg => 
        msg.id === messageId 
          ? { ...msg, feedbackGiven: rating }
          : msg
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
    <div className="min-h-screen bg-gradient-to-br from-purple-100 via-pink-100 to-blue-100">
      {/* Header */}
      <div className="bg-white shadow-md">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-purple-600">✨ Chat with Nia ✨</h1>
          <p className="text-sm text-gray-600">Your friendly learning assistant!</p>
        </div>
      </div>

      {/* Messages Container */}
      <div className="max-w-4xl mx-auto px-4 py-6">
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-6 min-h-[500px] max-h-[600px] overflow-y-auto">
          {messages.length === 0 ? (
            <div className="text-center text-gray-400 py-12">
              <p className="text-4xl mb-4">👋</p>
              <p className="text-lg">Hi! Ask me anything you're curious about!</p>
              <p className="text-sm mt-2">Try asking: "What is a seahorse?" or "Tell me about space!"</p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'child' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                      message.role === 'child'
                        ? 'bg-purple-500 text-white'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {/* Source Label for AI messages */}
                    {message.role === 'assistant' && message.sourceLabel && (
                      <div className="text-xs mb-2 opacity-75 font-medium">
                        {message.sourceLabel}
                      </div>
                    )}

                    {/* Message Content */}
                    <p className="whitespace-pre-wrap">{message.content}</p>

                    {/* DALL-E Image */}
                    {message.visualContent?.type === 'dalle_image' && (
                      <div className="mt-3">
                        <img
                          src={message.visualContent.image_url}
                          alt={message.visualContent.prompt}
                          className="rounded-lg max-w-full h-auto"
                          loading="lazy"
                        />
                        <p className="text-xs mt-1 opacity-75">
                          🎨 Generated image about: {message.visualContent.prompt}
                        </p>
                      </div>
                    )}

                    {/* Emoji Visual */}
                    {message.visualContent?.type === 'emoji_visual' && (
                      <div className="mt-2 text-2xl">
                        {message.visualContent.emojis?.join(' ')}
                      </div>
                    )}

                    {/* Feedback Buttons */}
                    {message.role === 'assistant' && (
                      <div className="mt-3 pt-3 border-t border-gray-200 flex gap-2">
                        <button
                          onClick={() => handleFeedback(message.id, 1)}
                          className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm transition-colors ${
                            message.feedbackGiven === 1
                              ? 'bg-green-500 text-white'
                              : 'bg-gray-200 hover:bg-green-100'
                          }`}
                          disabled={message.feedbackGiven !== null}
                        >
                          <ThumbsUp size={16} />
                          {message.feedbackGiven === 1 && 'Thanks!'}
                        </button>
                        <button
                          onClick={() => handleFeedback(message.id, -1)}
                          className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm transition-colors ${
                            message.feedbackGiven === -1
                              ? 'bg-red-500 text-white'
                              : 'bg-gray-200 hover:bg-red-100'
                          }`}
                          disabled={message.feedbackGiven !== null}
                        >
                          <ThumbsDown size={16} />
                          {message.feedbackGiven === -1 && 'Got it!'}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-2xl px-4 py-3">
                    <div className="flex gap-2">
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-lg p-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask me anything! 🤔"
              className="flex-1 px-4 py-3 border-2 border-purple-200 rounded-xl focus:outline-none focus:border-purple-400"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-6 py-3 bg-purple-500 text-white rounded-xl font-semibold hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Send 🚀
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
