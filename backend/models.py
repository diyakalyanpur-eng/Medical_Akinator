from pydantic import BaseModel
from typing import Optional, List, Dict

class StartGameRequest(BaseModel):
    specialty: str = "general"
    is_anonymous: bool = False
    difficulty: Optional[str] = "medium"

class StartGameResponse(BaseModel):
    session_id: str
    message: str
    difficulty: str
    initial_presentation: str
    patient_context: Dict

class AskQuestionRequest(BaseModel):
    session_id: str
    question: str

class AskQuestionResponse(BaseModel):
    answer: str
    explanation: str
    questions_count: int
    differential_diagnosis: List[Dict]

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
