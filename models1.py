from pydantic import BaseModel
from typing import Optional, List, Dict

class StartGameRequest(BaseModel):
    difficulty: Optional[str] = "medium"

class StartGameResponse(BaseModel):
    session_id: str
    message: str
    difficulty: str
    initial_presentation: str
    patient_context: Dict
    optimal_questions: Optional[int] = None  # NEW

class AskQuestionRequest(BaseModel):
    session_id: str
    question: str

class AskQuestionResponse(BaseModel):
    answer: str
    explanation: str
    questions_count: int
    differential_diagnosis: List[Dict]
    optimal_questions: Optional[int] = None  # NEW
    efficiency_status: Optional[str] = None  # NEW: "on track", "acceptable", "too many"

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
    diagnostic_pathway_quality: str
    essential_questions_asked: int
    essential_questions_missed: int
    differential_quality: str
    # NEW: Comprehensive scoring
    detailed_score: Optional[Dict] = None  # Full scoring breakdown
    performance_tier: Optional[str] = None
    optimal_comparison: Optional[Dict] = None