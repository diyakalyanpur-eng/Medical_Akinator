import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Stethoscope, ArrowLeft, Play, Loader2, Activity, Heart, Brain, Wind, Droplet } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SPECIALTY_ICONS = {
  respiratory: Wind,
  infectious: Activity,
  cardiology: Heart,
  neurology: Brain,
  general: Activity,
  cardiovascular: Heart,
  gastrointestinal: Droplet,
};

const SPECIALTY_COLORS = {
  respiratory: '#00f0ff',
  infectious: '#38b000',
  cardiology: '#ff0055',
  neurology: '#7d00ff',
  general: '#ffb700',
  cardiovascular: '#ff0055',
  gastrointestinal: '#ffb700',
};

export default function Game() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [specialties, setSpecialties] = useState([]);
  const [selectedSpecialty, setSelectedSpecialty] = useState(searchParams.get('specialty') || null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    fetchSpecialties();
  }, []);

  const fetchSpecialties = async () => {
    try {
      const response = await axios.get(`${API}/specialties`);
      setSpecialties(response.data);
      // Auto-select if only one or if specialty in URL
      if (response.data.length === 1) {
        setSelectedSpecialty(response.data[0][0]);
      }
    } catch (error) {
      console.error('Error fetching specialties:', error);
      toast.error('Failed to load specialties');
    } finally {
      setLoading(false);
    }
  };

  const startGame = async () => {
    const specialtyToUse = selectedSpecialty || 'general';
    
    setStarting(true);
    try {
      const response = await axios.post(`${API}/game/start`, { 
        specialty: specialtyToUse, 
        is_anonymous: true 
      });

      navigate(`/play/${response.data.game_id}`, { 
        state: { gameData: response.data } 
      });
    } catch (error) {
      console.error('Error starting game:', error);
      toast.error(error.response?.data?.detail || 'Failed to start game');
    } finally {
      setStarting(false);
    }
  };

  const selectedSpecialtyData = specialties.find(([key]) => key === selectedSpecialty)?.[1];

  return (
    <div className="min-h-screen bg-[#09090b] relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-grid opacity-30" />
      <div className="absolute inset-0 bg-gradient-radial" />

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between p-6">
        <Button
          variant="ghost"
          className="text-white/70 hover:text-white hover:bg-white/5"
          onClick={() => navigate('/')}
          data-testid="back-btn"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
      </header>

      <main className="relative z-10 max-w-5xl mx-auto px-6 py-8">
        <div className="text-center mb-12 animate-slide-up">
          <h1 className="text-4xl md:text-5xl font-bold text-white font-['Rajdhani'] tracking-tight uppercase mb-4">
            Select <span className="text-gradient">Specialty</span>
          </h1>
          <p className="text-white/50 max-w-xl mx-auto">
            Choose a medical specialty to begin. Each specialty contains diseases with 
            detailed patient presentations and symptom patterns.
          </p>
        </div>

        {/* Specialty Grid */}
        {loading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-40 bg-white/5 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : specialties.length === 0 ? (
          <Card className="glass p-12 text-center mb-8">
            <Stethoscope className="w-16 h-16 text-white/20 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No Diseases Available</h3>
            <p className="text-white/50 mb-4">Please add your diseases.json file to continue.</p>
            <p className="text-white/30 text-sm font-mono">Path: /app/backend/data/diseases.json</p>
          </Card>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-12">
            {specialties.map(([key, specialty]) => {
              const Icon = SPECIALTY_ICONS[key] || Activity;
              const color = SPECIALTY_COLORS[key] || '#00f0ff';
              const isSelected = selectedSpecialty === key;
              
              return (
                <Card 
                  key={key}
                  className={`p-6 cursor-pointer transition-all duration-300 ${
                    isSelected 
                      ? 'bg-black/80 border-2' 
                      : 'glass-card hover:bg-white/5'
                  }`}
                  style={{
                    borderColor: isSelected ? color : 'rgba(255,255,255,0.1)',
                    boxShadow: isSelected ? `0 0 30px -10px ${color}` : 'none'
                  }}
                  onClick={() => setSelectedSpecialty(key)}
                  data-testid={`specialty-select-${key}`}
                >
                  <div 
                    className={`w-12 h-12 rounded-lg flex items-center justify-center mb-4 transition-all duration-300 ${isSelected ? 'scale-110' : ''}`}
                    style={{ backgroundColor: `${color}20` }}
                  >
                    <Icon className="w-6 h-6" style={{ color }} />
                  </div>
                  <h3 className="text-white font-semibold font-['Rajdhani'] text-lg mb-1">
                    {specialty.name}
                  </h3>
                  <p className="text-white/40 text-sm">
                    {specialty.disease_count} disease{specialty.disease_count !== 1 ? 's' : ''}
                  </p>
                  
                  {isSelected && (
                    <div className="mt-3 flex items-center text-xs font-mono" style={{ color }}>
                      <div className="w-2 h-2 rounded-full mr-2 animate-pulse" style={{ backgroundColor: color }} />
                      Selected
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        )}

        {/* Start Game Panel */}
        <div className="glass rounded-2xl p-8 animate-fade-in">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="text-center md:text-left">
              <h2 className="text-2xl font-bold text-white font-['Rajdhani'] mb-2">
                {selectedSpecialtyData ? (
                  <>Ready to diagnose in <span style={{ color: SPECIALTY_COLORS[selectedSpecialty] || '#00f0ff' }}>{selectedSpecialtyData.name}</span>?</>
                ) : specialties.length > 0 ? (
                  'Select a specialty or start with random'
                ) : (
                  'Add diseases.json to begin'
                )}
              </h2>
              <p className="text-white/50">
                {specialties.length > 0 
                  ? 'A random disease will be selected. Answer up to 10 questions to reach the diagnosis.'
                  : 'No diseases available in the database'
                }
              </p>
              
              <div className="mt-4 flex flex-wrap gap-4 text-sm">
                <div className="flex items-center gap-2 text-white/40">
                  <div className="w-2 h-2 rounded-full bg-[#00f0ff]" />
                  <span className="font-mono">Max 10 Questions</span>
                </div>
                <div className="flex items-center gap-2 text-white/40">
                  <div className="w-2 h-2 rounded-full bg-[#7d00ff]" />
                  <span className="font-mono">Patient Context</span>
                </div>
                <div className="flex items-center gap-2 text-white/40">
                  <div className="w-2 h-2 rounded-full bg-[#00ff9d]" />
                  <span className="font-mono">Teaching Points</span>
                </div>
              </div>
            </div>
            
            <Button
              className="bg-[#00f0ff] text-black font-bold text-lg px-8 py-6 hover:bg-[#00f0ff]/90 disabled:opacity-50 min-w-[200px]"
              disabled={specialties.length === 0 || starting}
              onClick={startGame}
              data-testid="start-game-btn"
            >
              {starting ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <Play className="w-5 h-5 mr-2" />
                  Start Game
                </>
              )}
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
