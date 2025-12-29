import requests
import json
import time

class OllamaHandler:
    def __init__(self, model="gemma2:2b", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.generate_url = f"{base_url}/api/generate"

    def generate(self, prompt, temperature=0.3, max_retries=3):
        """Generate response from Ollama"""
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
                    timeout=60
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "").strip()
                else:
                    print(f"Ollama error: {response.status_code}")

            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)

        return None

    def answer_medical_question(self, disease_data, disease_name, question):
        """Use LLM to answer student's medical question with hybrid rule-based + AI approach"""

        question_lower = question.lower().strip()

        # ==================== RULE-BASED HANDLING ====================
        # Handle temporal/duration questions directly from data
        temporal_keywords = ['how long', 'when did', 'duration', 'timing', 'how recent',
                            'started when', 'began when', 'time frame', 'how quickly']

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
                explanation_parts.append(f"This timing pattern is typical for {disease_name}.")

                return {
                    "answer": ", ".join(answer_parts),
                    "explanation": " ".join(explanation_parts)
                }

        # Handle chief complaint questions
        chief_complaint_keywords = ['chief complaint', 'main complaint', 'presenting complaint',
                                    'why did', 'what brought', 'presenting with', 'came in for']

        if any(kw in question_lower for kw in chief_complaint_keywords):
            chief_complaint = disease_data.get('initial_presentation', {}).get('chief_complaint', '')
            if chief_complaint:
                return {
                    "answer": chief_complaint,
                    "explanation": f"This is the patient's chief complaint on presentation. {chief_complaint.capitalize()} is characteristic of {disease_name}."
                }

        # Handle vital signs questions
        if 'vital' in question_lower or 'temperature' in question_lower or 'blood pressure' in question_lower or 'heart rate' in question_lower:
            vitals = disease_data.get('physical_exam', {}).get('vital_signs', {})
            if vitals:
                vital_summary = []
                for key, value in vitals.items():
                    vital_summary.append(f"{key.replace('_', ' ')}: {value}")

                return {
                    "answer": "; ".join(vital_summary),
                    "explanation": f"These vital signs are typical for {disease_name}."
                }

        # Handle age/demographics questions
        if 'how old' in question_lower or 'age' in question_lower or 'demographics' in question_lower:
            demographics = disease_data.get('initial_presentation', {}).get('patient_demographics', {})
            age_range = demographics.get('age_range', '')
            sex = demographics.get('sex', '')

            if age_range or sex:
                demo_parts = []
                if age_range:
                    demo_parts.append(f"Age: {age_range}")
                if sex:
                    demo_parts.append(f"Sex: {sex}")

                return {
                    "answer": "; ".join(demo_parts),
                    "explanation": f"These demographics are typical for {disease_name}."
                }

        # ==================== LLM-BASED HANDLING ====================
        # Determine if this is a yes/no question or needs descriptive answer
        is_yes_no = any(question_lower.startswith(q) for q in
                        ['does', 'is', 'are', 'was', 'were', 'has', 'have', 'did', 'can', 'will', 'would'])

        if is_yes_no:
            response_instruction = """
Rules:
1. If a symptom/feature is NOT mentioned in the disease data, answer NO and briefly explain why it's typically absent for this condition but don't mention what the condition is
2. Be medically accurate based on the data
3. Keep your response brief and educational
4. Don't name the condition.

Respond in this exact JSON format (no extra text):
{"answer": "", "explanation": "brief medical reason"}"""
        else:
            response_instruction = """
Rules:
1. Provide a direct, specific answer based on the disease data
2. If the information is in the data, extract and present it clearly
3. If not in the data, explain what is typically expected for this condition
4. Be medically accurate and educational
5. Keep response brief but informative

Respond in this exact JSON format (no extra text):
{"answer": "specific answer", "explanation": "brief medical context"}"""

        prompt = f"""You are a medical game. A student is trying to diagnose a disease by asking questions.

The disease is: {disease_name}

Disease information:
{json.dumps(disease_data, indent=2)}

Student's question: "{question}"

Task: Based ONLY on the disease information provided, answer the student's question.

{response_instruction}"""

        response = self.generate(prompt, temperature=0.2)

        if not response:
            return {
                "answer": "ERROR",
                "explanation": "Unable to process question"
            }

        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return {
                    "answer": "ERROR",
                    "explanation": "Could not parse response"
                }
        except Exception as e:
            return {
                "answer": "ERROR",
                "explanation": f"Invalid response format: {str(e)}"
            }

    def update_differential_diagnosis(self, disease_name, questions_asked, all_diseases, disease_data=None):
        """Generate differential diagnosis based on questions asked so far"""

        findings = []
        for qa in questions_asked:
            if qa['answer'] in ['YES', 'NO']:
                findings.append(f"• {qa['question']}: {qa['answer']}")

        if not findings:
            return []

        # Get the proper differential from disease data if available
        suggested_differential = []
        if disease_data:
            diff_data = disease_data.get('differential_diagnosis', {})
            suggested_differential = diff_data.get('early_differential', [])

        # If no suggested differential, use all diseases
        if not suggested_differential:
            suggested_differential = [d['name'] for d in all_diseases[:15]]

        prompt = f"""You are helping a medical student build a differential diagnosis.

The student has gathered these findings:
{chr(10).join(findings)}

Based on these findings, consider these possible diagnoses:
{json.dumps(suggested_differential, indent=2)}

Task: Rank the TOP 3 most likely diseases based on the findings.

IMPORTANT: Base your ranking on which diseases best match the YES/NO pattern of findings.

Respond in this exact JSON format:
{{
  "differentials": [
    {{"disease": "Most Likely Disease Name", "likelihood": "high probability", "reasoning": "matches key findings"}},
    {{"disease": "Second Disease Name", "likelihood": "moderate probability", "reasoning": "some findings match"}},
    {{"disease": "Third Disease Name", "likelihood": "lower probability", "reasoning": "fewer findings match"}}
  ]
}}"""

        response = self.generate(prompt, temperature=0.3)

        if not response:
            return []

        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                return result.get('differentials', [])
        except:
            return []

    def check_diagnosis(self, correct_disease, student_diagnosis):
        """Check if student's diagnosis matches the correct disease"""
        prompt = f"""Compare these two disease names and determine if they refer to the same condition.

Correct disease: {correct_disease}
Student's diagnosis: {student_diagnosis}

Consider:
- Exact matches
- Common abbreviations (TB for Tuberculosis, MI for Myocardial Infarction)
- Synonyms (Heart Attack for Myocardial Infarction)
- Spelling variations

Respond in this exact JSON format:
{{"correct": true/false, "reasoning": "brief explanation"}}"""

        response = self.generate(prompt, temperature=0.1)

        if not response:
            return {"correct": False, "reasoning": "Unable to verify"}

        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                if isinstance(result.get("correct"), str):
                    result["correct"] = result["correct"].lower() == "true"
                return result
            else:
                return {
                    "correct": correct_disease.lower() in student_diagnosis.lower(),
                    "reasoning": "Simple text comparison"
                }
        except:
            return {
                "correct": correct_disease.lower() in student_diagnosis.lower(),
                "reasoning": "Fallback comparison"
            }

    def assess_diagnostic_quality(self, questions_asked, disease_data, correct_disease):
        """
        Assess the quality of the student's diagnostic approach
        NOTE: This is now deprecated in favor of the comprehensive PerformanceEvaluator
        Kept for backward compatibility
        """
        essential_features = disease_data.get('key_features', [])[:3]

        # Use scoring_criteria if available
        scoring_criteria = disease_data.get('scoring_criteria', {})
        essential_questions = scoring_criteria.get('essential_questions', [])

        if not essential_features and not essential_questions:
            return {
                "pathway_quality": "unknown",
                "essential_asked": 0,
                "essential_missed": 0,
                "feedback": "Unable to assess - no criteria available"
            }

        prompt = f"""Assess a medical student's diagnostic approach.

Correct disease: {correct_disease}

Essential questions that should be asked:
{json.dumps(essential_questions if essential_questions else essential_features, indent=2)}

Questions the student actually asked:
{json.dumps([q['question'] for q in questions_asked], indent=2)}

Task: Evaluate their diagnostic reasoning quality.

Respond in this exact JSON format:
{{
  "pathway_quality": "excellent/good/fair/poor",
  "essential_asked": number_of_essential_questions_asked,
  "essential_missed": number_of_essential_questions_missed,
  "feedback": "1-2 sentence constructive feedback"
}}"""

        response = self.generate(prompt, temperature=0.2)

        if not response:
            return {
                "pathway_quality": "unknown",
                "essential_asked": 0,
                "essential_missed": len(essential_questions) if essential_questions else len(essential_features),
                "feedback": "Unable to assess"
            }

        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except:
            return {
                "pathway_quality": "unknown",
                "essential_asked": 0,
                "essential_missed": len(essential_questions) if essential_questions else len(essential_features),
                "feedback": "Unable to assess"
            }
