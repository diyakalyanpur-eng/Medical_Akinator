import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Trophy, ArrowLeft, Play } from 'lucide-react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Leaderboard() {
  const navigate = useNavigate();
  const [leaders, setLeaders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLeaderboard();
  }, []);

  const fetchLeaderboard = async () => {
    try {
      const response = await axios.get(`${API}/leaderboard`);
      setLeaders(response.data);
    } catch (error) {
      console.error('Error fetching leaderboard:', error);
    } finally {
      setLoading(false);
    }
  };

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

      <main className="relative z-10 max-w-3xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="text-center mb-12 animate-slide-up">
          <div className="w-20 h-20 rounded-full bg-[#ffb700]/20 flex items-center justify-center mx-auto mb-6" style={{ boxShadow: '0 0 40px -10px rgba(255, 183, 0, 0.5)' }}>
            <Trophy className="w-10 h-10 text-[#ffb700]" />
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-white font-['Rajdhani'] uppercase tracking-tight mb-2">
            Leaderboard
          </h1>
          <p className="text-white/50">Top diagnosticians ranked by score</p>
        </div>

        {/* Leaderboard Content */}
        {loading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-20 bg-white/5 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : leaders.length === 0 ? (
          <Card className="glass p-12 text-center">
            <Trophy className="w-16 h-16 text-white/20 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">Coming Soon</h2>
            <p className="text-white/50 mb-6">
              Leaderboard functionality requires authentication. 
              For now, enjoy the diagnostic challenge!
            </p>
            <Button
              className="bg-[#00f0ff] text-black font-bold hover:bg-[#00f0ff]/90"
              onClick={() => navigate('/game')}
              data-testid="start-playing-btn"
            >
              <Play className="w-4 h-4 mr-2" />
              Start Playing
            </Button>
          </Card>
        ) : (
          <div className="space-y-3">
            {leaders.map((leader, index) => (
              <Card
                key={leader.user_id || index}
                className="glass-card p-4 flex items-center gap-4"
              >
                <div className="w-10 flex justify-center">
                  <span className="text-white/50 font-mono">{index + 1}</span>
                </div>
                <div className="flex-1">
                  <p className="text-white font-medium">{leader.name}</p>
                  <p className="text-white/40 text-sm font-mono">
                    {leader.games_played} games
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-[#00f0ff] font-bold font-['Rajdhani'] text-xl">
                    {leader.total_score?.toLocaleString() || 0}
                  </p>
                  <p className="text-white/40 text-xs font-mono">points</p>
                </div>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
