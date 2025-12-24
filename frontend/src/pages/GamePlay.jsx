import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useAuth } from '../App';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { Brain, Lightbulb, ArrowRight, Loader2, HelpCircle, X, Check, Minus } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ANSWER_OPTIONS = [
  { value: 'yes', label: 'Yes', icon: Check, color: '#00ff9d' },
  { value: 'no', label: 'No', icon: X, color: '#ff0055' },
  { value: 'maybe', label: 'Maybe', icon: Minus, color: '#ffb700' },
  { value: 'dont_know', label: "Don't Know", icon: HelpCircle, color: '#7d00ff' }
];

export default function GamePlay() {
  const navigate = useNavigate();
  const { gameId } = useParams();
  const location = useLocation();
  const { token } = useAuth();
  
  const [gameData, setGameData] = useState(location.state?.gameData || null);
  const [isAnonymous] = useState(location.state?.isAnonymous ?? true);
  const [loading, setLoading] = useState(false);
  const [hint, setHint] = useState(null);
  const [loadingHint, setLoadingHint] = useState(false);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [topCandidates, setTopCandidates] = useState([]);

  useEffect(() => {
    if (!gameData) {
      // Redirect back if no game data
      navigate('/game');
    }
  }, [gameData, navigate]);

  const submitAnswer = async (answer) => {
    setSelectedAnswer(answer);
    setLoading(true);
    setHint(null);

    try {
      const headers = {};
      if (token && !isAnonymous) {
        headers.Authorization = `Bearer ${token}`;
      }

      const response = await axios.post(
        `${API}/game/answer`,
        { game_id: gameId, answer },
        { headers, withCredentials: true }
      );

      if (response.data.game_completed) {
        // Navigate to results
        navigate(`/results/${gameId}`, { 
          state: { 
            result: response.data, 
            specialty: gameData.specialty,
            isAnonymous 
          } 
        });
      } else {
        // Update game state
        setGameData(prev => ({
          ...prev,
          question_number: response.data.question_number,
          question: response.data.question,
          symptom_key: response.data.symptom_key
        }));
        setTopCandidates(response.data.top_candidates || []);
        setSelectedAnswer(null);
      }
    } catch (error) {
      console.error('Error submitting answer:', error);
      toast.error(error.response?.data?.detail || 'Failed to submit answer');
    } finally {
      setLoading(false);
    }
  };

  const getHint = async () => {
    setLoadingHint(true);
    try {
      const response = await axios.post(`${API}/game/hint`, { game_id: gameId });
      setHint(response.data.hint);
    } catch (error) {
      console.error('Error getting hint:', error);
      toast.error('Failed to get hint');
    } finally {
      setLoadingHint(false);
    }
  };

  if (!gameData) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-[#00f0ff] animate-spin" />
      </div>
    );
  }

  const progress = ((gameData.question_number || 1) / (gameData.total_questions || 10)) * 100;

  return (
    <div className="min-h-screen bg-[#09090b] relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-grid opacity-30" />
      <div className="absolute inset-0 bg-gradient-radial" />
      
      {/* Mascot Background */}
      <div 
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] opacity-5 pointer-events-none"
        style={{
          backgroundImage: 'url(https://images.unsplash.com/photo-1654910971111-836ac0c213ae?crop=entropy&cs=srgb&fm=jpg&q=85)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          mixBlendMode: 'screen'
        }}
      />

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between p-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-[#00f0ff]/20 flex items-center justify-center neon-border">
            <Brain className="w-6 h-6 text-[#00f0ff]" />
          </div>
          <div>
            <span className="text-white/50 text-xs font-mono uppercase tracking-wider">
              {gameData.specialty?.name || 'Diagnosis'}
            </span>
            <p className="text-white font-['Rajdhani'] font-bold">
              Question {gameData.question_number} of {gameData.total_questions}
            </p>
          </div>
        </div>
        
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
          Exit Game
        </Button>
      </header>

      {/* Progress Bar */}
      <div className="relative z-10 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="h-2 bg-[#18181b] rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-[#00f0ff] to-[#7d00ff] transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      <main className="relative z-10 max-w-4xl mx-auto px-6 py-12">
        {/* Question Card */}
        <Card className="glass p-8 md:p-12 mb-8 animate-scale-in">
          <div className="text-center">
            <div className="w-20 h-20 rounded-full bg-[#00f0ff]/10 flex items-center justify-center mx-auto mb-6 animate-pulse-glow">
              <Brain className="w-10 h-10 text-[#00f0ff]" />
            </div>
            
            <h2 className="text-2xl md:text-3xl font-bold text-white font-['Rajdhani'] mb-4" data-testid="question-text">
              {gameData.question}
            </h2>
            
            <p className="text-white/40 text-sm font-mono mb-8">
              Symptom: {gameData.symptom_key?.replace(/_/g, ' ')}
            </p>

            {/* Answer Buttons */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              {ANSWER_OPTIONS.map((option) => {
                const Icon = option.icon;
                const isSelected = selectedAnswer === option.value;
                
                return (
                  <Button
                    key={option.value}
                    className={`h-20 flex flex-col items-center justify-center gap-2 transition-all duration-300 ${
                      isSelected 
                        ? 'scale-105' 
                        : 'bg-[#18181b] hover:bg-white/10'
                    }`}
                    style={{
                      backgroundColor: isSelected ? `${option.color}20` : undefined,
                      borderColor: isSelected ? option.color : 'rgba(255,255,255,0.1)',
                      borderWidth: isSelected ? '2px' : '1px',
                      boxShadow: isSelected ? `0 0 20px -5px ${option.color}` : 'none'
                    }}
                    disabled={loading}
                    onClick={() => submitAnswer(option.value)}
                    data-testid={`answer-${option.value}`}
                  >
                    <Icon className="w-6 h-6" style={{ color: option.color }} />
                    <span className="text-white font-semibold">{option.label}</span>
                  </Button>
                );
              })}
            </div>

            {/* Hint Section */}
            <div className="border-t border-white/10 pt-6">
              {hint ? (
                <div className="glass-card p-4 rounded-lg text-left animate-fade-in">
                  <div className="flex items-start gap-3">
                    <Lightbulb className="w-5 h-5 text-[#ffb700] flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-[#ffb700] text-sm font-semibold mb-1">AI Hint</p>
                      <p className="text-white/70 text-sm">{hint}</p>
                    </div>
                  </div>
                </div>
              ) : (
                <Button
                  variant="ghost"
                  className="text-white/50 hover:text-[#ffb700] hover:bg-[#ffb700]/10"
                  onClick={getHint}
                  disabled={loadingHint}
                  data-testid="get-hint-btn"
                >
                  {loadingHint ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Getting hint...
                    </>
                  ) : (
                    <>
                      <Lightbulb className="w-4 h-4 mr-2" />
                      Get AI Hint
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>
        </Card>

        {/* Top Candidates */}
        {topCandidates.length > 0 && (
          <Card className="glass-card p-6 animate-slide-up">
            <h3 className="text-white/50 text-xs font-mono uppercase tracking-wider mb-4">
              Top Candidates
            </h3>
            <div className="space-y-3">
              {topCandidates.map((candidate, index) => (
                <div key={index} className="flex items-center justify-between">
                  <span className="text-white font-medium">{candidate.name}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-2 bg-[#18181b] rounded-full overflow-hidden">
                      <div 
                        className="h-full rounded-full transition-all duration-500"
                        style={{ 
                          width: `${candidate.probability}%`,
                          backgroundColor: index === 0 ? '#00ff9d' : index === 1 ? '#00f0ff' : '#7d00ff'
                        }}
                      />
                    </div>
                    <span className="text-white/50 text-sm font-mono w-12 text-right">
                      {candidate.probability}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}
      </main>

      {/* Loading Overlay */}
      {loading && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="glass p-8 rounded-2xl text-center">
            <Loader2 className="w-12 h-12 text-[#00f0ff] animate-spin mx-auto mb-4" />
            <p className="text-white font-['Rajdhani'] text-lg">Analyzing response...</p>
          </div>
        </div>
      )}
    </div>
  );
}
