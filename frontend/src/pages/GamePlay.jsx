import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Stethoscope, Send, Loader2, User, MessageSquare, Target, Lightbulb } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function GamePlay() {
  const navigate = useNavigate();
  const { gameId } = useParams();
  const location = useLocation();
  const messagesEndRef = useRef(null);
  
  const [gameData, setGameData] = useState(location.state?.gameData || null);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [submittingDiagnosis, setSubmittingDiagnosis] = useState(false);
  const [conversation, setConversation] = useState([]);
  const [differential, setDifferential] = useState([]);
  const [showDiagnosisInput, setShowDiagnosisInput] = useState(false);
  const [diagnosisGuess, setDiagnosisGuess] = useState('');

  useEffect(() => {
    if (!gameData) {
      navigate('/game');
    } else {
      // Add initial presentation to conversation
      if (gameData.initial_presentation) {
        setConversation([{
          type: 'system',
          content: gameData.initial_presentation
        }]);
      }
    }
  }, [gameData, navigate]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation]);

  const askQuestion = async (e) => {
    e.preventDefault();
    if (!question.trim() || loading) return;

    const userQuestion = question.trim();
    setQuestion('');
    setLoading(true);

    // Add user question to conversation
    setConversation(prev => [...prev, {
      type: 'user',
      content: userQuestion
    }]);

    try {
      const response = await axios.post(`${API}/ask-question`, {
        session_id: gameId,
        question: userQuestion
      });

      // Add answer to conversation
      setConversation(prev => [...prev, {
        type: 'answer',
        content: response.data.answer,
        explanation: response.data.explanation
      }]);

      // Update differential if provided
      if (response.data.differential_diagnosis?.length > 0) {
        setDifferential(response.data.differential_diagnosis);
      }

    } catch (error) {
      console.error('Error asking question:', error);
      toast.error(error.response?.data?.detail || 'Failed to get answer');
      // Remove the user question if error
      setConversation(prev => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  const submitDiagnosis = async (e) => {
    e.preventDefault();
    if (!diagnosisGuess.trim() || submittingDiagnosis) return;

    setSubmittingDiagnosis(true);

    try {
      const response = await axios.post(`${API}/submit-diagnosis`, {
        session_id: gameId,
        diagnosis: diagnosisGuess.trim()
      });

      // Navigate to results
      navigate(`/results/${gameId}`, {
        state: {
          result: response.data,
          questionsAsked: conversation.filter(c => c.type === 'user').length
        }
      });

    } catch (error) {
      console.error('Error submitting diagnosis:', error);
      toast.error(error.response?.data?.detail || 'Failed to submit diagnosis');
    } finally {
      setSubmittingDiagnosis(false);
    }
  };

  if (!gameData) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-[#00f0ff] animate-spin" />
      </div>
    );
  }

  const questionsAsked = conversation.filter(c => c.type === 'user').length;

  return (
    <div className="min-h-screen bg-[#09090b] relative overflow-hidden flex flex-col">
      {/* Background */}
      <div className="absolute inset-0 bg-grid opacity-30" />
      <div className="absolute inset-0 bg-gradient-radial" />

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between p-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-[#00f0ff]/20 flex items-center justify-center neon-border">
            <Stethoscope className="w-6 h-6 text-[#00f0ff]" />
          </div>
          <div>
            <span className="text-white/50 text-xs font-mono uppercase tracking-wider">
              Diagnostic Session
            </span>
            <p className="text-white font-['Rajdhani'] font-bold">
              {questionsAsked} Questions Asked
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <Button
            className="bg-[#00ff9d] text-black font-bold hover:bg-[#00ff9d]/90"
            onClick={() => setShowDiagnosisInput(true)}
            data-testid="submit-diagnosis-btn"
          >
            <Target className="w-4 h-4 mr-2" />
            Submit Diagnosis
          </Button>
          <Button
            variant="ghost"
            className="text-white/50 hover:text-white hover:bg-white/5"
            onClick={() => {
              if (window.confirm('Are you sure you want to exit? Your progress will be lost.')) {
                navigate('/game');
              }
            }}
            data-testid="exit-game-btn"
          >
            Exit
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <div className="relative z-10 flex-1 flex overflow-hidden">
        {/* Conversation Panel */}
        <div className="flex-1 flex flex-col">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {conversation.map((msg, index) => (
              <div
                key={index}
                className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}
              >
                {msg.type === 'system' && (
                  <Card className="glass-card p-4 max-w-2xl">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-full bg-[#7d00ff]/20 flex items-center justify-center flex-shrink-0">
                        <User className="w-5 h-5 text-[#7d00ff]" />
                      </div>
                      <div>
                        <p className="text-[#7d00ff] text-sm font-semibold mb-1">Patient Presentation</p>
                        <p className="text-white/80 leading-relaxed">{msg.content}</p>
                      </div>
                    </div>
                  </Card>
                )}
                
                {msg.type === 'user' && (
                  <Card className="bg-[#00f0ff]/10 border-[#00f0ff]/30 p-4 max-w-xl">
                    <div className="flex items-start gap-3">
                      <div>
                        <p className="text-[#00f0ff] text-sm font-semibold mb-1">Your Question</p>
                        <p className="text-white/90">{msg.content}</p>
                      </div>
                      <div className="w-8 h-8 rounded-full bg-[#00f0ff]/20 flex items-center justify-center flex-shrink-0">
                        <MessageSquare className="w-4 h-4 text-[#00f0ff]" />
                      </div>
                    </div>
                  </Card>
                )}
                
                {msg.type === 'answer' && (
                  <Card className="glass p-4 max-w-2xl">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-full bg-[#00ff9d]/20 flex items-center justify-center flex-shrink-0">
                        <Stethoscope className="w-5 h-5 text-[#00ff9d]" />
                      </div>
                      <div>
                        <p className="text-[#00ff9d] text-sm font-semibold mb-1">Answer</p>
                        <p className="text-white font-medium text-lg mb-2">{msg.content}</p>
                        {msg.explanation && (
                          <p className="text-white/60 text-sm">{msg.explanation}</p>
                        )}
                      </div>
                    </div>
                  </Card>
                )}
              </div>
            ))}
            
            {loading && (
              <div className="flex justify-start animate-fade-in">
                <Card className="glass p-4">
                  <div className="flex items-center gap-3">
                    <Loader2 className="w-5 h-5 text-[#00f0ff] animate-spin" />
                    <span className="text-white/50">Analyzing patient data...</span>
                  </div>
                </Card>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Question Input */}
          <div className="p-4 border-t border-white/10">
            <form onSubmit={askQuestion} className="flex gap-3">
              <Input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask a question... (e.g., 'Does the patient have fever?', 'What are the vital signs?')"
                className="flex-1 bg-[#18181b]/50 border-white/10 text-white placeholder:text-white/30 h-12"
                disabled={loading}
                data-testid="question-input"
              />
              <Button
                type="submit"
                className="bg-[#00f0ff] text-black font-bold px-6 hover:bg-[#00f0ff]/90"
                disabled={loading || !question.trim()}
                data-testid="send-question-btn"
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </Button>
            </form>
            
            {/* Suggested Questions */}
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="text-white/30 text-xs">Suggestions:</span>
              {[
                "Does the patient have fever?",
                "What are the vital signs?",
                "When did symptoms start?",
                "Any relevant medical history?"
              ].map((suggestion, i) => (
                <button
                  key={i}
                  className="text-xs px-2 py-1 rounded bg-white/5 text-white/50 hover:bg-white/10 hover:text-white/70 transition-colors"
                  onClick={() => setQuestion(suggestion)}
                  type="button"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Differential Diagnosis Panel */}
        {differential.length > 0 && (
          <div className="w-80 border-l border-white/10 p-4 overflow-y-auto hidden lg:block">
            <h3 className="text-white/50 text-xs font-mono uppercase tracking-wider mb-4 flex items-center gap-2">
              <Lightbulb className="w-4 h-4" />
              Differential Diagnosis
            </h3>
            <div className="space-y-3">
              {differential.map((item, index) => (
                <Card key={index} className="glass-card p-3">
                  <p className="text-white font-medium text-sm">{item.disease}</p>
                  <p className="text-white/40 text-xs mt-1">{item.likelihood}</p>
                  {item.reasoning && (
                    <p className="text-white/50 text-xs mt-2">{item.reasoning}</p>
                  )}
                </Card>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Diagnosis Modal */}
      {showDiagnosisInput && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <Card className="glass p-8 max-w-md w-full animate-scale-in">
            <h2 className="text-2xl font-bold text-white font-['Rajdhani'] mb-2">
              Submit Your Diagnosis
            </h2>
            <p className="text-white/50 mb-6">
              Based on your findings, what is your diagnosis?
            </p>
            
            <form onSubmit={submitDiagnosis}>
              <Input
                value={diagnosisGuess}
                onChange={(e) => setDiagnosisGuess(e.target.value)}
                placeholder="Enter disease name (e.g., Pneumonia, Influenza)"
                className="bg-[#18181b]/50 border-white/10 text-white placeholder:text-white/30 h-12 mb-4"
                autoFocus
                data-testid="diagnosis-input"
              />
              
              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="outline"
                  className="flex-1 border-white/20 text-white hover:bg-white/5"
                  onClick={() => setShowDiagnosisInput(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="flex-1 bg-[#00ff9d] text-black font-bold hover:bg-[#00ff9d]/90"
                  disabled={!diagnosisGuess.trim() || submittingDiagnosis}
                  data-testid="confirm-diagnosis-btn"
                >
                  {submittingDiagnosis ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    'Submit'
                  )}
                </Button>
              </div>
            </form>
            
            <p className="text-white/30 text-xs mt-4 text-center">
              Questions asked: {questionsAsked}
            </p>
          </Card>
        </div>
      )}
    </div>
  );
}
