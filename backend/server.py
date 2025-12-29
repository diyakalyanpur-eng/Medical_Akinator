from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import uuid
import json
import random
import re
from pathlib import Path
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import modules
from llm_handler import OllamaHandler
from evaluation_system import PerformanceEvaluator
from models import (
    StartGameRequest, StartGameResponse,
    AskQuestionRequest, AskQuestionResponse,
    SubmitDiagnosisRequest, SubmitDiagnosisResponse
)

# Custom CORS middleware for maximum compatibility
class CORSHandler(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Handle preflight OPTIONS requests
        if request.method == "OPTIONS":
            response = Response()
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Max-Age"] = "3600"
            return response
        
        # Process the request
        response = await call_next(request)
        
        # Add CORS headers to all responses
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        
        return response

# Initialize components
llm = OllamaHandler(model="gemma2:2b")
evaluator = PerformanceEvaluator()

# Paths
DATA_DIR = ROOT_DIR / "data"
DISEASES_FILE = DATA_DIR / "diseases.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"

# Create data directory if it doesn't exist
DATA_DIR.mkdir(exist_ok=True)

if not SESSIONS_FILE.exists():
    with open(SESSIONS_FILE, 'w') as f:
        json.dump({}, f)

# Load data functions
def load_diseases():
    if DISEASES_FILE.exists():
        with open(DISEASES_FILE, 'r') as f:
            return json.load(f)
    return []

def load_sessions():
    if SESSIONS_FILE.exists():
        with open(SESSIONS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_sessions(sessions):
    with open(SESSIONS_FILE, 'w') as f:
        json.dump(sessions, f, indent=2)

# Global variables for data
diseases = []
active_sessions = {}

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    global diseases, active_sessions
    diseases = load_diseases()
    active_sessions = load_sessions()
    print(f"Loaded {len(diseases)} diseases")
    print("Server started on http://0.0.0.0:8001")
    yield
    print("Server shutting down...")
    save_sessions(active_sessions)

# Create app with lifespan
app = FastAPI(title="Disease Akinator API", lifespan=lifespan)

# CORS middleware - configured for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "*"  # Allow all origins for flexibility
    ],
    allow_credentials=False,  # Set to False when using "*" origins
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# ==================== PYDANTIC MODELS ====================
class SpecialtyInfo(BaseModel):
    name: str
    description: str
    disease_count: int

class GameStartRequest(BaseModel):
    specialty: str = "general"
    is_anonymous: bool = True

class GameStartResponse(BaseModel):
    game_id: str
    specialty: str
    question_number: int
    question: str
    symptom_key: str
    max_questions: int = 10
    initial_presentation: Optional[str] = None

class GameAnswerRequest(BaseModel):
    game_id: str
    answer: str  # yes/no/maybe/dont_know

class GameAnswerResponse(BaseModel):
    game_completed: bool
    question_number: Optional[int] = None
    question: Optional[str] = None
    symptom_key: Optional[str] = None
    top_candidates: Optional[List[Dict]] = None
    correct: Optional[bool] = None
    disease_name: Optional[str] = None
    score: Optional[int] = None
    questions_used: Optional[int] = None
    diagnosis: Optional[Dict] = None

class GameHintRequest(BaseModel):
    game_id: str

class GameHintResponse(BaseModel):
    hint: str

# ==================== HELPER FUNCTIONS ====================
def get_specialties_from_diseases():
    """Extract unique specialties from diseases data"""
    specialties = {}
    for disease in diseases:
        category = disease.get('category', 'general')
        if '/' in category:
            main_category = category.split('/')[0].lower()
        else:
            main_category = category.lower()

        if main_category not in specialties:
            specialties[main_category] = {
                'name': main_category.replace('_', ' ').title(),
                'description': f"Diagnose diseases related to {main_category.replace('_', ' ')}",
                'disease_count': 0
            }
        specialties[main_category]['disease_count'] += 1
    return specialties

def generate_patient_presentation(disease_data, disease_name):
    """Generate initial patient presentation context"""
    initial_pres = disease_data.get('initial_presentation', {})
    demographics = initial_pres.get('patient_demographics', {})

    chief_complaint = initial_pres.get('chief_complaint', '')
    setting = initial_pres.get('setting', 'emergency_department')

    age_range = demographics.get('age_range', '45-65')
    sex_info = demographics.get('sex', 'equal')
    appearance = demographics.get('appearance', 'appears uncomfortable')

    age_str = str(age_range)
    if 'peak' in age_str:
        age_str = age_str.split('peak')[0].strip()

    if '-' in age_str:
        ages = age_str.split('-')
        try:
            low = int(ages[0].strip())
            high = int(ages[1].strip())
            age = str((low + high) // 2)
        except:
            age = "35"
    else:
        numbers = re.findall(r'\d+', age_str)
        age = numbers[0] if numbers else "35"

    if 'male' in str(sex_info).lower() and 'female' not in str(sex_info).lower():
        gender = 'M'
    elif 'female' in str(sex_info).lower():
        gender = 'F'
    else:
        gender = random.choice(['M', 'F'])

    setting_map = {
        'emergency_department': 'the emergency department',
        'outpatient_clinic': 'the outpatient clinic',
        'hospital': 'the hospital',
        'urgent_care': 'urgent care'
    }
    setting_text = setting_map.get(setting, setting.replace('_', ' '))

    if chief_complaint:
        presentation = f"A {age}-year-old {gender} patient presents to {setting_text} with {chief_complaint}. The patient {appearance}."
    else:
        presentation = f"A {age}-year-old {gender} patient presents to {setting_text} with concerning symptoms. The patient {appearance}."

    return {
        "text": presentation,
        "age": age,
        "sex": gender,
        "setting": setting
    }

def get_next_question(disease_data, asked_questions):
    """Get next question based on what hasn't been asked"""
    all_symptoms = []
    history = disease_data.get('history', {})
    primary = history.get('primary_symptoms', {})
    all_symptoms.extend(primary.keys())
    associated = history.get('associated_symptoms', {})
    all_symptoms.extend(associated.keys())
    physical = disease_data.get('physical_exam', {})
    if isinstance(physical, dict):
        for system, findings in physical.items():
            if isinstance(findings, dict) and system not in ['vital_signs']:
                all_symptoms.extend([f"{system}_{k}" for k in findings.keys()])

    tests = disease_data.get('diagnostic_tests', {}).get('available_tests', {})
    all_symptoms.extend([f"need_{test}" for test in tests.keys()][:3])

    asked_keys = [q.get('symptom_key', '') for q in asked_questions]
    available_symptoms = [s for s in all_symptoms if s not in asked_keys]

    if not available_symptoms:
        return None, None

    symptom_key = None
    if len(asked_questions) < 3:
        primary_available = [s for s in primary.keys() if s not in asked_keys]
        if primary_available:
            symptom_key = primary_available[0]

    if not symptom_key:
        symptom_key = random.choice(available_symptoms)

    question_templates = {
        'sore_throat': 'Does the patient have a sore throat?',
        'fever': 'Does the patient have a fever?',
        'cough': 'Is the patient coughing?',
        'odynophagia': 'Does the patient have painful swallowing?',
        'headache': 'Does the patient have a headache?',
        'abdominal_pain': 'Does the patient have abdominal pain?',
        'rhinorrhea': 'Does the patient have a runny nose?',
        'hoarseness': 'Is the patient hoarse?',
        'rash': 'Does the patient have a rash?',
        'lymph_nodes': 'Are there enlarged or tender lymph nodes?',
        'tonsillar_exudates': 'Are there white patches on the tonsils?',
        'myalgias': 'Does the patient have muscle aches (myalgias)?',
        'dry_cough': 'Does the patient have a dry cough?',
        'fatigue': 'Is the patient experiencing fatigue?',
        'chills': 'Does the patient have chills?',
        'nausea_vomiting': 'Does the patient have nausea or vomiting?',
        'diarrhea': 'Does the patient have diarrhea?',
        'dyspnea': 'Does the patient have shortness of breath?',
    }

    question = question_templates.get(
        symptom_key,
        f"Does the patient have {symptom_key.replace('_', ' ')}?"
    )

    return question, symptom_key

def check_answer_match(disease_data, symptom_key, answer):
    """Check if the answer matches the disease data"""
    history = disease_data.get('history', {})
    primary = history.get('primary_symptoms', {})
    associated = history.get('associated_symptoms', {})
    all_symptoms = {**primary, **associated}

    expected = all_symptoms.get(symptom_key, None)
    if expected is None:
        return False

    expected_lower = str(expected).lower()
    answer_lower = answer.lower()

    if answer_lower == 'yes':
        return 'yes' in expected_lower or 'severe' in expected_lower or 'prominent' in expected_lower
    elif answer_lower == 'no':
        return 'no' in expected_lower or 'absent' in expected_lower or 'rare' in expected_lower
    elif answer_lower == 'sometimes' or answer_lower == 'maybe':
        return 'sometimes' in expected_lower or 'may' in expected_lower
    return False

# ==================== API ENDPOINTS ====================
@app.get("/api/")
async def root():
    return {"message": "Disease Akinator API - Medical Diagnosis Game"}

@app.get("/api/specialties")
async def get_specialties():
    """Get list of specialties with disease counts"""
    specialties = get_specialties_from_diseases()
    return [[key, value] for key, value in specialties.items()]

@app.post("/api/game/start", response_model=GameStartResponse)
async def start_game(request: GameStartRequest):
    """Start a new game session"""
    if not diseases:
        raise HTTPException(status_code=500, detail="No diseases loaded. Please add diseases.json to data folder.")

    specialty = request.specialty.lower()
    
    # Filter diseases by specialty
    specialty_diseases = [
        d for d in diseases
        if specialty in d.get('category', '').lower() or specialty == 'general'
    ]
    
    if not specialty_diseases:
        specialty_diseases = diseases  # Fall back to all diseases

    selected_disease = random.choice(specialty_diseases)
    disease_name = selected_disease['name']

    game_id = f"game_{uuid.uuid4().hex[:12]}"
    patient_presentation = generate_patient_presentation(selected_disease, disease_name)

    # Get first question
    first_q, first_key = get_next_question(selected_disease, [])

    session = {
        "game_id": game_id,
        "disease_name": disease_name,
        "disease_data": selected_disease,
        "questions_asked": [],
        "differential_diagnosis": [],
        "differential_history": [],
        "patient_presentation": patient_presentation,
        "current_question": {
            "question": first_q,
            "symptom_key": first_key,
            "number": 1
        },
        "created_at": time.time()
    }

    active_sessions[game_id] = session
    save_sessions(active_sessions)

    return GameStartResponse(
        game_id=game_id,
        specialty=specialty,
        question_number=1,
        question=first_q,
        symptom_key=first_key,
        max_questions=10,
        initial_presentation=patient_presentation["text"]
    )

@app.post("/api/game/answer", response_model=GameAnswerResponse)
async def submit_answer(request: GameAnswerRequest):
    """Submit an answer and get next question or results"""
    if request.game_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Game not found")

    session = active_sessions[request.game_id]
    disease_data = session["disease_data"]
    answer = request.answer.lower()

    # Record the answer
    current_q = session["current_question"]
    matches = check_answer_match(disease_data, current_q["symptom_key"], answer)

    qa_entry = {
        "question": current_q["question"],
        "symptom_key": current_q["symptom_key"],
        "answer": answer.upper(),
        "matches": matches
    }
    session["questions_asked"].append(qa_entry)

    questions_count = len(session["questions_asked"])

    # Check if game should end (10 questions or high confidence)
    if questions_count >= 10:
        # Calculate final score
        correct_count = sum(1 for q in session["questions_asked"] if q.get('matches', False))
        score = int((correct_count / questions_count) * 100)

        # Get teaching points
        teaching_points = disease_data.get('teaching_points', [])[:5]
        key_features = disease_data.get('key_features', [])[:5]

        result = {
            "game_completed": True,
            "correct": score >= 60,
            "disease_name": session["disease_name"],
            "score": score,
            "questions_used": questions_count,
            "diagnosis": {
                "icd_code": disease_data.get("icd10_code", "Unknown"),
                "name": session["disease_name"],
                "probability": score,
                "education": teaching_points + key_features
            }
        }

        del active_sessions[request.game_id]
        save_sessions(active_sessions)

        return GameAnswerResponse(**result)

    # Get next question
    next_q, next_key = get_next_question(disease_data, session["questions_asked"])

    if not next_q:
        # No more questions - end game
        correct_count = sum(1 for q in session["questions_asked"] if q.get('matches', False))
        score = int((correct_count / questions_count) * 100)
        
        teaching_points = disease_data.get('teaching_points', [])[:5]
        key_features = disease_data.get('key_features', [])[:5]

        result = {
            "game_completed": True,
            "correct": score >= 60,
            "disease_name": session["disease_name"],
            "score": score,
            "questions_used": questions_count,
            "diagnosis": {
                "icd_code": disease_data.get("icd10_code", "Unknown"),
                "name": session["disease_name"],
                "probability": score,
                "education": teaching_points + key_features
            }
        }

        del active_sessions[request.game_id]
        save_sessions(active_sessions)

        return GameAnswerResponse(**result)

    # Update differential every few questions
    top_candidates = []
    if questions_count >= 3 and questions_count % 2 == 1:
        differential = disease_data.get('differential_diagnosis', {}).get('early_differential', [])
        if differential:
            correct_ratio = sum(1 for q in session["questions_asked"] if q.get('matches', False)) / questions_count

            if correct_ratio > 0.7:
                top_candidates = [
                    {"name": session["disease_name"], "probability": 85},
                    {"name": differential[0] if differential else "Unknown", "probability": 60},
                    {"name": differential[1] if len(differential) > 1 else "Unknown", "probability": 40}
                ]
            else:
                top_candidates = [
                    {"name": differential[0] if differential else "Unknown", "probability": 70},
                    {"name": session["disease_name"], "probability": 50},
                    {"name": differential[1] if len(differential) > 1 else "Unknown", "probability": 30}
                ]

        session["differential_diagnosis"] = top_candidates

    # Update session
    session["current_question"] = {
        "question": next_q,
        "symptom_key": next_key,
        "number": questions_count + 1
    }

    save_sessions(active_sessions)

    return GameAnswerResponse(
        game_completed=False,
        question_number=questions_count + 1,
        question=next_q,
        symptom_key=next_key,
        top_candidates=top_candidates
    )

@app.post("/api/game/hint", response_model=GameHintResponse)
async def get_hint(request: GameHintRequest):
    """Get a hint for the current question"""
    if request.game_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Game not found")

    session = active_sessions[request.game_id]
    current_symptom = session["current_question"]["symptom_key"]

    hints = {
        'chest_pain': 'Consider the nature, location, and radiation of the pain',
        'shortness_of_breath': 'Think about onset, severity, and associated symptoms',
        'fever': 'Temperature patterns can be diagnostic',
        'cough': 'Is it productive or dry? Any blood?',
        'headache': 'Location, severity, and timing matter',
        'myalgias': 'Muscle aches are common in viral syndromes',
        'fatigue': 'Consider acute vs chronic fatigue patterns',
        'sore_throat': 'Look for exudates and lymphadenopathy'
    }

    hint = hints.get(current_symptom, f"Think about whether {current_symptom.replace('_', ' ')} is typical for this condition")

    return GameHintResponse(hint=hint)

@app.get("/api/game/{game_id}/education")
async def get_education(game_id: str):
    """Get educational content for a completed game"""
    # Try to find in session or return generic
    return {
        "ai_summary": "Review the key clinical features and differential diagnosis for this condition.",
        "ai_enhanced": False
    }

# Original endpoints for backward compatibility
@app.post("/api/start-game", response_model=StartGameResponse)
async def start_game_original(request: StartGameRequest = StartGameRequest()):
    """Original start game endpoint"""
    if not diseases:
        raise HTTPException(status_code=500, detail="No diseases loaded")

    selected_disease = random.choice(diseases)
    disease_name = selected_disease['name']

    session_id = str(uuid.uuid4())
    patient_presentation = generate_patient_presentation(selected_disease, disease_name)

    session = {
        "session_id": session_id,
        "disease_name": disease_name,
        "disease_data": selected_disease,
        "questions_asked": [],
        "differential_diagnosis": [],
        "differential_history": [],
        "patient_presentation": patient_presentation,
        "created_at": time.time()
    }

    active_sessions[session_id] = session
    save_sessions(active_sessions)

    return StartGameResponse(
        session_id=session_id,
        message=f"Game started! I've selected a {request.difficulty} difficulty disease.",
        difficulty=request.difficulty,
        initial_presentation=patient_presentation["text"],
        patient_context={
            "age": patient_presentation["age"],
            "sex": patient_presentation["sex"],
            "setting": patient_presentation["setting"]
        }
    )

@app.post("/api/ask-question", response_model=AskQuestionResponse)
async def ask_question_original(request: AskQuestionRequest):
    """Original ask question endpoint"""
    if request.session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")

    session = active_sessions[request.session_id]

    llm_response = llm.answer_medical_question(
        disease_data=session["disease_data"],
        disease_name=session["disease_name"],
        question=request.question
    )

    if llm_response["answer"] == "ERROR":
        raise HTTPException(status_code=500, detail=llm_response["explanation"])

    qa_entry = {
        "question": request.question,
        "answer": llm_response["answer"],
        "explanation": llm_response["explanation"]
    }
    session["questions_asked"].append(qa_entry)

    differential = []
    if len(session["questions_asked"]) >= 3:
        differential = llm.update_differential_diagnosis(
            disease_name=session["disease_name"],
            questions_asked=session["questions_asked"],
            all_diseases=diseases,
            disease_data=session["disease_data"]
        )
        session["differential_diagnosis"] = differential
        session["differential_history"].append(differential)

    save_sessions(active_sessions)

    return AskQuestionResponse(
        answer=llm_response["answer"],
        explanation=llm_response["explanation"],
        questions_count=len(session["questions_asked"]),
        differential_diagnosis=session.get("differential_diagnosis", [])
    )

@app.post("/api/submit-diagnosis", response_model=SubmitDiagnosisResponse)
async def submit_diagnosis_original(request: SubmitDiagnosisRequest):
    """Original submit diagnosis endpoint"""
    if request.session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")

    session = active_sessions[request.session_id]
    correct_disease = session["disease_name"]
    disease_data = session["disease_data"]

    check_result = llm.check_diagnosis(correct_disease, request.diagnosis)

    question_eval = evaluator.evaluate_question_quality(
        questions_asked=session["questions_asked"],
        disease_data=disease_data,
        disease_name=correct_disease
    )

    differential_eval = evaluator.evaluate_differential_accuracy(
        differential_history=session.get("differential_history", []),
        correct_disease=correct_disease,
        disease_data=disease_data
    )

    comprehensive = evaluator.generate_comprehensive_feedback(
        question_evaluation=question_eval,
        differential_evaluation=differential_eval,
        disease_name=correct_disease,
        questions_asked=session["questions_asked"]
    )

    questions_count = len(session["questions_asked"])
    key_features = disease_data.get('key_features', [])[:5]
    related_conditions = disease_data.get('related_conditions', [])[:5]

    del active_sessions[request.session_id]
    save_sessions(active_sessions)

    return SubmitDiagnosisResponse(
        correct=check_result["correct"],
        actual_disease=correct_disease,
        questions_used=questions_count,
        efficiency_score=comprehensive['overall_score'],
        feedback=check_result['reasoning'],
        key_features=key_features,
        related_conditions=related_conditions,
        diagnostic_pathway_quality=comprehensive['performance_level'],
        essential_questions_asked=question_eval['essential_questions_asked'],
        essential_questions_missed=question_eval['essential_questions_missed'],
        differential_quality=f"Accuracy: {differential_eval['accuracy_score']}/100"
    )

@app.get("/api/leaderboard")
async def get_leaderboard():
    """Get leaderboard - placeholder for now"""
    return []

@app.get("/api/user/stats")
async def get_user_stats():
    """Get user stats - placeholder for now"""
    return {
        "user": {"name": "Guest", "total_games": 0, "total_score": 0},
        "recent_games": [],
        "specialty_stats": []
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
