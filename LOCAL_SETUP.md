# Disease Akinator - Local Setup Guide

## Prerequisites

1. **Python 3.9+** - [Download](https://www.python.org/downloads/)
2. **Node.js 18+** - [Download](https://nodejs.org/)
3. **Ollama** (Optional, for AI-powered answers) - [Download](https://ollama.ai/)

## Project Structure

```
disease-akinator/
├── backend/
│   ├── server.py
│   ├── llm_handler.py
│   ├── bayesian_evaluator.py
│   ├── evaluation_system.py
│   ├── models.py
│   ├── requirements.txt
│   └── data/
│       ├── diseases.json
│       └── sessions.json
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.js
│   │   ├── index.css
│   │   └── pages/
│   └── .env
└── README.md
```

## Step 1: Backend Setup

```bash
# Navigate to backend folder
cd backend

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn python-dotenv requests pydantic

# Create data folder if it doesn't exist
mkdir -p data

# Make sure diseases.json is in the data folder
# (Copy your diseases.json to backend/data/diseases.json)

# Run the backend server
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

The backend will run at: `http://localhost:8001`

## Step 2: Frontend Setup

```bash
# Open a new terminal
# Navigate to frontend folder
cd frontend

# Install dependencies
npm install
# OR if you use yarn:
yarn install

# Create .env file with backend URL
echo "REACT_APP_BACKEND_URL=http://localhost:8001" > .env

# Start the frontend
npm start
# OR:
yarn start
```

The frontend will run at: `http://localhost:3000`

## Step 3: (Optional) Setup Ollama for AI Answers

Without Ollama, the game uses rule-based answers (still works great!).
With Ollama, you get more natural, AI-powered responses.

```bash
# Install Ollama from https://ollama.ai/

# Pull the model
ollama pull gemma2:2b

# Run Ollama (it runs in background by default after installation)
ollama serve
```

## Quick Start Commands

### Terminal 1 - Backend:
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Terminal 2 - Frontend:
```bash
cd frontend
npm start
```

### Terminal 3 - Ollama (Optional):
```bash
ollama run gemma2:2b
```

## Environment Variables

### Backend (.env) - Optional
```
# No required environment variables for local setup
# Ollama runs on default localhost:11434
```

### Frontend (.env) - Required
```
REACT_APP_BACKEND_URL=http://localhost:8001
```

## Troubleshooting

### CORS Errors
- Make sure backend is running on port 8001
- Make sure frontend .env has correct REACT_APP_BACKEND_URL
- Restart both servers after changing .env files

### "No diseases loaded" Error
- Check that `backend/data/diseases.json` exists
- Restart the backend server

### Ollama Connection Errors
- This is normal if Ollama isn't installed
- The game will use rule-based answers instead
- To fix: Install Ollama and run `ollama pull gemma2:2b`

### Port Already in Use
```bash
# Kill process on port 8001 (backend)
# Windows:
netstat -ano | findstr :8001
taskkill /PID <PID> /F

# Mac/Linux:
lsof -i :8001
kill -9 <PID>
```

## Testing the Setup

1. Open `http://localhost:3000` in your browser
2. You should see the landing page with specialties
3. Click "Start Case" to begin a game
4. Ask questions like "Does the patient have fever?"
5. Submit your diagnosis when ready

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/specialties` | GET | List all specialties |
| `/api/start-game` | POST | Start a new game |
| `/api/ask-question` | POST | Ask a question |
| `/api/submit-diagnosis` | POST | Submit diagnosis |

## Need Help?

- Check browser console (F12) for errors
- Check terminal running backend for Python errors
- Ensure all files are in correct locations
