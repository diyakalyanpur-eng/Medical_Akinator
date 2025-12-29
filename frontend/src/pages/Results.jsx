import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Trophy, Target, BookOpen, RotateCcw, Home, Loader2, Share2 } from 'lucide-react';
import { toast } from 'sonner';

export default function Results() {
  const navigate = useNavigate();
  const { gameId } = useParams();
  const location = useLocation();
  
  const [result] = useState(location.state?.result || null);
  const [specialty] = useState(location.state?.specialty || null);

  useEffect(() => {
    if (!result) {
      navigate('/game');
    }
  }, [result, navigate]);

  const shareResult = () => {
    const diagnosis = result.diagnosis || {};
    const text = `I just diagnosed ${diagnosis.name || result.disease_name} (ICD: ${diagnosis.icd_code}) in Disease Akinator with a ${diagnosis.probability || result.score}% score! Can you beat that?`;
    
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

  const diagnosis = result.diagnosis || {
    name: result.disease_name,
    icd_code: 'Unknown',
    probability: result.score,
    education: []
  };
  
  const isHighConfidence = (diagnosis.probability || result.score) >= 70;

  return (
    <div className="min-h-screen bg-[#09090b] relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-grid opacity-30" />
      <div className="absolute inset-0 bg-gradient-radial" />

      {/* Celebration Effect */}
      {isHighConfidence && (
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          {[...Array(20)].map((_, i) => (
            <div
              key={i}
              className="absolute w-2 h-2 rounded-full animate-float"
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
                backgroundColor: ['#00f0ff', '#7d00ff', '#00ff9d', '#ffb700'][i % 4],
                animationDelay: `${Math.random() * 2}s`,
                opacity: 0.3
              }}
            />
          ))}
        </div>
      )}

      <main className="relative z-10 max-w-4xl mx-auto px-6 py-12">
        {/* Result Header */}
        <div className="text-center mb-12 animate-scale-in">
          <div className={`w-24 h-24 rounded-full flex items-center justify-center mx-auto mb-6 ${
            isHighConfidence 
              ? 'bg-[#00ff9d]/20 animate-pulse-glow' 
              : 'bg-[#ffb700]/20'
          }`} style={{ 
            boxShadow: isHighConfidence 
              ? '0 0 40px -10px rgba(0, 255, 157, 0.5)' 
              : '0 0 40px -10px rgba(255, 183, 0, 0.5)' 
          }}>
            {isHighConfidence ? (
              <Trophy className="w-12 h-12 text-[#00ff9d]" />
            ) : (
              <Target className="w-12 h-12 text-[#ffb700]" />
            )}
          </div>
          
          <h1 className="text-4xl md:text-5xl font-bold text-white font-['Rajdhani'] mb-2">
            {isHighConfidence ? 'Excellent Diagnosis!' : 'Diagnosis Complete'}
          </h1>
          <p className="text-white/50">
            Reached in {result.questions_used} question{result.questions_used !== 1 ? 's' : ''}
          </p>
        </div>

        {/* Diagnosis Card */}
        <Card className="glass p-8 mb-8 animate-slide-up">
          <div className="text-center mb-8">
            <span className="text-xs font-mono text-[#00f0ff] tracking-widest uppercase mb-2 block">
              Final Diagnosis
            </span>
            <h2 className="text-3xl md:text-4xl font-bold text-white font-['Rajdhani'] mb-2">
              {diagnosis.name}
            </h2>
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-[#18181b] rounded-full">
              <span className="text-white/50 text-sm font-mono">ICD-10:</span>
              <span className="text-[#00f0ff] font-mono font-bold">{diagnosis.icd_code}</span>
            </div>
          </div>

          {/* Confidence & Score */}
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            <div className="text-center p-6 bg-[#18181b]/50 rounded-xl">
              <p className="text-white/50 text-sm font-mono uppercase tracking-wider mb-2">Accuracy Score</p>
              <p className="text-4xl font-bold font-['Rajdhani']" style={{ 
                color: isHighConfidence ? '#00ff9d' : '#ffb700' 
              }}>
                {diagnosis.probability || result.score}%
              </p>
            </div>
            <div className="text-center p-6 bg-[#18181b]/50 rounded-xl">
              <p className="text-white/50 text-sm font-mono uppercase tracking-wider mb-2">Questions Used</p>
              <p className="text-4xl font-bold text-[#00f0ff] font-['Rajdhani']">
                {result.questions_used}
              </p>
            </div>
          </div>

          {/* Education / Teaching Points */}
          {diagnosis.education && diagnosis.education.length > 0 && (
            <div className="border-t border-white/10 pt-6">
              <h3 className="text-white font-semibold font-['Rajdhani'] text-lg mb-4 flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-[#7d00ff]" />
                Teaching Points
              </h3>
              <ul className="space-y-3">
                {diagnosis.education.slice(0, 5).map((point, index) => (
                  <li key={index} className="flex items-start gap-3 text-white/70">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#7d00ff] mt-2 flex-shrink-0" />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
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
