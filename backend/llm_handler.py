import requests
import json
import time
import re

class OllamaHandler:
    def __init__(self, model="gemma2:2b", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.generate_url = f"{base_url}/api/generate"
        self.ollama_available = self._check_ollama()

    def _check_ollama(self):
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            print("Ollama not available - using rule-based responses only")
            return False

    def generate(self, prompt, temperature=0.3, max_retries=2):
        """Generate response from Ollama"""
        if not self.ollama_available:
            return None
            
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.generate_url,
                    json=payload,
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "").strip()
                else:
                    print(f"Ollama error: {response.status_code}")

            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(1)

        return None

    def _extract_symptom_value(self, disease_data, symptom_key):
        """Extract symptom value from disease data"""
        history = disease_data.get('history', {})
        primary = history.get('primary_symptoms', {})
        associated = history.get('associated_symptoms', {})
        
        # Check primary symptoms
        if symptom_key in primary:
            return primary[symptom_key]
        
        # Check associated symptoms
        if symptom_key in associated:
            return associated[symptom_key]
        
        # Check with variations
        for key, value in {**primary, **associated}.items():
            if symptom_key in key or key in symptom_key:
                return value
        
        return None

    def _is_yes_answer(self, value):
        """Determine if a symptom value indicates yes"""
        if not value:
            return False
        value_lower = str(value).lower()
        yes_indicators = ['yes', 'present', 'positive', 'true', 'high', 'elevated', 'severe', 'prominent', 'marked']
        no_indicators = ['no', 'absent', 'negative', 'false', 'normal', 'none', 'rare']
        
        for indicator in yes_indicators:
            if indicator in value_lower:
                return True
        for indicator in no_indicators:
            if indicator in value_lower:
                return False
        
        # If it has specific details, likely yes
        if len(value_lower) > 10:
            return True
        return None  # Uncertain

    def answer_medical_question(self, disease_data, disease_name, question):
        """Answer medical question with comprehensive rule-based + AI approach"""

        question_lower = question.lower().strip()

        # ==================== RULE-BASED HANDLING ====================
        
        # 1. Chief complaint questions
        chief_complaint_keywords = ['chief complaint', 'main complaint', 'presenting complaint',
                                    'why did', 'what brought', 'presenting with', 'came in for',
                                    'reason for visit', 'what is wrong']

        if any(kw in question_lower for kw in chief_complaint_keywords):
            chief_complaint = disease_data.get('initial_presentation', {}).get('chief_complaint', '')
            if chief_complaint:
                return {
                    "answer": chief_complaint,
                    "explanation": f"This is the patient's chief complaint on presentation."
                }

        # 2. Temporal/duration questions
        temporal_keywords = ['how long', 'when did', 'duration', 'timing', 'how recent',
                            'started when', 'began when', 'time frame', 'how quickly', 'onset']

        if any(kw in question_lower for kw in temporal_keywords):
            onset_data = disease_data.get('history', {}).get('symptom_onset', {})
            timing = onset_data.get('timing', '')
            mode = onset_data.get('mode', '')
            progression = onset_data.get('progression', '')

            if timing or mode:
                answer_parts = []
                if timing:
                    answer_parts.append(timing)
                if mode:
                    answer_parts.append(f"{mode} onset")

                explanation_parts = []
                if timing and mode:
                    explanation_parts.append(f"Symptoms began {timing} with {mode} onset.")
                if progression:
                    explanation_parts.append(f"The symptoms are {progression}.")

                return {
                    "answer": ", ".join(answer_parts) if answer_parts else "Information not available",
                    "explanation": " ".join(explanation_parts) if explanation_parts else "Timing pattern noted."
                }

        # 3. Vital signs questions
        vital_keywords = ['vital', 'temperature', 'blood pressure', 'bp', 'heart rate', 'pulse',
                         'respiratory rate', 'oxygen', 'saturation', 'spo2']
        
        if any(kw in question_lower for kw in vital_keywords):
            vitals = disease_data.get('physical_exam', {}).get('vital_signs', {})
            if vitals:
                vital_summary = []
                for key, value in vitals.items():
                    if value and str(value).lower() != 'normal':
                        vital_summary.append(f"{key.replace('_', ' ').title()}: {value}")
                
                if vital_summary:
                    return {
                        "answer": "; ".join(vital_summary),
                        "explanation": "These are the patient's vital signs."
                    }
                else:
                    return {
                        "answer": "Vital signs are within normal limits",
                        "explanation": "No significant abnormalities in vital signs."
                    }

        # 4. Age/demographics questions
        if 'how old' in question_lower or 'age' in question_lower or 'demographics' in question_lower:
            demographics = disease_data.get('initial_presentation', {}).get('patient_demographics', {})
            age_range = demographics.get('age_range', '')
            sex = demographics.get('sex', '')

            if age_range or sex:
                demo_parts = []
                if age_range:
                    demo_parts.append(f"Age range typically: {age_range}")
                if sex:
                    demo_parts.append(f"Sex distribution: {sex}")

                return {
                    "answer": "; ".join(demo_parts),
                    "explanation": "These demographics are typical for this presentation."
                }

        # 5. Medical history questions
        history_keywords = ['medical history', 'past history', 'pmh', 'comorbid', 'chronic condition',
                           'previous', 'underlying', 'pre-existing']
        
        if any(kw in question_lower for kw in history_keywords):
            pmh = disease_data.get('history', {}).get('past_medical_history', {})
            if pmh:
                history_parts = []
                for key, value in pmh.items():
                    if value and str(value).lower() not in ['none', 'negative', 'no']:
                        history_parts.append(f"{key.replace('_', ' ').title()}: {value}")
                
                if history_parts:
                    return {
                        "answer": "; ".join(history_parts[:3]),
                        "explanation": "Relevant past medical history."
                    }
                else:
                    return {
                        "answer": "No significant past medical history",
                        "explanation": "Past medical history is unremarkable."
                    }

        # 6. Physical exam questions
        exam_keywords = ['physical exam', 'examination', 'on exam', 'findings', 'auscultation',
                        'inspection', 'palpation', 'percussion', 'lung sounds', 'breath sounds',
                        'heart sounds', 'abdomen']
        
        if any(kw in question_lower for kw in exam_keywords):
            exam = disease_data.get('physical_exam', {})
            findings = []
            
            # General appearance
            if 'general' in exam:
                findings.append(f"General: {exam['general']}")
            
            # Check specific systems mentioned
            for system in ['respiratory', 'cardiovascular', 'heent', 'skin', 'neurological', 'abdominal']:
                if system in question_lower or system[:4] in question_lower:
                    system_exam = exam.get(system, {})
                    if isinstance(system_exam, dict):
                        for k, v in system_exam.items():
                            if v:
                                findings.append(f"{k.replace('_', ' ').title()}: {v}")
                    elif system_exam:
                        findings.append(f"{system.title()}: {system_exam}")
            
            # If no specific system, give general findings
            if not findings:
                for system, data in exam.items():
                    if system != 'vital_signs' and data:
                        if isinstance(data, dict):
                            for k, v in list(data.items())[:2]:
                                if v:
                                    findings.append(f"{k.replace('_', ' ').title()}: {v}")
                        else:
                            findings.append(f"{system.title()}: {data}")
            
            if findings:
                return {
                    "answer": "; ".join(findings[:4]),
                    "explanation": "Physical examination findings."
                }

        # 7. Social history questions
        social_keywords = ['social history', 'smoking', 'alcohol', 'drugs', 'occupation', 'travel',
                          'contacts', 'exposure', 'sick contacts', 'living situation']
        
        if any(kw in question_lower for kw in social_keywords):
            social = disease_data.get('history', {}).get('social_history', {})
            if social:
                social_parts = []
                for key, value in social.items():
                    if value and str(value).lower() not in ['none', 'negative', 'no', 'non_contributory']:
                        social_parts.append(f"{key.replace('_', ' ').title()}: {value}")
                
                if social_parts:
                    return {
                        "answer": "; ".join(social_parts[:3]),
                        "explanation": "Relevant social history."
                    }
            return {
                "answer": "Social history is non-contributory",
                "explanation": "No significant social history factors identified."
            }

        # 8. Specific symptom yes/no questions
        symptom_map = {
            'fever': ['fever', 'temperature', 'febrile'],
            'cough': ['cough', 'coughing'],
            'dyspnea': ['shortness of breath', 'dyspnea', 'breathing difficulty', 'breathless'],
            'chest_pain': ['chest pain', 'chest discomfort'],
            'headache': ['headache', 'head pain'],
            'fatigue': ['fatigue', 'tired', 'weakness'],
            'myalgias': ['muscle ache', 'myalgia', 'body ache'],
            'nausea': ['nausea', 'nauseous'],
            'vomiting': ['vomiting', 'vomit', 'throwing up'],
            'diarrhea': ['diarrhea', 'loose stool'],
            'sore_throat': ['sore throat', 'throat pain'],
            'rhinorrhea': ['runny nose', 'nasal discharge', 'rhinorrhea'],
            'chills': ['chills', 'rigors'],
            'sweating': ['sweating', 'diaphoresis'],
            'weight_loss': ['weight loss', 'losing weight'],
            'appetite': ['appetite', 'eating'],
            'rash': ['rash', 'skin lesion'],
            'swelling': ['swelling', 'edema'],
            'pain': ['pain', 'ache', 'discomfort']
        }

        for symptom_key, keywords in symptom_map.items():
            if any(kw in question_lower for kw in keywords):
                value = self._extract_symptom_value(disease_data, symptom_key)
                
                # Also check associated symptoms
                if not value:
                    for kw in keywords:
                        for k in kw.split():
                            value = self._extract_symptom_value(disease_data, k)
                            if value:
                                break
                        if value:
                            break
                
                if value:
                    is_yes = self._is_yes_answer(value)
                    if is_yes is True:
                        return {
                            "answer": f"YES - {value}",
                            "explanation": f"The patient does have this symptom."
                        }
                    elif is_yes is False:
                        return {
                            "answer": "NO",
                            "explanation": "This symptom is not present or is minimal."
                        }
                    else:
                        return {
                            "answer": str(value),
                            "explanation": "See details above."
                        }
                else:
                    # Check if it's a primary or associated symptom
                    history = disease_data.get('history', {})
                    primary = history.get('primary_symptoms', {})
                    associated = history.get('associated_symptoms', {})
                    
                    # If not mentioned in disease data, likely no
                    return {
                        "answer": "NO - not a typical feature",
                        "explanation": "This symptom is not typically associated with this presentation."
                    }

        # 9. Differential diagnosis question
        if 'differential' in question_lower or 'what else' in question_lower or 'other diagnos' in question_lower:
            diff = disease_data.get('differential_diagnosis', {}).get('early_differential', [])
            if diff:
                return {
                    "answer": ", ".join(diff[:4]),
                    "explanation": "These are conditions to consider in the differential diagnosis."
                }

        # 10. Lab/test results questions
        test_keywords = ['lab', 'test', 'result', 'x-ray', 'xray', 'ct', 'mri', 'blood work',
                        'cbc', 'cmp', 'culture', 'ecg', 'ekg']
        
        if any(kw in question_lower for kw in test_keywords):
            tests = disease_data.get('diagnostic_tests', {}).get('available_tests', {})
            if tests:
                test_results = []
                for test_name, test_data in list(tests.items())[:3]:
                    if isinstance(test_data, dict) and 'result' in test_data:
                        test_results.append(f"{test_name.replace('_', ' ').title()}: {test_data['result']}")
                
                if test_results:
                    return {
                        "answer": "; ".join(test_results),
                        "explanation": "Available test results."
                    }
            return {
                "answer": "Tests pending or not yet ordered",
                "explanation": "Consider what tests would be helpful for diagnosis."
            }

        # ==================== LLM FALLBACK ====================
        # Try LLM if available for complex questions
        if self.ollama_available:
            response = self._llm_answer(disease_data, disease_name, question)
            if response:
                return response

        # ==================== DEFAULT FALLBACK ====================
        # Generic response based on question type
        if question_lower.startswith(('does', 'is', 'are', 'was', 'were', 'has', 'have', 'did', 'can')):
            # Yes/No question - check if any keywords match disease features
            key_features = disease_data.get('key_features', [])
            for feature in key_features:
                if any(word in feature.lower() for word in question_lower.split() if len(word) > 3):
                    return {
                        "answer": "YES",
                        "explanation": f"This is consistent with the clinical picture: {feature}"
                    }
            
            return {
                "answer": "Information not directly available",
                "explanation": "Consider asking about specific symptoms, vital signs, or examination findings."
            }
        else:
            return {
                "answer": "Please ask a more specific question",
                "explanation": "Try asking about symptoms, vital signs, history, or examination findings."
            }

    def _llm_answer(self, disease_data, disease_name, question):
        """Use LLM for complex questions"""
        prompt = f"""You are a medical simulation. A student is diagnosing a patient with {disease_name}.

Disease data: {json.dumps(disease_data, indent=2)[:2000]}

Question: "{question}"

Answer based ONLY on the disease data. Keep response brief.
Format: {{"answer": "brief answer", "explanation": "brief explanation"}}"""

        response = self.generate(prompt, temperature=0.2)
        
        if response:
            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    return json.loads(response[json_start:json_end])
            except:
                pass
        return None

    def update_differential_diagnosis(self, disease_name, questions_asked, all_diseases, disease_data=None):
        """Generate differential diagnosis based on questions asked"""
        if not disease_data:
            return []
            
        # Get the proper differential from disease data
        diff_data = disease_data.get('differential_diagnosis', {})
        suggested_differential = diff_data.get('early_differential', [])
        
        if not suggested_differential:
            return []

        # Simple rule-based ranking based on findings
        findings_yes = [qa['answer'] for qa in questions_asked if 'YES' in qa.get('answer', '').upper()]
        
        differentials = []
        for i, disease in enumerate(suggested_differential[:3]):
            likelihood = "high probability" if i == 0 else "moderate probability" if i == 1 else "lower probability"
            differentials.append({
                "disease": disease,
                "likelihood": likelihood,
                "reasoning": f"Based on clinical findings"
            })
        
        return differentials

    def check_diagnosis(self, correct_disease, student_diagnosis):
        """Check if student's diagnosis matches"""
        correct_lower = correct_disease.lower().strip()
        student_lower = student_diagnosis.lower().strip()
        
        # Direct match
        if correct_lower == student_lower:
            return {"correct": True, "reasoning": "Exact match"}
        
        # Partial match
        if correct_lower in student_lower or student_lower in correct_lower:
            return {"correct": True, "reasoning": "Partial match accepted"}
        
        # Check for common abbreviations and synonyms
        synonyms = {
            'mi': ['myocardial infarction', 'heart attack'],
            'copd': ['chronic obstructive pulmonary disease'],
            'chf': ['congestive heart failure', 'heart failure'],
            'uti': ['urinary tract infection'],
            'dvt': ['deep vein thrombosis'],
            'pe': ['pulmonary embolism'],
            'tb': ['tuberculosis'],
            'dm': ['diabetes mellitus', 'diabetes'],
            'htn': ['hypertension', 'high blood pressure'],
            'cad': ['coronary artery disease'],
            'acs': ['acute coronary syndrome'],
            'pneumonia': ['community acquired pneumonia', 'cap', 'bacterial pneumonia'],
            'flu': ['influenza'],
        }
        
        for abbrev, full_names in synonyms.items():
            if student_lower == abbrev or student_lower in full_names:
                if correct_lower == abbrev or correct_lower in full_names:
                    return {"correct": True, "reasoning": f"Recognized as synonym for {correct_disease}"}
        
        # Word overlap check
        correct_words = set(correct_lower.replace('-', ' ').split())
        student_words = set(student_lower.replace('-', ' ').split())
        overlap = correct_words & student_words
        
        if len(overlap) >= 1 and len(overlap) / len(correct_words) >= 0.5:
            return {"correct": True, "reasoning": "Sufficient word overlap"}
        
        return {"correct": False, "reasoning": f"The correct diagnosis was {correct_disease}"}

    def assess_diagnostic_quality(self, questions_asked, disease_data, correct_disease):
        """Assess diagnostic quality"""
        essential_features = disease_data.get('key_features', [])[:3]
        scoring_criteria = disease_data.get('scoring_criteria', {})
        essential_questions = scoring_criteria.get('essential_questions', [])

        if not essential_features and not essential_questions:
            return {
                "pathway_quality": "unknown",
                "essential_asked": 0,
                "essential_missed": 0,
                "feedback": "Unable to assess - no criteria available"
            }

        # Count how many essential topics were covered
        all_essential = essential_questions + essential_features
        asked_text = ' '.join([q['question'].lower() for q in questions_asked])
        
        covered = sum(1 for item in all_essential if any(word in asked_text for word in item.lower().split() if len(word) > 3))
        missed = len(all_essential) - covered
        
        if covered >= len(all_essential) * 0.8:
            quality = "excellent"
        elif covered >= len(all_essential) * 0.5:
            quality = "good"
        elif covered >= len(all_essential) * 0.3:
            quality = "fair"
        else:
            quality = "needs_improvement"

        return {
            "pathway_quality": quality,
            "essential_asked": covered,
            "essential_missed": missed,
            "feedback": f"Covered {covered} of {len(all_essential)} essential areas."
        }
