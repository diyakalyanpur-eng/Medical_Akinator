import React, { createContext, useContext, useState, useEffect } from 'react';
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import axios from "axios";
import { Toaster } from 'sonner';

// Context - simplified without auth
const GameContext = createContext(null);

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Game Provider
export const GameProvider = ({ children }) => {
  const [currentGame, setCurrentGame] = useState(null);

  return (
    <GameContext.Provider value={{ currentGame, setCurrentGame, API }}>
      {children}
    </GameContext.Provider>
  );
};

export const useGame = () => useContext(GameContext);

// Lazy load pages
const Landing = React.lazy(() => import('./pages/Landing'));
const Game = React.lazy(() => import('./pages/Game'));
const GamePlay = React.lazy(() => import('./pages/GamePlay'));
const Results = React.lazy(() => import('./pages/Results'));
const Leaderboard = React.lazy(() => import('./pages/Leaderboard'));

// App Router
function AppRouter() {
  return (
    <React.Suspense fallback={
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-[#00f0ff] border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/game" element={<Game />} />
        <Route path="/play/:gameId" element={<GamePlay />} />
        <Route path="/results/:gameId" element={<Results />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
      </Routes>
    </React.Suspense>
  );
}

function App() {
  return (
    <div className="App min-h-screen bg-[#09090b]">
      <BrowserRouter>
        <GameProvider>
          <Toaster 
            position="top-center" 
            richColors 
            theme="dark"
            toastOptions={{
              style: {
                background: '#18181b',
                border: '1px solid rgba(255,255,255,0.1)',
                color: '#fafafa'
              }
            }}
          />
          <AppRouter />
        </GameProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
