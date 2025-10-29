from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid
import json
import random
from pathlib import Path

from llm_handler import OllamaHandler
from models1 import (
    StartGameRequest, StartGameResponse,
    AskQuestionRequest, AskQuestionResponse,
    SubmitDiagnosisRequest, SubmitDiagnosisResponse
)

# NEW: Import evaluation system
from evaluation.game_scorer import GameScorer

app = FastAPI(title="Disease Akinator API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LLM handler
llm = OllamaHandler(model="gemma2:2b")

# Paths
DATA_DIR = Path(__file__).parent / "data"
DISEASES_FILE = DATA_DIR / "diseases.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"
GENERATED_DIR = DATA_DIR / "generated"  # NEW
OPTIMAL_FILE = GENERATED_DIR / "optimal_questions.json"  # NEW

# Create data directory if it doesn't exist
DATA_DIR.mkdir(exist_ok=True)

if not SESSIONS_FILE.exists():
    with open(SESSIONS_FILE, 'w') as f:
        json.dump({}, f)

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

# NEW: Load optimal data
def load_optimal_data():
    if OPTIMAL_FILE.exists():
        with open(OPTIMAL_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def generate_patient_presentation(disease_data, disease_name):
    """Generate initial patient presentation context"""
    
    # Extract initial presentation data
    initial_pres = disease_data.get('initial_presentation', {})
    demographics = initial_pres.get('patient_demographics', {})
    
    # Get chief complaint - this is the most important part!
    chief_complaint = initial_pres.get('chief_complaint', '')
    setting = initial_pres.get('setting', 'emergency_department')
    
    # Extract age and sex
    age_range = demographics.get('age_range', '45-65')
    sex_info = demographics.get('sex', 'equal')
    appearance = demographics.get('appearance', 'appears uncomfortable')
    
    # Parse age - handle various formats
    if '-' in str(age_range):
        ages = age_range.split('-')[0].strip()
        try:
            age = str(int(ages) + 10)
        except:
            age = "45"
    elif 'any' in str(age_range).lower():
        age = "55"
    else:
        age = str(age_range).split()[0]
    
    # Determine sex for this case
    if 'male predominant' in str(sex_info).lower() or 'male_more_common' in str(sex_info).lower():
        gender = 'M'
    elif 'female predominant' in str(sex_info).lower() or 'female_more_common' in str(sex_info).lower():
        gender = 'F'
    else:
        gender = random.choice(['M', 'F'])
    
    # Format setting nicely
    setting_map = {
        'emergency_department': 'the emergency department',
        'outpatient_clinic': 'the outpatient clinic',
        'hospital': 'the hospital',
        'urgent_care': 'urgent care'
    }
    setting_text = setting_map.get(setting, setting.replace('_', ' '))
    
    # Build presentation using chief complaint
    if chief_complaint:
        presentation = f"A {age}-year-old {gender} patient presents to {setting_text} with {chief_complaint}. The patient {appearance}."
    else:
        # Fallback
        primary_symptoms = disease_data.get('history', {}).get('primary_symptoms', {})
        symptoms_list = []
        for symptom, value in primary_symptoms.items():
            if value == 'yes' and len(symptoms_list) < 2:
                symptoms_list.append(symptom.replace('_', ' '))
        
        if symptoms_list:
            presentation = f"A {age}-year-old {gender} patient presents to {setting_text} with {' and '.join(symptoms_list)}. The patient {appearance}."
        else:
            presentation = f"A {age}-year-old {gender} patient presents to {setting_text} with concerning symptoms. The patient {appearance}."
    
    return {
        "text": presentation,
        "age": age,
        "sex": gender,
        "setting": setting
    }

# Global variables
diseases = load_diseases()
active_sessions = load_sessions()
optimal_data = {}  # NEW
game_scorer = None  # NEW

@app.on_event("startup")
async def startup_event():
    global diseases, optimal_data, game_scorer
    diseases = load_diseases()
    optimal_data = load_optimal_data()
    
    # Initialize scorer if optimal data exists
    if optimal_data:
        game_scorer = GameScorer(optimal_data)
        print(f"✓ Loaded optimal data for {len(optimal_data)} diseases")
    else:
        print("⚠️ No optimal data found. Run setup_evaluation.py first for advanced scoring.")
    
    print(f"✓ Loaded {len(diseases)} diseases")
    print("✓ Server started on http://localhost:8000")

@app.get("/")
async def root():
    return {
        "message": "Disease Akinator API",
        "status": "running",
        "diseases_count": len(diseases),
        "evaluation_system": "enabled" if game_scorer else "disabled"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "llm_model": "gemma2:2b",
        "diseases_loaded": len(diseases),
        "optimal_data_loaded": len(optimal_data),
        "evaluation_enabled": game_scorer is not None
    }

@app.get("/api/diseases")
async def list_diseases():
    """List all available diseases"""
    disease_list = []
    for d in diseases:
        disease_info = {
            "id": d.get("id", "unknown"),
            "name": d.get("name", "Unknown"),
            "category": d.get("category", "Unknown"),
            "difficulty": d.get("difficulty", "medium")
        }
        
        # Add optimal info if available
        if d.get("id") in optimal_data:
            disease_info["optimal_questions"] = optimal_data[d["id"]]["realistic_optimal"]
        
        disease_list.append(disease_info)
    
    return {
        "count": len(diseases),
        "diseases": disease_list
    }

@app.post("/api/start-game", response_model=StartGameResponse)
async def start_game(request: StartGameRequest):
    """Start a new game by randomly selecting a disease"""
    filtered_diseases = [d for d in diseases if d.get("difficulty") == request.difficulty]
    
    if not filtered_diseases:
        filtered_diseases = diseases
    
    if not filtered_diseases:
        raise HTTPException(status_code=404, detail="No diseases found")
    
    selected_disease = random.choice(filtered_diseases)
    disease_id = selected_disease.get("id", "unknown")
    
    # Generate patient presentation
    presentation = generate_patient_presentation(
        selected_disease,
        selected_disease.get("name", "Unknown Disease")
    )
    
    session_id = str(uuid.uuid4())
    
    # Get optimal questions for this disease
    optimal_questions = None
    if disease_id in optimal_data:
        optimal_questions = optimal_data[disease_id]["realistic_optimal"]
    
    active_sessions[session_id] = {
        "disease_id": disease_id,
        "disease_name": selected_disease.get("name", "Unknown Disease"),
        "disease_data": selected_disease,
        "difficulty": request.difficulty,
        "questions_asked": [],
        "differential_diagnosis": [],
        "presentation": presentation,
        "optimal_questions": optimal_questions  # NEW
    }
    
    save_sessions(active_sessions)
    
    return StartGameResponse(
        session_id=session_id,
        message=f"A new patient has arrived. Gather history and make your diagnosis.",
        difficulty=request.difficulty,
        initial_presentation=presentation['text'],
        patient_context={
            "age": presentation['age'],
            "sex": presentation['sex'],
            "setting": presentation['setting']
        },
        optimal_questions=optimal_questions  # NEW
    )

@app.post("/api/ask-question", response_model=AskQuestionResponse)
async def ask_question(request: AskQuestionRequest):
    """Student asks a question, LLM answers based on disease data"""
    if request.session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    session = active_sessions[request.session_id]
    
    # Use LLM to answer the question
    llm_response = llm.answer_medical_question(
        disease_data=session["disease_data"],
        disease_name=session["disease_name"],
        question=request.question
    )
    
    if llm_response["answer"] == "ERROR":
        raise HTTPException(status_code=500, detail=llm_response["explanation"])
    
    # Store question and answer
    qa_entry = {
        "question": request.question,
        "answer": llm_response["answer"],
        "explanation": llm_response["explanation"]
    }
    session["questions_asked"].append(qa_entry)
    
    # Update differential diagnosis after every 2-3 questions
    if len(session["questions_asked"]) >= 3 and len(session["questions_asked"]) % 2 == 0:
        differential = llm.update_differential_diagnosis(
            disease_name=session["disease_name"],
            questions_asked=session["questions_asked"],
            all_diseases=diseases
        )
        session["differential_diagnosis"] = differential
    
    save_sessions(active_sessions)
    
    # NEW: Calculate efficiency status
    efficiency_status = None
    optimal_questions = session.get("optimal_questions")
    
    if optimal_questions:
        questions_count = len(session["questions_asked"])
        if questions_count <= optimal_questions:
            efficiency_status = "on track"
        elif questions_count <= int(optimal_questions * 1.5):
            efficiency_status = "acceptable"
        else:
            efficiency_status = "too many questions"
    
    return AskQuestionResponse(
        answer=llm_response["answer"],
        explanation=llm_response["explanation"],
        questions_count=len(session["questions_asked"]),
        differential_diagnosis=session.get("differential_diagnosis", []),
        optimal_questions=optimal_questions,  # NEW
        efficiency_status=efficiency_status  # NEW
    )

@app.post("/api/submit-diagnosis", response_model=SubmitDiagnosisResponse)
async def submit_diagnosis(request: SubmitDiagnosisRequest):
    """Student submits their diagnosis"""
    if request.session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    session = active_sessions[request.session_id]
    correct_disease = session["disease_name"]
    disease_id = session["disease_id"]
    
    # Check diagnosis
    check_result = llm.check_diagnosis(correct_disease, request.diagnosis)
    
    # Assess diagnostic quality
    quality_assessment = llm.assess_diagnostic_quality(
        questions_asked=session["questions_asked"],
        disease_data=session["disease_data"],
        correct_disease=correct_disease
    )
    
    # Calculate scores
    questions_count = len(session["questions_asked"])
    
    # NEW: Use advanced scoring if available
    detailed_score = None
    performance_tier = None
    optimal_comparison = None
    
    if game_scorer and disease_id in optimal_data:
        score_result = game_scorer.calculate_score(
            disease_id=disease_id,
            questions_asked=session["questions_asked"],
            correct=check_result["correct"],
            hints_used=0
        )
        
        detailed_score = score_result
        performance_tier = score_result['performance_tier']
        optimal_comparison = score_result['optimal_info']
        efficiency_score = score_result['breakdown']['efficiency']
    else:
        # Fallback scoring
        efficiency_score = max(0, 100 - (questions_count * 5))
    
    # Get disease info
    disease_data = session["disease_data"]
    key_features = disease_data.get("key_features", [])
    related_conditions = disease_data.get("related_conditions", [])
    
    # Clean up session
    del active_sessions[request.session_id]
    save_sessions(active_sessions)
    
    return SubmitDiagnosisResponse(
        correct=check_result["correct"],
        actual_disease=correct_disease,
        questions_used=questions_count,
        efficiency_score=efficiency_score,
        feedback=check_result["reasoning"],
        key_features=key_features[:5] if key_features else [],
        related_conditions=related_conditions[:5] if related_conditions else [],
        diagnostic_pathway_quality=quality_assessment.get("pathway_quality", "unknown"),
        essential_questions_asked=quality_assessment.get("essential_asked", 0),
        essential_questions_missed=quality_assessment.get("essential_missed", 0),
        differential_quality=f"Built differential with {len(session.get('differential_diagnosis', []))} diseases considered",
        detailed_score=detailed_score,  # NEW
        performance_tier=performance_tier,  # NEW
        optimal_comparison=optimal_comparison  # NEW
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)