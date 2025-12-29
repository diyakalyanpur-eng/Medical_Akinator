import math
from typing import Dict, List

class BayesianDiseaseEvaluator:
    """
    Bayesian / Akinator-style probabilistic evaluator
    Calculates P(disease | answers) and evaluates diagnostic efficiency.
    """

    def __init__(self, diseases_data: List[Dict]):
        self.diseases_data = diseases_data
        self.disease_profiles = self._extract_feature_profiles()
        self._initialize_priors()

    def _extract_feature_profiles(self) -> Dict[str, Dict[str, float]]:
        """Convert disease data into P(feature|disease) likelihood table"""
        mapping = {
            "yes": 0.9, "often": 0.8, "typical": 0.8,
            "sometimes": 0.5, "may": 0.5,
            "rare": 0.2, "no": 0.05
        }
        profiles = {}

        for d in self.diseases_data:
            disease_name = d["name"]
            profiles[disease_name] = {}
            hist = d.get("history", {})
            primary = hist.get("primary_symptoms", {})
            assoc = hist.get("associated_symptoms", {})
            exams = d.get("physical_exam", {})
            timing = hist.get("timing", {})
            features = {**primary, **assoc, **timing}
            
            # Flatten physical exam
            if isinstance(exams, dict):
                for section, findings in exams.items():
                    if isinstance(findings, dict):
                        for k, v in findings.items():
                            features[f"{section}_{k}"] = v
                    else:
                        features[section] = findings

            for k, val in features.items():
                val_str = str(val).lower()
                prob = next((p for key, p in mapping.items() if key in val_str), 0.5)
                profiles[disease_name][k.lower()] = prob

        return profiles

    def _initialize_priors(self):
        """Uniform priors initially"""
        n = max(len(self.disease_profiles), 1)
        self.posteriors = {d: 1 / n for d in self.disease_profiles}

    def update_with_question(self, question: str, answer: str):
        """Bayesian update: P(disease|answer) ∝ P(answer|disease) * P(disease)"""
        q = question.lower()
        observed_yes = answer.lower() in ("yes", "true", "positive", "present")
        new_post = {}

        for disease, features in self.disease_profiles.items():
            likelihood = 0.5  # neutral default
            for f, prob in features.items():
                if f in q:
                    likelihood = prob if observed_yes else (1 - prob)
                    break
            new_post[disease] = self.posteriors[disease] * likelihood

        total = sum(new_post.values()) or 1e-6
        for d in new_post:
            new_post[d] /= total
        self.posteriors = new_post

    def confidence_of(self, true_disease: str) -> float:
        """Return posterior probability of the true disease"""
        return round(self.posteriors.get(true_disease, 0.0) * 100, 1)
    
    def get_confidence(self, true_disease: str) -> float:
        """Alias for confidence_of"""
        return self.confidence_of(true_disease)

    def information_gain_from(self, prev_probs: Dict[str, float]) -> float:
        """Compute relative entropy drop"""
        def entropy(probs):
            return -sum(p * math.log2(p) for p in probs.values() if p > 0)
        return max(0, entropy(prev_probs) - entropy(self.posteriors))
    
    def get_information_gain(self, prev_probs: Dict[str, float]) -> float:
        """Alias for information_gain_from"""
        return self.information_gain_from(prev_probs)

    def final_bayesian_score(self, true_disease: str, num_questions: int, optimal_q: int = 10) -> float:
        """Compute final Bayesian evaluation score"""
        conf = self.confidence_of(true_disease)
        efficiency_penalty = max(0, (num_questions - optimal_q) * 2)
        score = max(0, min(100, conf - efficiency_penalty))
        return round(score, 1)
    
    def final_score(self, true_disease: str, num_questions: int, optimal_q: int = 10) -> float:
        """Alias for final_bayesian_score"""
        return self.final_bayesian_score(true_disease, num_questions, optimal_q)
