import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Trophy, Target, BookOpen, RotateCcw, Home, Loader2, Share2, CheckCircle, XCircle, TrendingUp, MessageSquare } from 'lucide-react';
import { toast } from 'sonner';

export default function Results() {
  const navigate = useNavigate();
  const { gameId } = useParams();
  const location = useLocation();
  
  const [result] = useState(location.state?.result || null);
  const [questionsAsked] = useState(location.state?.questionsAsked || 0);

  useEffect(() => {
    if (!result) {
      navigate('/game');
    }
  }, [result, navigate]);

  const shareResult = () => {
    const text = result.correct 
      ? `I correctly diagnosed ${result.actual_disease} in Disease Akinator with ${questionsAsked} questions! Score: ${result.efficiency_score}%`
      : `I attempted to diagnose a case in Disease Akinator. The answer was ${result.actual_disease}. Can you do better?`;
    
    if (navigator.share) {
      navigator.share({
        title: 'Disease Akinator - Medical Diagnosis Game',
        text,
        url: window.location.origin
      });
    } else {
      navigator.clipboard.writeText(text);
      toast.success('Result copied to clipboard!');
    }
  };

  if (!result) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-[#00f0ff] animate-spin" />
      </div>
    );
  }

  const isCorrect = result.correct;

  return (
    <div className="min-h-screen bg-[#09090b] relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-grid opacity-30" />
      <div className="absolute inset-0 bg-gradient-radial" />

      {/* Celebration/Commiseration Effect */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {[...Array(15)].map((_, i) => (
          <div
            key={i}
            className="absolute w-2 h-2 rounded-full animate-float"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              backgroundColor: isCorrect 
                ? ['#00f0ff', '#00ff9d'][i % 2]
                : ['#ff0055', '#ffb700'][i % 2],
              animationDelay: `${Math.random() * 2}s`,
              opacity: 0.3
            }}
          />
        ))}
      </div>

      <main className="relative z-10 max-w-4xl mx-auto px-6 py-12">
        {/* Result Header */}
        <div className="text-center mb-12 animate-scale-in">
          <div className={`w-24 h-24 rounded-full flex items-center justify-center mx-auto mb-6 ${
            isCorrect 
              ? 'bg-[#00ff9d]/20' 
              : 'bg-[#ff0055]/20'
          }`} style={{ 
            boxShadow: isCorrect 
              ? '0 0 40px -10px rgba(0, 255, 157, 0.5)' 
              : '0 0 40px -10px rgba(255, 0, 85, 0.5)' 
          }}>
            {isCorrect ? (
              <CheckCircle className="w-12 h-12 text-[#00ff9d]" />
            ) : (
              <XCircle className="w-12 h-12 text-[#ff0055]" />
            )}
          </div>
          
          <h1 className="text-4xl md:text-5xl font-bold text-white font-['Rajdhani'] mb-2">
            {isCorrect ? 'Correct Diagnosis!' : 'Not Quite Right'}
          </h1>
          <p className="text-white/50">
            {result.feedback}
          </p>
        </div>

        {/* Diagnosis Card */}
        <Card className="glass p-8 mb-8 animate-slide-up">
          <div className="text-center mb-8">
            <span className="text-xs font-mono text-[#00f0ff] tracking-widest uppercase mb-2 block">
              Correct Diagnosis
            </span>
            <h2 className="text-3xl md:text-4xl font-bold text-white font-['Rajdhani'] mb-4">
              {result.actual_disease}
            </h2>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="text-center p-4 bg-[#18181b]/50 rounded-xl">
              <MessageSquare className="w-5 h-5 text-[#00f0ff] mx-auto mb-2" />
              <p className="text-2xl font-bold text-white font-['Rajdhani']">
                {result.questions_used}
              </p>
              <p className="text-white/40 text-xs">Questions</p>
            </div>
            <div className="text-center p-4 bg-[#18181b]/50 rounded-xl">
              <TrendingUp className="w-5 h-5 text-[#7d00ff] mx-auto mb-2" />
              <p className="text-2xl font-bold text-white font-['Rajdhani']">
                {result.efficiency_score}%
              </p>
              <p className="text-white/40 text-xs">Efficiency</p>
            </div>
            <div className="text-center p-4 bg-[#18181b]/50 rounded-xl">
              <CheckCircle className="w-5 h-5 text-[#00ff9d] mx-auto mb-2" />
              <p className="text-2xl font-bold text-white font-['Rajdhani']">
                {result.essential_questions_asked}
              </p>
              <p className="text-white/40 text-xs">Essential Asked</p>
            </div>
            <div className="text-center p-4 bg-[#18181b]/50 rounded-xl">
              <Target className="w-5 h-5 text-[#ffb700] mx-auto mb-2" />
              <p className="text-2xl font-bold text-white font-['Rajdhani']">
                {result.diagnostic_pathway_quality}
              </p>
              <p className="text-white/40 text-xs">Quality</p>
            </div>
          </div>

          {/* Key Features */}
          {result.key_features && result.key_features.length > 0 && (
            <div className="border-t border-white/10 pt-6 mb-6">
              <h3 className="text-white font-semibold font-['Rajdhani'] text-lg mb-4 flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-[#7d00ff]" />
                Key Features to Remember
              </h3>
              <ul className="space-y-2">
                {result.key_features.map((feature, index) => (
                  <li key={index} className="flex items-start gap-3 text-white/70">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#7d00ff] mt-2 flex-shrink-0" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Related Conditions */}
          {result.related_conditions && result.related_conditions.length > 0 && (
            <div className="border-t border-white/10 pt-6">
              <h3 className="text-white font-semibold font-['Rajdhani'] text-lg mb-4">
                Related Conditions
              </h3>
              <div className="flex flex-wrap gap-2">
                {result.related_conditions.map((condition, index) => (
                  <span 
                    key={index}
                    className="px-3 py-1 rounded-full bg-white/5 text-white/60 text-sm"
                  >
                    {condition}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Differential Quality */}
          {result.differential_quality && (
            <div className="border-t border-white/10 pt-6 mt-6">
              <p className="text-white/50 text-sm">
                <span className="text-white/70">Differential Diagnosis Quality:</span> {result.differential_quality}
              </p>
              {result.essential_questions_missed > 0 && (
                <p className="text-[#ffb700]/70 text-sm mt-2">
                  You missed {result.essential_questions_missed} essential question(s). 
                  Consider asking about key symptoms and history next time.
                </p>
              )}
            </div>
          )}
        </Card>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-fade-in">
          <Button
            className="w-full sm:w-auto bg-[#00f0ff] text-black font-bold px-8 py-6 hover:bg-[#00f0ff]/90"
            onClick={() => navigate('/game')}
            data-testid="play-again-btn"
          >
            <RotateCcw className="w-5 h-5 mr-2" />
            Play Again
          </Button>
          
          <Button
            variant="outline"
            className="w-full sm:w-auto border-white/20 text-white hover:bg-white/5 px-8 py-6"
            onClick={shareResult}
            data-testid="share-btn"
          >
            <Share2 className="w-5 h-5 mr-2" />
            Share Result
          </Button>
          
          <Button
            variant="ghost"
            className="w-full sm:w-auto text-white/50 hover:text-white hover:bg-white/5 px-8 py-6"
            onClick={() => navigate('/')}
            data-testid="home-btn"
          >
            <Home className="w-5 h-5 mr-2" />
            Home
          </Button>
        </div>
      </main>
    </div>
  );
}
