

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid
import json
import random
from pathlib import Path

from llm_handler import OllamaHandler
from models import (
    StartGameRequest, StartGameResponse,
    AskQuestionRequest, AskQuestionResponse,
    SubmitDiagnosisRequest, SubmitDiagnosisResponse
)

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

# def generate_patient_presentation(disease_data, disease_name):
#     """Generate initial patient presentation context"""
#     # Extract basic demographics
#     demographics = disease_data.get('demographics', {})
#     age_range = demographics.get('age_range', '45-65')
#     sex = demographics.get('sex', 'equal')
    
#     # Determine age and sex for presentation
#     if '-' in age_range:
#         age = age_range.split('-')[0]  # Use lower bound
#     else:
#         age = age_range
    
#     if sex == 'male_more_common':
#         gender = 'M'
#     elif sex == 'female_more_common':
#         gender = 'F'
#     else:
#         gender = random.choice(['M', 'F'])
    
#     # Extract chief complaint
#     symptoms = disease_data.get('symptoms', {})
#     chief_complaints = []
    
#     for symptom, value in symptoms.items():
#         if value == 'yes' and len(chief_complaints) < 2:
#             chief_complaints.append(symptom.replace('_', ' '))
    
#     if not chief_complaints:
#         chief_complaints = ['symptoms']
    
#     # Get severity/appearance
#     appearance = demographics.get('appearance', 'appears uncomfortable')
    
#     # Build presentation
#     presentation = f"A {age}-year-old {gender} patient presents with {' and '.join(chief_complaints)}. {appearance}."
    
#     return {
#         "text": presentation,
#         "age": age,
#         "sex": gender,
#         "setting": disease_data.get('setting', 'emergency_department')
#     }

# diseases = load_diseases()
# active_sessions = load_sessions()

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
        # "20-40" -> use middle value
        ages = age_range.split('-')[0].strip()
        try:
            age = str(int(ages) + 10)  # Middle of range
        except:
            age = "45"
    elif 'any' in str(age_range).lower():
        age = "55"
    else:
        age = str(age_range).split()[0]  # First number
    
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
        # Fallback: try to extract from primary symptoms
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
diseases = load_diseases()
active_sessions = load_sessions()
@app.on_event("startup")
async def startup_event():
    global diseases
    diseases = load_diseases()
    print(f"Loaded {len(diseases)} diseases")
    print("Server started on http://localhost:8000")

@app.get("/")
async def root():
    return {
        "message": "Disease Akinator API",
        "status": "running",
        "diseases_count": len(diseases)
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "llm_model": "gemma2:2b",
        "diseases_loaded": len(diseases)
    }

@app.get("/api/diseases")
async def list_diseases():
    """List all available diseases"""
    return {
        "count": len(diseases),
        "diseases": [
            {
                "id": d.get("id", "unknown"),
                "name": d.get("name", "Unknown"),
                "category": d.get("category", "Unknown"),
                "difficulty": d.get("difficulty", "medium")
            }
            for d in diseases
        ]
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
    
    # Generate patient presentation
    presentation = generate_patient_presentation(
        selected_disease,
        selected_disease.get("name", "Unknown Disease")
    )
    
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = {
        "disease_id": selected_disease.get("id", "unknown"),
        "disease_name": selected_disease.get("name", "Unknown Disease"),
        "disease_data": selected_disease,
        "difficulty": request.difficulty,
        "questions_asked": [],
        "differential_diagnosis": [],
        "presentation": presentation
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
        }
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
    
    return AskQuestionResponse(
        answer=llm_response["answer"],
        explanation=llm_response["explanation"],
        questions_count=len(session["questions_asked"]),
        differential_diagnosis=session.get("differential_diagnosis", [])
    )

@app.post("/api/submit-diagnosis", response_model=SubmitDiagnosisResponse)
async def submit_diagnosis(request: SubmitDiagnosisRequest):
    """Student submits their diagnosis"""
    if request.session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    session = active_sessions[request.session_id]
    correct_disease = session["disease_name"]
    
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
        differential_quality=f"Built differential with {len(session.get('differential_diagnosis', []))} diseases considered"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)