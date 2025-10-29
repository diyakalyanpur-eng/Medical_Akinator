
from pydantic import BaseModel
from typing import Optional, List, Dict

class StartGameRequest(BaseModel):
    difficulty: Optional[str] = "medium"

class StartGameResponse(BaseModel):
    session_id: str
    message: str
    difficulty: str
    initial_presentation: str  # NEW: Patient presentation
    patient_context: Dict  # NEW: Age, sex, setting

class AskQuestionRequest(BaseModel):
    session_id: str
    question: str

class AskQuestionResponse(BaseModel):
    answer: str
    explanation: str
    questions_count: int
    differential_diagnosis: List[Dict]  # NEW: Updated differential list

class SubmitDiagnosisRequest(BaseModel):
    session_id: str
    diagnosis: str

class SubmitDiagnosisResponse(BaseModel):
    correct: bool
    actual_disease: str
    questions_used: int
    efficiency_score: int
    feedback: str
    key_features: List[str]
    related_conditions: List[str]
    diagnostic_pathway_quality: str  # NEW: Assessment of reasoning
    essential_questions_asked: int  # NEW
    essential_questions_missed: int  # NEW
    differential_quality: str  # NEW: How well they built differential