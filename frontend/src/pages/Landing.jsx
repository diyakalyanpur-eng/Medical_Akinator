import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Heart, Brain, Wind, Utensils, Activity, Droplet, Bone, Bug, Scan, BrainCircuit, Trophy, Play, User, LogOut, ChevronRight } from 'lucide-react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SPECIALTY_ICONS = {
  cardiology: Heart,
  neurology: Brain,
  pulmonology: Wind,
  gastroenterology: Utensils,
  endocrinology: Activity,
  nephrology: Droplet,
  rheumatology: Bone,
  infectious_disease: Bug,
  dermatology: Scan,
  psychiatry: BrainCircuit
};

const SPECIALTY_COLORS = {
  cardiology: '#ff0055',
  neurology: '#7d00ff',
  pulmonology: '#00f0ff',
  gastroenterology: '#ffb700',
  endocrinology: '#00ff9d',
  nephrology: '#ff6b35',
  rheumatology: '#9d4edd',
  infectious_disease: '#38b000',
  dermatology: '#fb8500',
  psychiatry: '#8338ec'
};

export default function Landing() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [specialties, setSpecialties] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSpecialties();
  }, []);

  const fetchSpecialties = async () => {
    try {
      const response = await axios.get(`${API}/specialties`);
      setSpecialties(response.data);
    } catch (error) {
      console.error('Error fetching specialties:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#09090b] relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-grid opacity-30" />
      <div className="absolute inset-0 bg-gradient-radial" />
      
      {/* Mascot Background */}
      <div 
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] opacity-10 pointer-events-none"
        style={{
          backgroundImage: 'url(https://images.unsplash.com/photo-1654910971111-836ac0c213ae?crop=entropy&cs=srgb&fm=jpg&q=85)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          mixBlendMode: 'screen',
          filter: 'blur(1px)'
        }}
      />

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between p-6 md:p-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-[#00f0ff]/20 flex items-center justify-center neon-border">
            <Brain className="w-6 h-6 text-[#00f0ff]" />
          </div>
          <span className="text-xl font-bold text-white font-['Rajdhani'] tracking-wider">DR. NEURO</span>
        </div>
        
        <nav className="flex items-center gap-4">
          <Button 
            variant="ghost" 
            className="text-white/70 hover:text-white hover:bg-white/5"
            onClick={() => navigate('/leaderboard')}
            data-testid="leaderboard-nav-btn"
          >
            <Trophy className="w-4 h-4 mr-2" />
            Leaderboard
          </Button>
          
          {user ? (
            <div className="flex items-center gap-3">
              <Button 
                variant="ghost" 
                className="text-white/70 hover:text-white hover:bg-white/5"
                onClick={() => navigate('/dashboard')}
                data-testid="dashboard-nav-btn"
              >
                <User className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
              <Button 
                variant="ghost" 
                className="text-white/70 hover:text-red-400 hover:bg-red-400/10"
                onClick={logout}
                data-testid="logout-btn"
              >
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
          ) : (
            <Button 
              className="bg-[#00f0ff] text-black font-bold hover:bg-[#00f0ff]/90"
              onClick={() => navigate('/login')}
              data-testid="login-nav-btn"
            >
              Sign In
            </Button>
          )}
        </nav>
      </header>

      {/* Hero Section */}
      <main className="relative z-10 max-w-7xl mx-auto px-6 py-12 md:py-20">
        <div className="text-center mb-16 animate-slide-up">
          <h1 className="text-5xl md:text-7xl font-bold text-white font-['Rajdhani'] tracking-tighter uppercase mb-6">
            Think Like a
            <span className="text-gradient block">Diagnostician</span>
          </h1>
          <p className="text-lg md:text-xl text-white/60 max-w-2xl mx-auto mb-8">
            Master the art of differential diagnosis through an AI-powered game. 
            Can you reach the correct diagnosis in 10 questions or less?
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button 
              className="btn-primary"
              onClick={() => navigate('/game')}
              data-testid="start-game-btn"
            >
              <span>START DIAGNOSIS</span>
            </button>
            {!user && (
              <Button 
                variant="outline" 
                className="border-white/20 text-white hover:bg-white/5 font-mono"
                onClick={() => navigate('/register')}
                data-testid="register-btn"
              >
                Create Account for Full Access
              </Button>
            )}
          </div>
        </div>

        {/* Specialties Grid */}
        <section className="mb-16">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-2xl md:text-3xl font-semibold text-white font-['Rajdhani']">
              Choose Your Specialty
            </h2>
            <span className="text-sm font-mono text-white/40 uppercase tracking-widest">
              10 Specialties Available
            </span>
          </div>
          
          {loading ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
              {[...Array(10)].map((_, i) => (
                <div key={i} className="h-40 bg-white/5 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
              {specialties.map(([key, specialty]) => {
                const Icon = SPECIALTY_ICONS[key] || Activity;
                const color = SPECIALTY_COLORS[key] || '#00f0ff';
                
                return (
                  <Card 
                    key={key}
                    className="glass-card p-6 cursor-pointer card-interactive group"
                    onClick={() => navigate(`/game?specialty=${key}`)}
                    data-testid={`specialty-card-${key}`}
                  >
                    <div 
                      className="w-12 h-12 rounded-lg flex items-center justify-center mb-4 transition-all duration-300 group-hover:scale-110"
                      style={{ backgroundColor: `${color}20` }}
                    >
                      <Icon className="w-6 h-6" style={{ color }} />
                    </div>
                    <h3 className="text-white font-semibold font-['Rajdhani'] text-lg mb-1">
                      {specialty.name}
                    </h3>
                    <p className="text-white/40 text-sm line-clamp-2">
                      {specialty.description}
                    </p>
                    <div className="mt-4 flex items-center text-white/30 text-xs font-mono group-hover:text-[#00f0ff] transition-colors">
                      <span>Play Now</span>
                      <ChevronRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </section>

        {/* How It Works */}
        <section className="glass rounded-2xl p-8 md:p-12">
          <h2 className="text-2xl md:text-3xl font-semibold text-white font-['Rajdhani'] mb-8 text-center">
            How It Works
          </h2>
          
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-[#00f0ff]/10 flex items-center justify-center mx-auto mb-4 neon-border">
                <span className="text-2xl font-bold text-[#00f0ff] font-['Rajdhani']">1</span>
              </div>
              <h3 className="text-white font-semibold mb-2">Select Specialty</h3>
              <p className="text-white/50 text-sm">Choose from 10 medical specialties to focus your diagnostic challenge.</p>
            </div>
            
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-[#7d00ff]/10 flex items-center justify-center mx-auto mb-4" style={{ border: '1px solid rgba(125, 0, 255, 0.5)', boxShadow: '0 0 15px -3px rgba(125, 0, 255, 0.2)' }}>
                <span className="text-2xl font-bold text-[#7d00ff] font-['Rajdhani']">2</span>
              </div>
              <h3 className="text-white font-semibold mb-2">Answer Questions</h3>
              <p className="text-white/50 text-sm">Respond to symptom-based questions. Use AI hints if needed.</p>
            </div>
            
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-[#00ff9d]/10 flex items-center justify-center mx-auto mb-4" style={{ border: '1px solid rgba(0, 255, 157, 0.5)', boxShadow: '0 0 15px -3px rgba(0, 255, 157, 0.2)' }}>
                <span className="text-2xl font-bold text-[#00ff9d] font-['Rajdhani']">3</span>
              </div>
              <h3 className="text-white font-semibold mb-2">Get Diagnosis</h3>
              <p className="text-white/50 text-sm">Discover the diagnosis with ICD code and educational insights.</p>
            </div>
          </div>
        </section>

        {/* Features Banner */}
        <section className="mt-12 flex flex-wrap justify-center gap-6 text-center">
          <div className="flex items-center gap-2 text-white/40">
            <div className="w-2 h-2 rounded-full bg-[#00f0ff]" />
            <span className="text-sm font-mono">200+ ICD Codes</span>
          </div>
          <div className="flex items-center gap-2 text-white/40">
            <div className="w-2 h-2 rounded-full bg-[#7d00ff]" />
            <span className="text-sm font-mono">AI-Powered Hints</span>
          </div>
          <div className="flex items-center gap-2 text-white/40">
            <div className="w-2 h-2 rounded-full bg-[#00ff9d]" />
            <span className="text-sm font-mono">Educational Mode</span>
          </div>
          <div className="flex items-center gap-2 text-white/40">
            <div className="w-2 h-2 rounded-full bg-[#ffb700]" />
            <span className="text-sm font-mono">Global Leaderboard</span>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="relative z-10 text-center py-8 text-white/30 text-sm font-mono">
        <p>DR. NEURO © 2025 • Medical Diagnosis Training Game</p>
      </footer>
    </div>
  );
}
