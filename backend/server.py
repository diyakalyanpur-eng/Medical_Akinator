from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-key')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 168  # 7 days

# Emergent LLM Key
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ MODELS ============
class UserCreate(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    total_games: int = 0
    correct_diagnoses: int = 0
    score: int = 0

class GameStartRequest(BaseModel):
    specialty: str
    is_anonymous: bool = False

class GameAnswerRequest(BaseModel):
    game_id: str
    answer: str  # "yes", "no", "maybe", "dont_know"

class HintRequest(BaseModel):
    game_id: str

# ============ ICD-10 DISEASE DATABASE ============
# Comprehensive medical database organized by specialty
SPECIALTIES = {
    "cardiology": {
        "name": "Cardiology",
        "icon": "Heart",
        "description": "Heart and cardiovascular system",
        "color": "#ff0055"
    },
    "neurology": {
        "name": "Neurology",
        "icon": "Brain",
        "description": "Brain and nervous system",
        "color": "#7d00ff"
    },
    "pulmonology": {
        "name": "Pulmonology",
        "icon": "Wind",
        "description": "Respiratory system",
        "color": "#00f0ff"
    },
    "gastroenterology": {
        "name": "Gastroenterology",
        "icon": "Utensils",
        "description": "Digestive system",
        "color": "#ffb700"
    },
    "endocrinology": {
        "name": "Endocrinology",
        "icon": "Activity",
        "description": "Hormonal disorders",
        "color": "#00ff9d"
    },
    "nephrology": {
        "name": "Nephrology",
        "icon": "Droplet",
        "description": "Kidney diseases",
        "color": "#ff6b35"
    },
    "rheumatology": {
        "name": "Rheumatology",
        "icon": "Bone",
        "description": "Musculoskeletal diseases",
        "color": "#9d4edd"
    },
    "infectious_disease": {
        "name": "Infectious Disease",
        "icon": "Bug",
        "description": "Infections and pathogens",
        "color": "#38b000"
    },
    "dermatology": {
        "name": "Dermatology",
        "icon": "Scan",
        "description": "Skin conditions",
        "color": "#fb8500"
    },
    "psychiatry": {
        "name": "Psychiatry",
        "icon": "BrainCircuit",
        "description": "Mental health disorders",
        "color": "#8338ec"
    }
}

DISEASES_DB = {
    "cardiology": [
        {
            "icd_code": "I21.9",
            "name": "Acute Myocardial Infarction",
            "symptoms": {
                "chest_pain": 0.95,
                "radiating_arm_pain": 0.75,
                "shortness_of_breath": 0.70,
                "sweating": 0.65,
                "nausea": 0.50,
                "jaw_pain": 0.40,
                "fatigue": 0.60,
                "palpitations": 0.45
            },
            "education": [
                "Acute MI occurs when blood flow to heart muscle is blocked",
                "Time-sensitive: 'door-to-balloon' time should be <90 minutes",
                "Troponin levels rise 3-6 hours after onset",
                "ECG changes: ST elevation, Q waves, T wave inversion",
                "Risk factors: HTN, DM, smoking, hyperlipidemia, family history"
            ]
        },
        {
            "icd_code": "I50.9",
            "name": "Heart Failure",
            "symptoms": {
                "shortness_of_breath": 0.90,
                "leg_swelling": 0.85,
                "fatigue": 0.80,
                "orthopnea": 0.70,
                "paroxysmal_nocturnal_dyspnea": 0.65,
                "weight_gain": 0.55,
                "cough": 0.45,
                "decreased_exercise_tolerance": 0.75
            },
            "education": [
                "Heart failure is the heart's inability to pump blood effectively",
                "Classified as HFrEF (EF≤40%) or HFpEF (EF≥50%)",
                "Key markers: BNP >100 pg/mL, NT-proBNP >300 pg/mL",
                "NYHA classes I-IV based on functional limitation",
                "First-line treatment: ACEi/ARB, beta-blockers, diuretics"
            ]
        },
        {
            "icd_code": "I10",
            "name": "Essential Hypertension",
            "symptoms": {
                "headache": 0.50,
                "dizziness": 0.45,
                "blurred_vision": 0.35,
                "nosebleeds": 0.25,
                "fatigue": 0.40,
                "chest_pain": 0.20,
                "asymptomatic": 0.60
            },
            "education": [
                "Blood pressure ≥130/80 mmHg defines hypertension (ACC/AHA 2017)",
                "Often called 'silent killer' - usually asymptomatic",
                "Causes: 90-95% essential (primary), 5-10% secondary",
                "Target organs: heart, brain, kidneys, eyes, blood vessels",
                "Lifestyle: DASH diet, exercise, sodium restriction, weight loss"
            ]
        },
        {
            "icd_code": "I48.91",
            "name": "Atrial Fibrillation",
            "symptoms": {
                "palpitations": 0.85,
                "irregular_heartbeat": 0.90,
                "fatigue": 0.65,
                "shortness_of_breath": 0.60,
                "dizziness": 0.50,
                "chest_discomfort": 0.45,
                "exercise_intolerance": 0.55
            },
            "education": [
                "Most common sustained cardiac arrhythmia",
                "ECG: irregularly irregular rhythm, absent P waves",
                "5x increased stroke risk - anticoagulation crucial",
                "CHA2DS2-VASc score guides anticoagulation decisions",
                "Rate vs rhythm control based on symptoms and age"
            ]
        },
        {
            "icd_code": "I25.10",
            "name": "Coronary Artery Disease",
            "symptoms": {
                "chest_pain": 0.80,
                "exertional_angina": 0.85,
                "shortness_of_breath": 0.60,
                "fatigue": 0.55,
                "radiation_to_arm_jaw": 0.50,
                "relieved_by_rest": 0.70,
                "sweating": 0.40
            },
            "education": [
                "Atherosclerotic plaque buildup in coronary arteries",
                "Stable angina: predictable chest pain with exertion",
                "Diagnosis: stress test, coronary CT, angiography",
                "Medical therapy: aspirin, statin, beta-blocker, nitrates",
                "Revascularization: PCI or CABG for significant stenosis"
            ]
        }
    ],
    "neurology": [
        {
            "icd_code": "G43.909",
            "name": "Migraine",
            "symptoms": {
                "severe_headache": 0.95,
                "unilateral_headache": 0.75,
                "throbbing_pain": 0.80,
                "photophobia": 0.70,
                "phonophobia": 0.65,
                "nausea": 0.70,
                "vomiting": 0.50,
                "aura": 0.30
            },
            "education": [
                "Primary headache disorder affecting 12% of population",
                "Phases: prodrome, aura (30%), headache, postdrome",
                "Duration: 4-72 hours if untreated",
                "Triggers: stress, sleep changes, foods, hormones, weather",
                "Acute treatment: NSAIDs, triptans, CGRP antagonists"
            ]
        },
        {
            "icd_code": "I63.9",
            "name": "Ischemic Stroke",
            "symptoms": {
                "sudden_weakness": 0.90,
                "facial_droop": 0.85,
                "arm_weakness": 0.85,
                "speech_difficulty": 0.80,
                "confusion": 0.65,
                "vision_loss": 0.50,
                "severe_headache": 0.40,
                "dizziness": 0.55
            },
            "education": [
                "Brain infarction due to arterial occlusion",
                "Time critical: 'Time is brain' - 1.9M neurons lost per minute",
                "FAST: Face, Arms, Speech, Time to call emergency",
                "tPA window: within 4.5 hours of symptom onset",
                "Thrombectomy: up to 24 hours for large vessel occlusion"
            ]
        },
        {
            "icd_code": "G40.909",
            "name": "Epilepsy",
            "symptoms": {
                "seizures": 0.95,
                "loss_of_consciousness": 0.70,
                "convulsions": 0.65,
                "confusion": 0.60,
                "staring_spells": 0.50,
                "aura": 0.45,
                "post_ictal_state": 0.75,
                "tongue_biting": 0.40
            },
            "education": [
                "Recurrent unprovoked seizures (≥2 or 1 with high recurrence risk)",
                "Types: focal (partial) vs generalized",
                "EEG: epileptiform discharges, MRI for structural cause",
                "First-line AEDs: levetiracetam, lamotrigine, valproate",
                "Driving restrictions vary by state/country"
            ]
        },
        {
            "icd_code": "G20",
            "name": "Parkinson's Disease",
            "symptoms": {
                "tremor": 0.85,
                "bradykinesia": 0.90,
                "rigidity": 0.80,
                "postural_instability": 0.65,
                "shuffling_gait": 0.70,
                "mask_like_face": 0.55,
                "micrographia": 0.50,
                "constipation": 0.60
            },
            "education": [
                "Progressive neurodegenerative disorder - dopamine deficiency",
                "Cardinal features: TRAP (Tremor, Rigidity, Akinesia, Postural instability)",
                "Resting tremor - 'pill-rolling' at 4-6 Hz",
                "Treatment: Levodopa/carbidopa is gold standard",
                "Non-motor: depression, sleep disorders, autonomic dysfunction"
            ]
        },
        {
            "icd_code": "G30.9",
            "name": "Alzheimer's Disease",
            "symptoms": {
                "memory_loss": 0.95,
                "confusion": 0.85,
                "difficulty_with_tasks": 0.80,
                "language_problems": 0.70,
                "disorientation": 0.75,
                "mood_changes": 0.65,
                "personality_changes": 0.60,
                "wandering": 0.50
            },
            "education": [
                "Most common cause of dementia (60-80%)",
                "Pathology: amyloid plaques and neurofibrillary tangles",
                "Diagnosis: clinical + biomarkers (CSF, PET)",
                "Treatment: cholinesterase inhibitors, memantine",
                "New: anti-amyloid therapies (aducanumab, lecanemab)"
            ]
        }
    ],
    "pulmonology": [
        {
            "icd_code": "J45.909",
            "name": "Asthma",
            "symptoms": {
                "wheezing": 0.90,
                "shortness_of_breath": 0.85,
                "cough": 0.80,
                "chest_tightness": 0.75,
                "nocturnal_symptoms": 0.60,
                "exercise_triggered": 0.55,
                "symptom_variability": 0.70
            },
            "education": [
                "Chronic inflammatory airway disease with reversible obstruction",
                "Diagnosis: spirometry showing reversible obstruction (>12% FEV1 improvement)",
                "Controller: inhaled corticosteroids are first-line",
                "Rescue: SABA (albuterol) for acute symptoms",
                "Severity: intermittent, mild/moderate/severe persistent"
            ]
        },
        {
            "icd_code": "J44.9",
            "name": "COPD",
            "symptoms": {
                "chronic_cough": 0.85,
                "dyspnea": 0.90,
                "sputum_production": 0.75,
                "wheezing": 0.65,
                "barrel_chest": 0.40,
                "weight_loss": 0.35,
                "fatigue": 0.60,
                "decreased_breath_sounds": 0.55
            },
            "education": [
                "Chronic bronchitis + emphysema - largely irreversible",
                "Smoking is #1 cause (85-90%)",
                "Spirometry: FEV1/FVC <0.70 post-bronchodilator",
                "GOLD staging I-IV based on FEV1% predicted",
                "Treatment: bronchodilators, ICS for frequent exacerbators"
            ]
        },
        {
            "icd_code": "J18.9",
            "name": "Pneumonia",
            "symptoms": {
                "cough": 0.90,
                "fever": 0.85,
                "dyspnea": 0.75,
                "chest_pain_pleuritic": 0.60,
                "sputum_production": 0.70,
                "fatigue": 0.65,
                "chills": 0.55,
                "crackles_on_auscultation": 0.70
            },
            "education": [
                "Lung infection - bacterial, viral, or atypical organisms",
                "CAP: S. pneumoniae most common typical pathogen",
                "Chest X-ray: infiltrates, consolidation",
                "CURB-65 score guides outpatient vs inpatient treatment",
                "Empiric antibiotics: macrolide or fluoroquinolone for outpatient"
            ]
        },
        {
            "icd_code": "I26.99",
            "name": "Pulmonary Embolism",
            "symptoms": {
                "sudden_dyspnea": 0.90,
                "pleuritic_chest_pain": 0.75,
                "tachycardia": 0.70,
                "cough": 0.45,
                "hemoptysis": 0.30,
                "leg_swelling": 0.50,
                "hypoxia": 0.65,
                "anxiety": 0.40
            },
            "education": [
                "Obstruction of pulmonary artery by thrombus (usually from DVT)",
                "Virchow's triad: stasis, endothelial injury, hypercoagulability",
                "Wells score for clinical probability assessment",
                "D-dimer: high sensitivity, low specificity",
                "CT pulmonary angiography is gold standard"
            ]
        },
        {
            "icd_code": "J84.10",
            "name": "Pulmonary Fibrosis",
            "symptoms": {
                "progressive_dyspnea": 0.95,
                "dry_cough": 0.80,
                "clubbing": 0.50,
                "velcro_crackles": 0.75,
                "fatigue": 0.65,
                "weight_loss": 0.45,
                "exercise_intolerance": 0.70
            },
            "education": [
                "Progressive scarring of lung tissue",
                "IPF: idiopathic form, median survival 3-5 years",
                "HRCT: honeycombing, reticular pattern, traction bronchiectasis",
                "Treatment: pirfenidone, nintedanib slow progression",
                "Lung transplant for eligible candidates"
            ]
        }
    ],
    "gastroenterology": [
        {
            "icd_code": "K21.0",
            "name": "GERD",
            "symptoms": {
                "heartburn": 0.90,
                "regurgitation": 0.80,
                "dysphagia": 0.45,
                "chest_pain": 0.40,
                "chronic_cough": 0.35,
                "hoarseness": 0.30,
                "nausea": 0.35
            },
            "education": [
                "Gastroesophageal reflux causing symptoms or complications",
                "Risk factors: obesity, hiatal hernia, pregnancy",
                "Alarm features: dysphagia, weight loss, GI bleeding",
                "First-line: lifestyle modifications + PPI",
                "EGD if alarm symptoms or refractory to treatment"
            ]
        },
        {
            "icd_code": "K25.9",
            "name": "Peptic Ulcer Disease",
            "symptoms": {
                "epigastric_pain": 0.90,
                "pain_related_to_meals": 0.75,
                "nausea": 0.55,
                "bloating": 0.50,
                "hematemesis": 0.30,
                "melena": 0.35,
                "weight_loss": 0.25
            },
            "education": [
                "Mucosal erosion in stomach or duodenum",
                "Causes: H. pylori (70%), NSAIDs (25%)",
                "Gastric ulcer: pain worse with eating",
                "Duodenal ulcer: pain better with eating, worse at night",
                "Treatment: PPI + H. pylori eradication if positive"
            ]
        },
        {
            "icd_code": "K50.90",
            "name": "Crohn's Disease",
            "symptoms": {
                "abdominal_pain": 0.85,
                "diarrhea": 0.80,
                "weight_loss": 0.65,
                "fatigue": 0.60,
                "bloody_stool": 0.45,
                "perianal_disease": 0.40,
                "fever": 0.35,
                "mouth_ulcers": 0.30
            },
            "education": [
                "Chronic inflammatory bowel disease - transmural inflammation",
                "Can affect any part of GI tract, skip lesions",
                "Complications: strictures, fistulas, abscesses",
                "Treatment: 5-ASA, steroids, immunomodulators, biologics",
                "Surgery for complications, not curative"
            ]
        },
        {
            "icd_code": "K51.90",
            "name": "Ulcerative Colitis",
            "symptoms": {
                "bloody_diarrhea": 0.90,
                "abdominal_pain": 0.70,
                "tenesmus": 0.65,
                "urgency": 0.75,
                "weight_loss": 0.50,
                "fatigue": 0.55,
                "fever": 0.30
            },
            "education": [
                "Chronic IBD - mucosal inflammation of colon/rectum",
                "Always involves rectum, extends proximally continuously",
                "Severity: mild (<4 stools/day) to severe (>6 + systemic)",
                "Treatment: 5-ASA, steroids, biologics (anti-TNF, vedolizumab)",
                "Colectomy is curative but permanent"
            ]
        },
        {
            "icd_code": "K74.60",
            "name": "Cirrhosis",
            "symptoms": {
                "fatigue": 0.80,
                "jaundice": 0.70,
                "ascites": 0.65,
                "spider_angiomata": 0.50,
                "palmar_erythema": 0.45,
                "easy_bruising": 0.55,
                "confusion": 0.40,
                "edema": 0.60
            },
            "education": [
                "End-stage liver fibrosis - irreversible",
                "Causes: alcohol, viral hepatitis, NAFLD, autoimmune",
                "Complications: varices, ascites, HE, HCC, coagulopathy",
                "Child-Pugh and MELD scores for prognosis",
                "Liver transplant for decompensated cirrhosis"
            ]
        }
    ],
    "endocrinology": [
        {
            "icd_code": "E11.9",
            "name": "Type 2 Diabetes Mellitus",
            "symptoms": {
                "polyuria": 0.75,
                "polydipsia": 0.70,
                "fatigue": 0.65,
                "blurred_vision": 0.50,
                "weight_loss": 0.40,
                "slow_wound_healing": 0.45,
                "recurrent_infections": 0.40,
                "numbness_tingling": 0.35
            },
            "education": [
                "Insulin resistance + relative insulin deficiency",
                "Diagnosis: FPG ≥126, 2hr OGTT ≥200, A1C ≥6.5%",
                "First-line: metformin + lifestyle modification",
                "Microvascular: retinopathy, nephropathy, neuropathy",
                "A1C goal <7% for most adults"
            ]
        },
        {
            "icd_code": "E05.90",
            "name": "Hyperthyroidism",
            "symptoms": {
                "weight_loss": 0.80,
                "heat_intolerance": 0.75,
                "palpitations": 0.70,
                "tremor": 0.65,
                "anxiety": 0.60,
                "diarrhea": 0.45,
                "menstrual_irregularity": 0.50,
                "exophthalmos": 0.40
            },
            "education": [
                "Excess thyroid hormone production",
                "Graves' disease most common cause (80%)",
                "TSH low, T4/T3 elevated",
                "Treatment: antithyroid drugs, RAI, surgery",
                "Thyroid storm is medical emergency"
            ]
        },
        {
            "icd_code": "E03.9",
            "name": "Hypothyroidism",
            "symptoms": {
                "fatigue": 0.85,
                "weight_gain": 0.75,
                "cold_intolerance": 0.70,
                "constipation": 0.60,
                "dry_skin": 0.65,
                "depression": 0.50,
                "bradycardia": 0.45,
                "menstrual_irregularity": 0.40
            },
            "education": [
                "Insufficient thyroid hormone production",
                "Hashimoto's thyroiditis most common cause",
                "TSH elevated, T4 low",
                "Treatment: levothyroxine replacement",
                "Goal: TSH in normal range (0.4-4.0 mU/L)"
            ]
        },
        {
            "icd_code": "E24.9",
            "name": "Cushing's Syndrome",
            "symptoms": {
                "weight_gain_central": 0.85,
                "moon_face": 0.75,
                "buffalo_hump": 0.65,
                "purple_striae": 0.70,
                "easy_bruising": 0.60,
                "hypertension": 0.55,
                "muscle_weakness": 0.50,
                "diabetes": 0.45
            },
            "education": [
                "Excess cortisol - exogenous (steroids) or endogenous",
                "Endogenous: pituitary adenoma (Cushing's disease) or adrenal tumor",
                "Screening: 24hr urine cortisol, overnight dexamethasone suppression",
                "ACTH level differentiates ACTH-dependent vs independent",
                "Treatment: address underlying cause"
            ]
        },
        {
            "icd_code": "E27.1",
            "name": "Addison's Disease",
            "symptoms": {
                "fatigue": 0.90,
                "weight_loss": 0.75,
                "hyperpigmentation": 0.70,
                "hypotension": 0.65,
                "salt_craving": 0.55,
                "nausea": 0.50,
                "muscle_weakness": 0.60,
                "abdominal_pain": 0.40
            },
            "education": [
                "Primary adrenal insufficiency - destruction of adrenal cortex",
                "Causes: autoimmune (70%), TB, adrenal hemorrhage",
                "Low cortisol + high ACTH",
                "ACTH stimulation test: cortisol fails to rise",
                "Lifelong glucocorticoid + mineralocorticoid replacement"
            ]
        }
    ],
    "nephrology": [
        {
            "icd_code": "N18.9",
            "name": "Chronic Kidney Disease",
            "symptoms": {
                "fatigue": 0.80,
                "edema": 0.70,
                "nausea": 0.55,
                "decreased_urine_output": 0.50,
                "itching": 0.45,
                "shortness_of_breath": 0.40,
                "hypertension": 0.65,
                "anemia_symptoms": 0.50
            },
            "education": [
                "Progressive loss of kidney function over months/years",
                "Stages 1-5 based on GFR (G1: >90, G5: <15 mL/min)",
                "Causes: DM, HTN, glomerulonephritis",
                "Complications: anemia, bone disease, hyperkalemia, acidosis",
                "Stage 5: dialysis or transplant required"
            ]
        },
        {
            "icd_code": "N17.9",
            "name": "Acute Kidney Injury",
            "symptoms": {
                "decreased_urine_output": 0.85,
                "edema": 0.70,
                "fatigue": 0.65,
                "confusion": 0.45,
                "nausea": 0.55,
                "shortness_of_breath": 0.50,
                "chest_pain": 0.30
            },
            "education": [
                "Rapid decline in kidney function over hours to days",
                "KDIGO criteria: Cr rise >0.3 mg/dL in 48h or >1.5x baseline",
                "Pre-renal (most common), intrinsic, post-renal",
                "FENa <1% suggests pre-renal, >2% intrinsic",
                "Treatment: address underlying cause, supportive care"
            ]
        },
        {
            "icd_code": "N10",
            "name": "Pyelonephritis",
            "symptoms": {
                "fever": 0.90,
                "flank_pain": 0.85,
                "dysuria": 0.70,
                "frequency": 0.65,
                "nausea": 0.60,
                "vomiting": 0.50,
                "costovertebral_angle_tenderness": 0.80
            },
            "education": [
                "Upper urinary tract infection - kidney parenchyma",
                "Usually ascending from lower UTI",
                "E. coli most common pathogen (80%)",
                "UA: pyuria, bacteriuria, WBC casts",
                "Treatment: fluoroquinolone or ceftriaxone, 7-14 days"
            ]
        },
        {
            "icd_code": "N04.9",
            "name": "Nephrotic Syndrome",
            "symptoms": {
                "edema": 0.95,
                "foamy_urine": 0.75,
                "weight_gain": 0.65,
                "fatigue": 0.55,
                "anorexia": 0.40,
                "periorbital_edema": 0.70
            },
            "education": [
                "Proteinuria >3.5g/day, hypoalbuminemia, edema, hyperlipidemia",
                "Causes: minimal change, FSGS, membranous, diabetic",
                "Complications: thromboembolism, infection, AKI",
                "Treatment depends on underlying cause",
                "ACEi/ARB for proteinuria reduction"
            ]
        },
        {
            "icd_code": "N20.0",
            "name": "Nephrolithiasis",
            "symptoms": {
                "flank_pain": 0.95,
                "colicky_pain": 0.85,
                "hematuria": 0.75,
                "nausea": 0.65,
                "vomiting": 0.55,
                "dysuria": 0.45,
                "urinary_urgency": 0.40
            },
            "education": [
                "Kidney stones - calcium oxalate most common (80%)",
                "Risk factors: dehydration, high sodium, hyperparathyroidism",
                "CT non-contrast is gold standard imaging",
                "Small stones (<5mm) usually pass spontaneously",
                "Intervention: ESWL, ureteroscopy, PCNL for larger stones"
            ]
        }
    ],
    "rheumatology": [
        {
            "icd_code": "M06.9",
            "name": "Rheumatoid Arthritis",
            "symptoms": {
                "joint_pain": 0.95,
                "morning_stiffness": 0.85,
                "symmetric_arthritis": 0.80,
                "joint_swelling": 0.85,
                "fatigue": 0.65,
                "rheumatoid_nodules": 0.35,
                "hand_involvement": 0.75
            },
            "education": [
                "Chronic autoimmune inflammatory arthritis",
                "Affects small joints of hands/feet symmetrically",
                "Labs: RF, anti-CCP antibodies, elevated ESR/CRP",
                "Treatment goal: remission, prevent joint destruction",
                "DMARDs: methotrexate first-line, biologics if refractory"
            ]
        },
        {
            "icd_code": "M32.9",
            "name": "Systemic Lupus Erythematosus",
            "symptoms": {
                "fatigue": 0.90,
                "joint_pain": 0.85,
                "malar_rash": 0.70,
                "photosensitivity": 0.60,
                "oral_ulcers": 0.45,
                "serositis": 0.40,
                "renal_involvement": 0.50,
                "fever": 0.55
            },
            "education": [
                "Multisystem autoimmune disease, 9:1 female predominance",
                "Diagnosis: SLICC criteria (≥4 of 11)",
                "Labs: ANA (sensitive), anti-dsDNA/anti-Smith (specific)",
                "Lupus nephritis: major cause of morbidity",
                "Treatment: hydroxychloroquine for all, steroids/immunosuppressants for flares"
            ]
        },
        {
            "icd_code": "M10.9",
            "name": "Gout",
            "symptoms": {
                "acute_joint_pain": 0.95,
                "joint_swelling": 0.90,
                "redness": 0.85,
                "warmth": 0.80,
                "first_mtp_involvement": 0.75,
                "tophi": 0.35,
                "fever": 0.40
            },
            "education": [
                "Crystal arthropathy - monosodium urate deposition",
                "Risk factors: hyperuricemia, alcohol, red meat, diuretics",
                "Diagnosis: negatively birefringent crystals on joint aspiration",
                "Acute: NSAIDs, colchicine, or steroids",
                "Prophylaxis: allopurinol, febuxostat (target uric acid <6)"
            ]
        },
        {
            "icd_code": "M34.9",
            "name": "Systemic Sclerosis",
            "symptoms": {
                "skin_thickening": 0.95,
                "raynauds_phenomenon": 0.90,
                "digital_ulcers": 0.55,
                "dysphagia": 0.60,
                "dyspnea": 0.50,
                "heartburn": 0.65,
                "sclerodactyly": 0.75
            },
            "education": [
                "Autoimmune connective tissue disease with fibrosis",
                "Limited (CREST) vs diffuse cutaneous forms",
                "Antibodies: anti-centromere (limited), anti-Scl-70 (diffuse)",
                "Complications: ILD, pulmonary HTN, renal crisis",
                "Treatment: organ-specific, immunosuppression for ILD"
            ]
        },
        {
            "icd_code": "M35.3",
            "name": "Polymyalgia Rheumatica",
            "symptoms": {
                "shoulder_stiffness": 0.95,
                "hip_stiffness": 0.85,
                "morning_stiffness": 0.90,
                "fatigue": 0.70,
                "low_grade_fever": 0.40,
                "weight_loss": 0.35,
                "elevated_esr": 0.85
            },
            "education": [
                "Inflammatory disorder in patients >50 years",
                "Bilateral shoulder/hip girdle pain and stiffness",
                "ESR/CRP markedly elevated",
                "15% associated with giant cell arteritis",
                "Dramatic response to low-dose prednisone (15-20mg)"
            ]
        }
    ],
    "infectious_disease": [
        {
            "icd_code": "A41.9",
            "name": "Sepsis",
            "symptoms": {
                "fever": 0.85,
                "tachycardia": 0.80,
                "tachypnea": 0.75,
                "hypotension": 0.70,
                "confusion": 0.60,
                "chills": 0.65,
                "decreased_urine_output": 0.50,
                "mottled_skin": 0.45
            },
            "education": [
                "Life-threatening organ dysfunction due to infection",
                "qSOFA: RR≥22, altered mentation, SBP≤100",
                "SOFA score for organ dysfunction assessment",
                "Hour-1 bundle: cultures, lactate, antibiotics, fluids",
                "Mortality increases 8% for each hour antibiotic delay"
            ]
        },
        {
            "icd_code": "B20",
            "name": "HIV/AIDS",
            "symptoms": {
                "fatigue": 0.80,
                "weight_loss": 0.75,
                "fever": 0.65,
                "night_sweats": 0.60,
                "lymphadenopathy": 0.70,
                "opportunistic_infections": 0.55,
                "oral_thrush": 0.50,
                "diarrhea": 0.45
            },
            "education": [
                "Retrovirus attacking CD4+ T cells",
                "AIDS: CD4 <200 or AIDS-defining illness",
                "Diagnosis: HIV Ab/Ag test, confirm with HIV RNA",
                "ART: 2 NRTIs + integrase inhibitor (first-line)",
                "Goal: undetectable viral load, U=U"
            ]
        },
        {
            "icd_code": "A15.0",
            "name": "Tuberculosis",
            "symptoms": {
                "chronic_cough": 0.90,
                "hemoptysis": 0.55,
                "night_sweats": 0.75,
                "weight_loss": 0.70,
                "fever": 0.65,
                "fatigue": 0.60,
                "lymphadenopathy": 0.45
            },
            "education": [
                "Mycobacterium tuberculosis - primarily pulmonary",
                "Screening: TST or IGRA",
                "Diagnosis: sputum AFB smear/culture, nucleic acid amplification",
                "Active TB: 4-drug RIPE regimen (6-9 months)",
                "Latent TB: INH 9 months or rifampin 4 months"
            ]
        },
        {
            "icd_code": "B02.9",
            "name": "Herpes Zoster",
            "symptoms": {
                "dermatomal_pain": 0.95,
                "vesicular_rash": 0.90,
                "burning_sensation": 0.80,
                "itching": 0.65,
                "fever": 0.40,
                "headache": 0.35,
                "fatigue": 0.50
            },
            "education": [
                "Reactivation of varicella-zoster virus",
                "Risk: age >50, immunocompromised",
                "Unilateral, dermatomal vesicular rash",
                "Complications: PHN, herpes zoster ophthalmicus",
                "Treatment: acyclovir/valacyclovir within 72 hours"
            ]
        },
        {
            "icd_code": "A09",
            "name": "Infectious Gastroenteritis",
            "symptoms": {
                "diarrhea": 0.95,
                "nausea": 0.80,
                "vomiting": 0.75,
                "abdominal_cramps": 0.85,
                "fever": 0.55,
                "dehydration": 0.60,
                "bloody_stool": 0.30
            },
            "education": [
                "Infection of GI tract - viral, bacterial, parasitic",
                "Viral: norovirus, rotavirus most common",
                "Bacterial: Salmonella, Campylobacter, E. coli",
                "Most cases self-limited, supportive care",
                "Antibiotics for severe bacterial gastroenteritis"
            ]
        }
    ],
    "dermatology": [
        {
            "icd_code": "L40.9",
            "name": "Psoriasis",
            "symptoms": {
                "scaly_plaques": 0.95,
                "silvery_scales": 0.85,
                "erythematous_patches": 0.80,
                "itching": 0.65,
                "nail_changes": 0.50,
                "scalp_involvement": 0.60,
                "joint_pain": 0.30
            },
            "education": [
                "Chronic autoimmune skin disease",
                "Plaque psoriasis most common (90%)",
                "Auspitz sign: pinpoint bleeding with scale removal",
                "Psoriatic arthritis in 30%",
                "Treatment: topicals, phototherapy, systemic, biologics"
            ]
        },
        {
            "icd_code": "L20.9",
            "name": "Atopic Dermatitis",
            "symptoms": {
                "itching": 0.95,
                "dry_skin": 0.90,
                "eczematous_patches": 0.85,
                "flexural_involvement": 0.70,
                "lichenification": 0.55,
                "erythema": 0.75,
                "vesicles": 0.40
            },
            "education": [
                "Chronic inflammatory skin disease, part of atopic triad",
                "Peak onset: infancy and early childhood",
                "Distribution varies with age (face in infants, flexures in children)",
                "Treatment: emollients, topical steroids, calcineurin inhibitors",
                "Dupilumab for moderate-severe disease"
            ]
        },
        {
            "icd_code": "L50.9",
            "name": "Urticaria",
            "symptoms": {
                "hives": 0.95,
                "itching": 0.90,
                "wheals": 0.85,
                "angioedema": 0.45,
                "transient_lesions": 0.80,
                "dermatographism": 0.50
            },
            "education": [
                "Mast cell-mediated skin reaction",
                "Acute (<6 weeks) vs chronic (>6 weeks)",
                "Acute: often allergic; chronic: usually idiopathic",
                "Individual wheals last <24 hours",
                "Treatment: antihistamines, omalizumab for chronic"
            ]
        },
        {
            "icd_code": "L70.0",
            "name": "Acne Vulgaris",
            "symptoms": {
                "comedones": 0.90,
                "papules": 0.85,
                "pustules": 0.80,
                "nodules": 0.50,
                "cysts": 0.40,
                "facial_involvement": 0.95,
                "scarring": 0.35
            },
            "education": [
                "Chronic inflammation of pilosebaceous units",
                "Pathogenesis: sebum, follicular hyperkeratinization, C. acnes, inflammation",
                "Mild: topical retinoid + benzoyl peroxide",
                "Moderate: add topical or oral antibiotics",
                "Severe: isotretinoin (iPLEDGE program required)"
            ]
        },
        {
            "icd_code": "C43.9",
            "name": "Melanoma",
            "symptoms": {
                "asymmetric_mole": 0.80,
                "irregular_borders": 0.75,
                "color_variation": 0.80,
                "diameter_over_6mm": 0.65,
                "evolving_lesion": 0.85,
                "bleeding": 0.40,
                "itching": 0.35
            },
            "education": [
                "Most lethal skin cancer - from melanocytes",
                "ABCDE criteria for suspicious lesions",
                "Risk factors: UV exposure, fair skin, family history, dysplastic nevi",
                "Staging: Breslow depth is key prognostic factor",
                "Treatment: excision, immunotherapy, targeted therapy"
            ]
        }
    ],
    "psychiatry": [
        {
            "icd_code": "F32.9",
            "name": "Major Depressive Disorder",
            "symptoms": {
                "depressed_mood": 0.95,
                "anhedonia": 0.85,
                "sleep_disturbance": 0.75,
                "appetite_changes": 0.65,
                "fatigue": 0.80,
                "worthlessness": 0.70,
                "concentration_difficulty": 0.65,
                "suicidal_ideation": 0.45
            },
            "education": [
                "≥5 symptoms for ≥2 weeks including depressed mood or anhedonia",
                "SIG E CAPS mnemonic for symptoms",
                "Screen for bipolar before starting antidepressants",
                "First-line: SSRI or SNRI",
                "Therapy: CBT, interpersonal therapy effective"
            ]
        },
        {
            "icd_code": "F41.1",
            "name": "Generalized Anxiety Disorder",
            "symptoms": {
                "excessive_worry": 0.95,
                "restlessness": 0.80,
                "fatigue": 0.70,
                "concentration_difficulty": 0.65,
                "muscle_tension": 0.75,
                "sleep_disturbance": 0.70,
                "irritability": 0.60
            },
            "education": [
                "Excessive anxiety/worry more days than not for ≥6 months",
                "Difficult to control worry + ≥3 somatic symptoms",
                "Rule out medical causes: hyperthyroidism, substances",
                "Treatment: CBT, SSRI/SNRI first-line pharmacotherapy",
                "Benzodiazepines for short-term, avoid long-term use"
            ]
        },
        {
            "icd_code": "F31.9",
            "name": "Bipolar Disorder",
            "symptoms": {
                "mood_swings": 0.90,
                "manic_episodes": 0.95,
                "depressive_episodes": 0.85,
                "decreased_sleep_need": 0.80,
                "grandiosity": 0.70,
                "racing_thoughts": 0.75,
                "increased_activity": 0.80,
                "risky_behavior": 0.60
            },
            "education": [
                "Bipolar I: ≥1 manic episode; Bipolar II: hypomania + depression",
                "Mania: DIGFAST (Distractibility, Insomnia, Grandiosity, Flight of ideas, Activity, Speech, Thoughtlessness)",
                "Mood stabilizers: lithium, valproate, lamotrigine",
                "Atypical antipsychotics for acute mania",
                "Avoid antidepressant monotherapy (can trigger mania)"
            ]
        },
        {
            "icd_code": "F20.9",
            "name": "Schizophrenia",
            "symptoms": {
                "hallucinations": 0.85,
                "delusions": 0.85,
                "disorganized_speech": 0.70,
                "disorganized_behavior": 0.65,
                "negative_symptoms": 0.75,
                "social_withdrawal": 0.70,
                "flat_affect": 0.60
            },
            "education": [
                "≥2 symptoms for ≥1 month, continuous disturbance ≥6 months",
                "Positive symptoms: hallucinations, delusions",
                "Negative symptoms: flat affect, avolition, alogia",
                "First-line: second-generation antipsychotics",
                "Clozapine for treatment-resistant cases"
            ]
        },
        {
            "icd_code": "F43.10",
            "name": "PTSD",
            "symptoms": {
                "intrusive_memories": 0.90,
                "flashbacks": 0.80,
                "nightmares": 0.75,
                "avoidance": 0.85,
                "hypervigilance": 0.80,
                "negative_mood": 0.70,
                "exaggerated_startle": 0.65,
                "sleep_disturbance": 0.70
            },
            "education": [
                "Develops after exposure to traumatic event",
                "Symptom clusters: intrusion, avoidance, negative cognitions, arousal",
                "Duration >1 month (acute stress disorder if <1 month)",
                "First-line: trauma-focused CBT, EMDR",
                "Pharmacotherapy: sertraline, paroxetine FDA-approved"
            ]
        }
    ]
}

# ============ QUESTION BANK ============
SYMPTOM_QUESTIONS = {
    "chest_pain": "Does the patient have chest pain?",
    "radiating_arm_pain": "Does the pain radiate to the arm, jaw, or neck?",
    "shortness_of_breath": "Does the patient experience shortness of breath?",
    "sweating": "Is there excessive sweating (diaphoresis)?",
    "nausea": "Does the patient have nausea?",
    "jaw_pain": "Is there jaw pain or discomfort?",
    "fatigue": "Does the patient report fatigue or tiredness?",
    "palpitations": "Does the patient feel palpitations or irregular heartbeat?",
    "leg_swelling": "Is there leg or ankle swelling (edema)?",
    "orthopnea": "Does the patient have difficulty breathing when lying flat?",
    "paroxysmal_nocturnal_dyspnea": "Does the patient wake up at night gasping for air?",
    "weight_gain": "Has there been recent unexplained weight gain?",
    "cough": "Does the patient have a cough?",
    "decreased_exercise_tolerance": "Has exercise tolerance decreased?",
    "headache": "Does the patient have headaches?",
    "dizziness": "Does the patient experience dizziness or lightheadedness?",
    "blurred_vision": "Is there any blurred vision?",
    "nosebleeds": "Does the patient have nosebleeds?",
    "asymptomatic": "Is the patient essentially without symptoms?",
    "irregular_heartbeat": "Is the heartbeat irregular?",
    "chest_discomfort": "Is there any chest discomfort or pressure?",
    "exercise_intolerance": "Is there exercise intolerance?",
    "exertional_angina": "Does the patient have chest pain with exertion?",
    "radiation_to_arm_jaw": "Does the pain radiate to arm or jaw?",
    "relieved_by_rest": "Is the chest pain relieved by rest?",
    "severe_headache": "Is the headache severe or the 'worst ever'?",
    "unilateral_headache": "Is the headache on one side only?",
    "throbbing_pain": "Is the pain throbbing or pulsating?",
    "photophobia": "Is there sensitivity to light?",
    "phonophobia": "Is there sensitivity to sound?",
    "vomiting": "Does the patient have vomiting?",
    "aura": "Does the patient experience visual or sensory aura before symptoms?",
    "sudden_weakness": "Is there sudden weakness, especially on one side?",
    "facial_droop": "Is there facial drooping?",
    "arm_weakness": "Is there arm weakness or difficulty lifting?",
    "speech_difficulty": "Does the patient have difficulty speaking?",
    "confusion": "Is the patient confused or disoriented?",
    "vision_loss": "Is there any vision loss?",
    "seizures": "Has the patient had seizures?",
    "loss_of_consciousness": "Has there been loss of consciousness?",
    "convulsions": "Does the patient have convulsions?",
    "staring_spells": "Does the patient have staring spells?",
    "post_ictal_state": "Is there a confused state after episodes?",
    "tongue_biting": "Is there evidence of tongue biting?",
    "tremor": "Does the patient have tremor?",
    "bradykinesia": "Is there slowness of movement?",
    "rigidity": "Is there muscle rigidity?",
    "postural_instability": "Does the patient have balance problems?",
    "shuffling_gait": "Does the patient have a shuffling walk?",
    "mask_like_face": "Is there reduced facial expression?",
    "micrographia": "Has handwriting become smaller?",
    "constipation": "Does the patient have constipation?",
    "memory_loss": "Is there memory loss?",
    "difficulty_with_tasks": "Is there difficulty with familiar tasks?",
    "language_problems": "Are there language or word-finding difficulties?",
    "disorientation": "Is there disorientation to time or place?",
    "mood_changes": "Are there mood changes?",
    "personality_changes": "Are there personality changes?",
    "wandering": "Does the patient wander or get lost?",
    "wheezing": "Does the patient have wheezing?",
    "chest_tightness": "Is there chest tightness?",
    "nocturnal_symptoms": "Are symptoms worse at night?",
    "exercise_triggered": "Are symptoms triggered by exercise?",
    "symptom_variability": "Do symptoms vary in intensity?",
    "chronic_cough": "Is there a chronic cough (>3 weeks)?",
    "dyspnea": "Does the patient have difficulty breathing?",
    "sputum_production": "Is there sputum production?",
    "barrel_chest": "Is there a barrel-shaped chest?",
    "weight_loss": "Has there been unexplained weight loss?",
    "decreased_breath_sounds": "Are breath sounds decreased?",
    "fever": "Does the patient have fever?",
    "chest_pain_pleuritic": "Is the chest pain worse with breathing?",
    "chills": "Does the patient have chills?",
    "crackles_on_auscultation": "Are there crackles heard on lung exam?",
    "sudden_dyspnea": "Was the shortness of breath sudden in onset?",
    "pleuritic_chest_pain": "Is there sharp chest pain worse with breathing?",
    "tachycardia": "Is the heart rate elevated?",
    "hemoptysis": "Is the patient coughing up blood?",
    "hypoxia": "Is oxygen saturation low?",
    "anxiety": "Does the patient have anxiety?",
    "progressive_dyspnea": "Has shortness of breath been progressively worsening?",
    "dry_cough": "Is the cough dry (non-productive)?",
    "clubbing": "Is there finger clubbing?",
    "velcro_crackles": "Are there 'velcro-like' crackles on exam?",
    "heartburn": "Does the patient have heartburn?",
    "regurgitation": "Is there regurgitation of food or acid?",
    "dysphagia": "Is there difficulty swallowing?",
    "hoarseness": "Is there hoarseness or voice changes?",
    "epigastric_pain": "Is there pain in the upper abdomen?",
    "pain_related_to_meals": "Is the pain related to eating?",
    "bloating": "Is there bloating or abdominal distension?",
    "hematemesis": "Is the patient vomiting blood?",
    "melena": "Are stools black and tarry?",
    "abdominal_pain": "Does the patient have abdominal pain?",
    "diarrhea": "Does the patient have diarrhea?",
    "bloody_stool": "Is there blood in the stool?",
    "perianal_disease": "Is there perianal disease (fistulas, abscess)?",
    "mouth_ulcers": "Are there mouth ulcers?",
    "tenesmus": "Is there a sensation of incomplete evacuation?",
    "urgency": "Is there urgency to defecate?",
    "bloody_diarrhea": "Is the diarrhea bloody?",
    "jaundice": "Is there yellowing of skin or eyes?",
    "ascites": "Is there fluid in the abdomen?",
    "spider_angiomata": "Are there spider-like blood vessels on skin?",
    "palmar_erythema": "Are the palms red?",
    "easy_bruising": "Is there easy bruising?",
    "edema": "Is there swelling (edema)?",
    "polyuria": "Is there excessive urination?",
    "polydipsia": "Is there excessive thirst?",
    "slow_wound_healing": "Do wounds heal slowly?",
    "recurrent_infections": "Are there frequent infections?",
    "numbness_tingling": "Is there numbness or tingling?",
    "heat_intolerance": "Is there heat intolerance?",
    "cold_intolerance": "Is there cold intolerance?",
    "dry_skin": "Is the skin dry?",
    "depression": "Is there depression?",
    "bradycardia": "Is the heart rate slow?",
    "menstrual_irregularity": "Are there menstrual irregularities?",
    "exophthalmos": "Are the eyes bulging?",
    "weight_gain_central": "Is weight gain central (trunk)?",
    "moon_face": "Is there a round, moon-shaped face?",
    "buffalo_hump": "Is there fat accumulation at the upper back?",
    "purple_striae": "Are there purple stretch marks?",
    "hypertension": "Does the patient have high blood pressure?",
    "muscle_weakness": "Is there muscle weakness?",
    "diabetes": "Does the patient have diabetes or high blood sugar?",
    "hyperpigmentation": "Is there darkening of the skin?",
    "hypotension": "Is blood pressure low?",
    "salt_craving": "Is there salt craving?",
    "decreased_urine_output": "Is urine output decreased?",
    "itching": "Is there itching (pruritus)?",
    "anemia_symptoms": "Are there signs of anemia (pale, tired)?",
    "flank_pain": "Is there pain in the side/back (flank)?",
    "dysuria": "Is there pain with urination?",
    "frequency": "Is urination more frequent?",
    "costovertebral_angle_tenderness": "Is there tenderness at the kidney area?",
    "foamy_urine": "Is the urine foamy?",
    "anorexia": "Is there loss of appetite?",
    "periorbital_edema": "Is there swelling around the eyes?",
    "colicky_pain": "Is the pain coming in waves (colicky)?",
    "hematuria": "Is there blood in the urine?",
    "urinary_urgency": "Is there urinary urgency?",
    "joint_pain": "Does the patient have joint pain?",
    "morning_stiffness": "Is there morning stiffness?",
    "symmetric_arthritis": "Is joint involvement symmetric?",
    "joint_swelling": "Is there joint swelling?",
    "rheumatoid_nodules": "Are there nodules under the skin?",
    "hand_involvement": "Are the hands/fingers affected?",
    "malar_rash": "Is there a butterfly-shaped rash on the face?",
    "photosensitivity": "Is there sun sensitivity?",
    "oral_ulcers": "Are there mouth or nose sores?",
    "serositis": "Is there chest or abdominal pain from inflammation?",
    "renal_involvement": "Is there kidney involvement?",
    "acute_joint_pain": "Is the joint pain sudden and severe?",
    "redness": "Is there redness at the affected area?",
    "warmth": "Is the affected area warm to touch?",
    "first_mtp_involvement": "Is the big toe affected?",
    "tophi": "Are there hard deposits under the skin?",
    "skin_thickening": "Is the skin thickening?",
    "raynauds_phenomenon": "Do fingers turn white/blue in cold?",
    "digital_ulcers": "Are there ulcers on fingers?",
    "sclerodactyly": "Are fingers becoming stiff and tight?",
    "shoulder_stiffness": "Is there shoulder stiffness?",
    "hip_stiffness": "Is there hip stiffness?",
    "low_grade_fever": "Is there a low-grade fever?",
    "elevated_esr": "Is the ESR elevated?",
    "tachypnea": "Is breathing rapid?",
    "mottled_skin": "Is the skin mottled?",
    "night_sweats": "Are there night sweats?",
    "lymphadenopathy": "Are lymph nodes enlarged?",
    "opportunistic_infections": "Are there unusual infections?",
    "oral_thrush": "Is there white coating in the mouth?",
    "dermatomal_pain": "Is pain following a nerve pattern?",
    "vesicular_rash": "Is there a blistering rash?",
    "burning_sensation": "Is there burning pain?",
    "abdominal_cramps": "Are there abdominal cramps?",
    "dehydration": "Is there dehydration?",
    "scaly_plaques": "Are there scaly skin plaques?",
    "silvery_scales": "Are the scales silvery?",
    "erythematous_patches": "Are there red patches?",
    "nail_changes": "Are there nail changes?",
    "scalp_involvement": "Is the scalp affected?",
    "eczematous_patches": "Are there eczema-like patches?",
    "flexural_involvement": "Are skin folds affected?",
    "lichenification": "Is skin thickened from scratching?",
    "erythema": "Is there skin redness?",
    "vesicles": "Are there small blisters?",
    "hives": "Are there hives (raised itchy welts)?",
    "wheals": "Are there wheals?",
    "angioedema": "Is there swelling of lips/face/throat?",
    "transient_lesions": "Do lesions come and go quickly?",
    "dermatographism": "Does skin welt when scratched?",
    "comedones": "Are there blackheads/whiteheads?",
    "papules": "Are there small raised bumps?",
    "pustules": "Are there pus-filled bumps?",
    "nodules": "Are there deep painful lumps?",
    "cysts": "Are there cysts?",
    "facial_involvement": "Is the face affected?",
    "scarring": "Is there scarring?",
    "asymmetric_mole": "Is a mole asymmetric?",
    "irregular_borders": "Does a mole have irregular borders?",
    "color_variation": "Does a mole have multiple colors?",
    "diameter_over_6mm": "Is a mole larger than 6mm?",
    "evolving_lesion": "Has a skin lesion been changing?",
    "bleeding": "Is there bleeding?",
    "depressed_mood": "Is there persistent sad mood?",
    "anhedonia": "Is there loss of interest in activities?",
    "sleep_disturbance": "Is there sleep disturbance?",
    "appetite_changes": "Are there appetite changes?",
    "worthlessness": "Are there feelings of worthlessness?",
    "concentration_difficulty": "Is there difficulty concentrating?",
    "suicidal_ideation": "Are there thoughts of self-harm or suicide?",
    "excessive_worry": "Is there excessive worry?",
    "restlessness": "Is there restlessness?",
    "muscle_tension": "Is there muscle tension?",
    "irritability": "Is there irritability?",
    "mood_swings": "Are there mood swings?",
    "manic_episodes": "Are there episodes of elevated mood/energy?",
    "depressive_episodes": "Are there episodes of depression?",
    "decreased_sleep_need": "Is less sleep needed than usual?",
    "grandiosity": "Is there inflated self-esteem?",
    "racing_thoughts": "Are thoughts racing?",
    "increased_activity": "Is there increased activity or energy?",
    "risky_behavior": "Is there risky behavior?",
    "hallucinations": "Are there hallucinations?",
    "delusions": "Are there delusions (false beliefs)?",
    "disorganized_speech": "Is speech disorganized?",
    "disorganized_behavior": "Is behavior disorganized?",
    "negative_symptoms": "Is there flat affect or decreased motivation?",
    "social_withdrawal": "Is there social withdrawal?",
    "flat_affect": "Is there flat or blunted emotion?",
    "intrusive_memories": "Are there intrusive memories of trauma?",
    "flashbacks": "Are there flashbacks?",
    "nightmares": "Are there nightmares?",
    "avoidance": "Is there avoidance of reminders?",
    "hypervigilance": "Is there hypervigilance?",
    "negative_mood": "Is there persistent negative mood?",
    "exaggerated_startle": "Is there exaggerated startle response?"
}

# ============ AUTH HELPERS ============
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request) -> Optional[Dict]:
    # Check cookie first
    session_token = request.cookies.get("session_token")
    
    # Then check Authorization header
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        return None
    
    # Check for JWT token
    try:
        payload = jwt.decode(session_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0})
        return user
    except jwt.ExpiredSignatureError:
        pass
    except jwt.InvalidTokenError:
        pass
    
    # Check for Google OAuth session
    session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if session:
        expires_at = session.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at > datetime.now(timezone.utc):
            user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
            return user
    
    return None

# ============ GAME LOGIC ============
def calculate_question_importance(diseases: List[Dict], symptom: str) -> float:
    """Calculate how much a symptom differentiates between remaining diseases"""
    probabilities = [d["symptoms"].get(symptom, 0) for d in diseases]
    if not probabilities:
        return 0
    avg = sum(probabilities) / len(probabilities)
    variance = sum((p - avg) ** 2 for p in probabilities) / len(probabilities)
    return variance * avg  # Prefer symptoms that are common but vary between diseases

def select_next_question(diseases: List[Dict], asked_symptoms: List[str]) -> Optional[str]:
    """Select the most discriminating symptom to ask about"""
    all_symptoms = set()
    for disease in diseases:
        all_symptoms.update(disease["symptoms"].keys())
    
    remaining_symptoms = all_symptoms - set(asked_symptoms)
    if not remaining_symptoms:
        return None
    
    best_symptom = max(remaining_symptoms, key=lambda s: calculate_question_importance(diseases, s))
    return best_symptom

def update_disease_probabilities(diseases: List[Dict], symptom: str, answer: str) -> List[Dict]:
    """Update disease probabilities based on answer"""
    multipliers = {
        "yes": lambda p: p * 1.5,
        "no": lambda p: (1 - p) * 1.2,
        "maybe": lambda p: p * 1.1,
        "dont_know": lambda p: p
    }
    
    multiplier = multipliers.get(answer, lambda p: p)
    
    for disease in diseases:
        base_prob = disease["symptoms"].get(symptom, 0.2)
        current_score = disease.get("score", 1.0)
        disease["score"] = current_score * multiplier(base_prob)
    
    # Normalize scores
    total = sum(d.get("score", 1) for d in diseases)
    if total > 0:
        for disease in diseases:
            disease["probability"] = disease.get("score", 1) / total
    
    return diseases

def get_top_diagnosis(diseases: List[Dict]) -> Dict:
    """Get the most likely diagnosis"""
    return max(diseases, key=lambda d: d.get("probability", d.get("score", 0)))

# ============ AUTH ROUTES ============
@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    user_doc = {
        "user_id": user_id,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "name": user_data.name,
        "picture": None,
        "total_games": 0,
        "correct_diagnoses": 0,
        "score": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    token = create_token(user_id)
    
    return {
        "token": token,
        "user": {
            "user_id": user_id,
            "email": user_data.email,
            "name": user_data.name,
            "total_games": 0,
            "correct_diagnoses": 0,
            "score": 0
        }
    }

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user.get("password", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user["user_id"])
    
    return {
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "email": user["email"],
            "name": user["name"],
            "picture": user.get("picture"),
            "total_games": user.get("total_games", 0),
            "correct_diagnoses": user.get("correct_diagnoses", 0),
            "score": user.get("score", 0)
        }
    }

@api_router.post("/auth/session")
async def process_google_session(request: Request, response: Response):
    """Process Google OAuth session from Emergent Auth"""
    body = await request.json()
    session_id = body.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")
    
    # Exchange session_id for user data
    async with httpx.AsyncClient() as client:
        auth_response = await client.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id}
        )
    
    if auth_response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    auth_data = auth_response.json()
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": auth_data["email"]}, {"_id": 0})
    
    if existing_user:
        user_id = existing_user["user_id"]
        # Update user info
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "name": auth_data["name"],
                "picture": auth_data["picture"]
            }}
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": auth_data["email"],
            "name": auth_data["name"],
            "picture": auth_data["picture"],
            "total_games": 0,
            "correct_diagnoses": 0,
            "score": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    # Create session
    session_token = auth_data["session_token"]
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60
    )
    
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture"),
        "total_games": user.get("total_games", 0),
        "correct_diagnoses": user.get("correct_diagnoses", 0),
        "score": user.get("score", 0)
    }

@api_router.get("/auth/me")
async def get_me(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture"),
        "total_games": user.get("total_games", 0),
        "correct_diagnoses": user.get("correct_diagnoses", 0),
        "score": user.get("score", 0)
    }

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out"}

# ============ GAME ROUTES ============
@api_router.get("/specialties")
async def get_specialties():
    return list(SPECIALTIES.items())

@api_router.post("/game/start")
async def start_game(game_request: GameStartRequest, request: Request):
    user = await get_current_user(request)
    
    specialty = game_request.specialty
    if specialty not in DISEASES_DB:
        raise HTTPException(status_code=400, detail="Invalid specialty")
    
    # Initialize diseases with scores
    diseases = []
    for disease in DISEASES_DB[specialty]:
        d = disease.copy()
        d["score"] = 1.0
        d["probability"] = 1.0 / len(DISEASES_DB[specialty])
        diseases.append(d)
    
    # Select first question
    first_symptom = select_next_question(diseases, [])
    
    game_id = f"game_{uuid.uuid4().hex[:12]}"
    game_session = {
        "game_id": game_id,
        "user_id": user["user_id"] if user and not game_request.is_anonymous else None,
        "specialty": specialty,
        "diseases": diseases,
        "asked_symptoms": [],
        "current_symptom": first_symptom,
        "question_number": 1,
        "is_anonymous": game_request.is_anonymous,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed": False
    }
    
    await db.game_sessions.insert_one(game_session)
    
    return {
        "game_id": game_id,
        "specialty": SPECIALTIES[specialty],
        "question_number": 1,
        "question": SYMPTOM_QUESTIONS.get(first_symptom, f"Does the patient have {first_symptom.replace('_', ' ')}?"),
        "symptom_key": first_symptom,
        "total_questions": 10
    }

@api_router.post("/game/answer")
async def submit_answer(answer_request: GameAnswerRequest, request: Request):
    game = await db.game_sessions.find_one({"game_id": answer_request.game_id}, {"_id": 0})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if game["completed"]:
        raise HTTPException(status_code=400, detail="Game already completed")
    
    # Update probabilities
    diseases = update_disease_probabilities(
        game["diseases"],
        game["current_symptom"],
        answer_request.answer
    )
    
    asked_symptoms = game["asked_symptoms"] + [game["current_symptom"]]
    question_number = game["question_number"] + 1
    
    # Check if game should end
    top_disease = get_top_diagnosis(diseases)
    should_end = (
        question_number > 10 or
        top_disease.get("probability", 0) > 0.75 or
        len(asked_symptoms) >= len(set().union(*[set(d["symptoms"].keys()) for d in diseases]))
    )
    
    if should_end:
        # Complete game
        user = await get_current_user(request)
        
        # Calculate score
        base_score = int(top_disease.get("probability", 0) * 100)
        speed_bonus = max(0, (11 - question_number) * 10)
        total_score = base_score + speed_bonus
        
        await db.game_sessions.update_one(
            {"game_id": answer_request.game_id},
            {"$set": {
                "diseases": diseases,
                "asked_symptoms": asked_symptoms,
                "completed": True,
                "final_diagnosis": top_disease["icd_code"],
                "score": total_score,
                "completed_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Update user stats if authenticated
        if user and not game.get("is_anonymous"):
            await db.users.update_one(
                {"user_id": user["user_id"]},
                {"$inc": {
                    "total_games": 1,
                    "score": total_score
                }}
            )
            
            # Add to leaderboard
            await db.leaderboard.update_one(
                {"user_id": user["user_id"]},
                {"$set": {
                    "name": user["name"],
                    "picture": user.get("picture")
                }, "$inc": {
                    "total_score": total_score,
                    "games_played": 1
                }},
                upsert=True
            )
        
        return {
            "game_completed": True,
            "diagnosis": {
                "icd_code": top_disease["icd_code"],
                "name": top_disease["name"],
                "probability": round(top_disease.get("probability", 0) * 100, 1),
                "education": top_disease.get("education", [])
            },
            "score": total_score,
            "questions_asked": question_number - 1
        }
    
    # Select next question
    next_symptom = select_next_question(diseases, asked_symptoms)
    
    await db.game_sessions.update_one(
        {"game_id": answer_request.game_id},
        {"$set": {
            "diseases": diseases,
            "asked_symptoms": asked_symptoms,
            "current_symptom": next_symptom,
            "question_number": question_number
        }}
    )
    
    # Get top 3 candidates for display
    sorted_diseases = sorted(diseases, key=lambda d: d.get("probability", 0), reverse=True)[:3]
    
    return {
        "game_completed": False,
        "question_number": question_number,
        "question": SYMPTOM_QUESTIONS.get(next_symptom, f"Does the patient have {next_symptom.replace('_', ' ')}?"),
        "symptom_key": next_symptom,
        "top_candidates": [
            {"name": d["name"], "probability": round(d.get("probability", 0) * 100, 1)}
            for d in sorted_diseases
        ]
    }

@api_router.post("/game/hint")
async def get_hint(hint_request: HintRequest):
    """Get AI-powered hint for the current question"""
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="AI service not configured")
    
    game = await db.game_sessions.find_one({"game_id": hint_request.game_id}, {"_id": 0})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    current_symptom = game["current_symptom"]
    symptom_readable = current_symptom.replace("_", " ")
    
    # Get top candidates
    sorted_diseases = sorted(game["diseases"], key=lambda d: d.get("probability", 0), reverse=True)[:3]
    candidates = ", ".join([d["name"] for d in sorted_diseases])
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"hint_{hint_request.game_id}",
            system_message="You are a helpful medical education assistant. Provide concise clinical hints without giving away the answer."
        )
        
        prompt = f"""The current symptom being assessed is: {symptom_readable}
Top diagnostic candidates are: {candidates}

Provide a brief clinical hint (2-3 sentences) about how this symptom relates to differential diagnosis without revealing the answer. Focus on clinical significance."""
        
        response = await chat.send_message(UserMessage(text=prompt))
        
        return {"hint": response}
    except Exception as e:
        logger.error(f"AI hint error: {e}")
        return {"hint": f"Consider the clinical significance of {symptom_readable} in your differential diagnosis."}

@api_router.get("/game/{game_id}/education")
async def get_detailed_education(game_id: str):
    """Get AI-powered detailed education for completed game"""
    game = await db.game_sessions.find_one({"game_id": game_id}, {"_id": 0})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if not game.get("completed"):
        raise HTTPException(status_code=400, detail="Game not completed")
    
    # Get the diagnosed disease
    diagnosed_icd = game.get("final_diagnosis")
    disease = None
    for d in game["diseases"]:
        if d["icd_code"] == diagnosed_icd:
            disease = d
            break
    
    if not disease:
        raise HTTPException(status_code=404, detail="Disease not found")
    
    if not EMERGENT_LLM_KEY:
        return {"education": disease.get("education", []), "ai_enhanced": False}
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"edu_{game_id}",
            system_message="You are a medical education expert. Provide concise, clinically relevant information."
        )
        
        prompt = f"""For the diagnosis: {disease['name']} (ICD: {disease['icd_code']})

Provide a brief educational summary (max 500 characters) covering:
1. Key diagnostic features
2. First-line treatment
3. One important clinical pearl

Be concise and clinically actionable."""
        
        response = await chat.send_message(UserMessage(text=prompt))
        
        return {
            "disease_name": disease["name"],
            "icd_code": disease["icd_code"],
            "base_education": disease.get("education", []),
            "ai_summary": response,
            "ai_enhanced": True
        }
    except Exception as e:
        logger.error(f"AI education error: {e}")
        return {
            "disease_name": disease["name"],
            "icd_code": disease["icd_code"],
            "base_education": disease.get("education", []),
            "ai_enhanced": False
        }

# ============ LEADERBOARD ============
@api_router.get("/leaderboard")
async def get_leaderboard():
    leaders = await db.leaderboard.find({}, {"_id": 0}).sort("total_score", -1).limit(50).to_list(50)
    return leaders

@api_router.get("/user/stats")
async def get_user_stats(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get recent games
    recent_games = await db.game_sessions.find(
        {"user_id": user["user_id"], "completed": True},
        {"_id": 0}
    ).sort("completed_at", -1).limit(10).to_list(10)
    
    # Get specialty breakdown
    pipeline = [
        {"$match": {"user_id": user["user_id"], "completed": True}},
        {"$group": {"_id": "$specialty", "count": {"$sum": 1}, "avg_score": {"$avg": "$score"}}}
    ]
    specialty_stats = await db.game_sessions.aggregate(pipeline).to_list(100)
    
    return {
        "user": {
            "user_id": user["user_id"],
            "name": user["name"],
            "email": user["email"],
            "total_games": user.get("total_games", 0),
            "total_score": user.get("score", 0)
        },
        "recent_games": [
            {
                "game_id": g["game_id"],
                "specialty": g["specialty"],
                "diagnosis": g.get("final_diagnosis"),
                "score": g.get("score", 0),
                "completed_at": g.get("completed_at")
            }
            for g in recent_games
        ],
        "specialty_stats": specialty_stats
    }

# ============ ROOT ============
@api_router.get("/")
async def root():
    return {"message": "Dr. Neuro API - Medical Diagnosis Game"}

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
