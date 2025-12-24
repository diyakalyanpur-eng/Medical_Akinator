import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Trophy, Medal, ArrowLeft, Crown, User } from 'lucide-react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Leaderboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
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

  const getRankIcon = (rank) => {
    switch (rank) {
      case 1:
        return <Crown className="w-6 h-6 text-[#ffb700]" />;
      case 2:
        return <Medal className="w-6 h-6 text-[#c0c0c0]" />;
      case 3:
        return <Medal className="w-6 h-6 text-[#cd7f32]" />;
      default:
        return <span className="text-white/50 font-mono w-6 text-center">{rank}</span>;
    }
  };

  const getRankStyle = (rank) => {
    switch (rank) {
      case 1:
        return { borderColor: '#ffb700', boxShadow: '0 0 20px -5px rgba(255, 183, 0, 0.3)' };
      case 2:
        return { borderColor: '#c0c0c0', boxShadow: '0 0 20px -5px rgba(192, 192, 192, 0.3)' };
      case 3:
        return { borderColor: '#cd7f32', boxShadow: '0 0 20px -5px rgba(205, 127, 50, 0.3)' };
      default:
        return { borderColor: 'rgba(255,255,255,0.1)' };
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
          <p className="text-white/50">Top diagnosticians ranked by total score</p>
        </div>

        {/* Leaderboard List */}
        {loading ? (
          <div className="space-y-4">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="h-20 bg-white/5 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : leaders.length === 0 ? (
          <Card className="glass p-12 text-center">
            <Trophy className="w-16 h-16 text-white/20 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-white mb-2">No Leaders Yet</h2>
            <p className="text-white/50 mb-6">Be the first to make it to the leaderboard!</p>
            <Button
              className="bg-[#00f0ff] text-black font-bold hover:bg-[#00f0ff]/90"
              onClick={() => navigate('/game')}
              data-testid="start-playing-btn"
            >
              Start Playing
            </Button>
          </Card>
        ) : (
          <div className="space-y-3">
            {leaders.map((leader, index) => {
              const rank = index + 1;
              const isCurrentUser = user?.user_id === leader.user_id;
              const style = getRankStyle(rank);
              
              return (
                <Card
                  key={leader.user_id}
                  className={`p-4 flex items-center gap-4 transition-all duration-300 ${
                    isCurrentUser ? 'bg-[#00f0ff]/10' : 'glass-card hover:bg-white/5'
                  }`}
                  style={{
                    borderWidth: rank <= 3 ? '2px' : '1px',
                    ...style
                  }}
                  data-testid={`leader-${rank}`}
                >
                  {/* Rank */}
                  <div className="w-10 flex justify-center">
                    {getRankIcon(rank)}
                  </div>
                  
                  {/* Avatar */}
                  <div className="w-12 h-12 rounded-full bg-[#18181b] flex items-center justify-center overflow-hidden border border-white/10">
                    {leader.picture ? (
                      <img src={leader.picture} alt={leader.name} className="w-full h-full object-cover" />
                    ) : (
                      <User className="w-6 h-6 text-white/40" />
                    )}
                  </div>
                  
                  {/* Name & Stats */}
                  <div className="flex-1 min-w-0">
                    <p className={`font-semibold truncate ${isCurrentUser ? 'text-[#00f0ff]' : 'text-white'}`}>
                      {leader.name}
                      {isCurrentUser && <span className="text-xs ml-2 opacity-70">(You)</span>}
                    </p>
                    <p className="text-white/40 text-sm font-mono">
                      {leader.games_played} game{leader.games_played !== 1 ? 's' : ''} played
                    </p>
                  </div>
                  
                  {/* Score */}
                  <div className="text-right">
                    <p className={`text-2xl font-bold font-['Rajdhani'] ${
                      rank === 1 ? 'text-[#ffb700]' : 
                      rank === 2 ? 'text-[#c0c0c0]' : 
                      rank === 3 ? 'text-[#cd7f32]' : 
                      'text-white'
                    }`}>
                      {leader.total_score?.toLocaleString() || 0}
                    </p>
                    <p className="text-white/40 text-xs font-mono uppercase">Points</p>
                  </div>
                </Card>
              );
            })}
          </div>
        )}

        {/* Call to Action */}
        {!user && leaders.length > 0 && (
          <Card className="glass-card p-6 mt-8 text-center animate-fade-in">
            <p className="text-white/70 mb-4">
              Sign in to track your progress and compete for the top spot!
            </p>
            <div className="flex justify-center gap-4">
              <Button
                className="bg-[#00f0ff] text-black font-bold hover:bg-[#00f0ff]/90"
                onClick={() => navigate('/login')}
                data-testid="login-cta-btn"
              >
                Sign In
              </Button>
              <Button
                variant="outline"
                className="border-white/20 text-white hover:bg-white/5"
                onClick={() => navigate('/game')}
                data-testid="play-anonymous-btn"
              >
                Play Anonymous
              </Button>
            </div>
          </Card>
        )}
      </main>
    </div>
  );
}
