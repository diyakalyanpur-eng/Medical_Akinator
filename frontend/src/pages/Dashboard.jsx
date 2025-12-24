import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Brain, Trophy, Target, Play, LogOut, User, TrendingUp, Clock, Star, ArrowRight } from 'lucide-react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Dashboard() {
  const navigate = useNavigate();
  const { user, token, logout } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      fetchStats();
    }
  }, [token]);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/user/stats`, {
        headers: { Authorization: `Bearer ${token}` },
        withCredentials: true
      });
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-[#00f0ff] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#09090b] relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-grid opacity-30" />
      <div className="absolute inset-0 bg-gradient-radial" />

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between p-6 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-[#00f0ff]/20 flex items-center justify-center neon-border">
            <Brain className="w-6 h-6 text-[#00f0ff]" />
          </div>
          <span className="text-xl font-bold text-white font-['Rajdhani'] tracking-wider">DR. NEURO</span>
        </div>
        
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            className="text-white/70 hover:text-white hover:bg-white/5"
            onClick={() => navigate('/leaderboard')}
            data-testid="leaderboard-btn"
          >
            <Trophy className="w-4 h-4 mr-2" />
            Leaderboard
          </Button>
          <Button
            variant="ghost"
            className="text-white/70 hover:text-red-400 hover:bg-red-400/10"
            onClick={handleLogout}
            data-testid="logout-btn"
          >
            <LogOut className="w-4 h-4" />
          </Button>
        </div>
      </header>

      <main className="relative z-10 max-w-6xl mx-auto px-6 py-8">
        {/* Welcome Section */}
        <div className="mb-8 animate-slide-up">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 rounded-full bg-[#18181b] flex items-center justify-center border border-white/10 overflow-hidden">
              {user?.picture ? (
                <img src={user.picture} alt={user.name} className="w-full h-full object-cover" />
              ) : (
                <User className="w-8 h-8 text-white/40" />
              )}
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-white font-['Rajdhani']">
                Welcome back, {user?.name?.split(' ')[0]}!
              </h1>
              <p className="text-white/50">{user?.email}</p>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid md:grid-cols-3 gap-6 mb-8">
          <Card className="glass p-6 animate-fade-in" style={{ animationDelay: '0.1s' }}>
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 rounded-lg bg-[#00f0ff]/20 flex items-center justify-center">
                <Target className="w-6 h-6 text-[#00f0ff]" />
              </div>
              <TrendingUp className="w-5 h-5 text-[#00ff9d]" />
            </div>
            <p className="text-3xl font-bold text-white font-['Rajdhani']">
              {stats?.user?.total_games || 0}
            </p>
            <p className="text-white/50 text-sm">Games Played</p>
          </Card>

          <Card className="glass p-6 animate-fade-in" style={{ animationDelay: '0.2s' }}>
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 rounded-lg bg-[#7d00ff]/20 flex items-center justify-center">
                <Trophy className="w-6 h-6 text-[#7d00ff]" />
              </div>
              <Star className="w-5 h-5 text-[#ffb700]" />
            </div>
            <p className="text-3xl font-bold text-white font-['Rajdhani']">
              {stats?.user?.total_score?.toLocaleString() || 0}
            </p>
            <p className="text-white/50 text-sm">Total Score</p>
          </Card>

          <Card className="glass p-6 animate-fade-in" style={{ animationDelay: '0.3s' }}>
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 rounded-lg bg-[#00ff9d]/20 flex items-center justify-center">
                <Clock className="w-6 h-6 text-[#00ff9d]" />
              </div>
            </div>
            <p className="text-3xl font-bold text-white font-['Rajdhani']">
              {stats?.user?.total_games > 0 
                ? Math.round(stats.user.total_score / stats.user.total_games) 
                : 0}
            </p>
            <p className="text-white/50 text-sm">Avg. Score</p>
          </Card>
        </div>

        {/* Quick Actions */}
        <Card className="glass p-6 mb-8 animate-slide-up">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-white font-['Rajdhani'] mb-1">
                Ready for another challenge?
              </h2>
              <p className="text-white/50">Test your diagnostic skills across 10 specialties</p>
            </div>
            <Button
              className="bg-[#00f0ff] text-black font-bold px-8 py-6 hover:bg-[#00f0ff]/90"
              onClick={() => navigate('/game')}
              data-testid="start-game-btn"
            >
              <Play className="w-5 h-5 mr-2" />
              Start New Game
            </Button>
          </div>
        </Card>

        {/* Recent Games */}
        <Card className="glass p-6 animate-fade-in">
          <h2 className="text-xl font-bold text-white font-['Rajdhani'] mb-6">Recent Games</h2>
          
          {stats?.recent_games?.length > 0 ? (
            <div className="space-y-3">
              {stats.recent_games.map((game, index) => (
                <div
                  key={game.game_id}
                  className="flex items-center justify-between p-4 bg-[#18181b]/50 rounded-lg border border-white/5 hover:border-white/10 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-[#7d00ff]/20 flex items-center justify-center">
                      <Brain className="w-5 h-5 text-[#7d00ff]" />
                    </div>
                    <div>
                      <p className="text-white font-medium capitalize">
                        {game.specialty?.replace(/_/g, ' ')}
                      </p>
                      <p className="text-white/40 text-sm font-mono">
                        {game.diagnosis || 'Unknown'}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-[#00f0ff] font-bold font-['Rajdhani'] text-xl">
                      {game.score}
                    </p>
                    <p className="text-white/40 text-xs font-mono">points</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Brain className="w-12 h-12 text-white/20 mx-auto mb-4" />
              <p className="text-white/50 mb-4">No games played yet</p>
              <Button
                variant="outline"
                className="border-white/20 text-white hover:bg-white/5"
                onClick={() => navigate('/game')}
              >
                Play Your First Game
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          )}
        </Card>

        {/* Specialty Breakdown */}
        {stats?.specialty_stats?.length > 0 && (
          <Card className="glass p-6 mt-6 animate-fade-in">
            <h2 className="text-xl font-bold text-white font-['Rajdhani'] mb-6">Specialty Performance</h2>
            <div className="grid md:grid-cols-2 gap-4">
              {stats.specialty_stats.map((stat) => (
                <div
                  key={stat._id}
                  className="flex items-center justify-between p-4 bg-[#18181b]/50 rounded-lg"
                >
                  <div>
                    <p className="text-white font-medium capitalize">
                      {stat._id?.replace(/_/g, ' ')}
                    </p>
                    <p className="text-white/40 text-sm">
                      {stat.count} game{stat.count !== 1 ? 's' : ''}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-[#00ff9d] font-bold">
                      Avg: {Math.round(stat.avg_score || 0)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}
      </main>
    </div>
  );
}
