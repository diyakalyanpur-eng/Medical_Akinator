from typing import List, Dict
from bayesian_evaluator import BayesianDiseaseEvaluator

class PerformanceEvaluator:
    """Evaluates medical student diagnostic performance"""

    def __init__(self, llm_handler=None):
        self.llm_handler = llm_handler

    def evaluate_question_quality(
        self,
        questions_asked: List[Dict],
        disease_data: Dict,
        disease_name: str
    ) -> Dict:
        scoring_criteria = disease_data.get('scoring_criteria', {})
        essential_questions = scoring_criteria.get('essential_questions', [])
        essential_exams = scoring_criteria.get('essential_exams', [])
        optimal_question_count = scoring_criteria.get('optimal_question_count', 15)

        all_essential_items = essential_questions + essential_exams
        asked_questions_text = [q['question'].lower() for q in questions_asked]

        essential_coverage = self._calculate_essential_coverage(
            asked_questions_text,
            all_essential_items,
            disease_data
        )

        questions_count = len(questions_asked)
        efficiency_score = self._calculate_efficiency_score(
            questions_count,
            optimal_question_count
        )

        completeness_score = (
            essential_coverage['covered_count'] /
            max(len(all_essential_items), 1)
        ) * 100

        quality_rating = self._determine_quality_rating(
            completeness_score,
            efficiency_score
        )

        return {
            'essential_questions_total': len(all_essential_items),
            'essential_questions_asked': essential_coverage['covered_count'],
            'essential_questions_missed': essential_coverage['missed_count'],
            'essential_items_covered': essential_coverage['covered_items'],
            'essential_items_missed': essential_coverage['missed_items'],
            'total_questions_asked': questions_count,
            'optimal_question_count': optimal_question_count,
            'efficiency_score': round(efficiency_score, 1),
            'completeness_score': round(completeness_score, 1),
            'quality_rating': quality_rating,
            'redundant_questions': self._identify_redundant_questions(questions_asked)
        }

    def _calculate_essential_coverage(
        self,
        asked_questions: List[str],
        essential_items: List[str],
        disease_data: Dict
    ) -> Dict:
        covered, missed = [], []
        for item in essential_items:
            item_lower = item.lower()
            keywords = self._extract_keywords(item_lower)
            is_covered = False
            for question in asked_questions:
                if self._question_covers_topic(question, keywords, item_lower, disease_data):
                    is_covered = True
                    break
            (covered if is_covered else missed).append(item)
        return {
            'covered_items': covered,
            'missed_items': missed,
            'covered_count': len(covered),
            'missed_count': len(missed)
        }

    def _extract_keywords(self, item: str) -> List[str]:
        stop_words = {'the', 'and', 'or', 'for', 'in', 'on', 'at', 'to', 'a', 'an'}
        words = item.replace('_', ' ').split()
        return [w for w in words if w not in stop_words and len(w) > 2]

    def _question_covers_topic(
        self,
        question: str,
        keywords: List[str],
        topic: str,
        disease_data: Dict
    ) -> bool:
        q = question.lower()
        if topic in q or any(kw in q for kw in keywords):
            return True
        topic_mappings = {
            'symptom onset pattern': ['when', 'started', 'began', 'how long', 'onset', 'duration'],
            'fever and myalgias': ['fever', 'temperature', 'body ache', 'myalgia', 'muscle pain'],
            'seasonal timing': ['season', 'winter', 'time of year', 'when occur'],
            'vaccination status': ['vaccine', 'vaccinated', 'immunization', 'flu shot'],
            'high-risk conditions': ['medical history', 'chronic', 'condition', 'comorbid'],
            'vital signs': ['vital', 'blood pressure', 'heart rate', 'temperature', 'respiratory rate'],
            'respiratory examination': ['lung', 'breath', 'respiratory', 'chest', 'auscult'],
            'assess for complications': ['complication', 'severe', 'worsen', 'danger'],
        }
        for topic_key, topic_keywords in topic_mappings.items():
            if topic_key in topic and any(kw in q for kw in topic_keywords):
                return True
        return False

    def _calculate_efficiency_score(self, questions_asked: int, optimal_count: int) -> float:
        if questions_asked == optimal_count:
            return 100.0
        if questions_asked < optimal_count:
            ratio = questions_asked / optimal_count
            return max(50, ratio * 100)
        excess = questions_asked - optimal_count
        penalty = min(40, excess * 3)
        return max(30, 100 - penalty)

    def _determine_quality_rating(self, completeness_score: float, efficiency_score: float) -> str:
        combined = (completeness_score * 0.6) + (efficiency_score * 0.4)
        if combined >= 90: return "excellent"
        if combined >= 75: return "good"
        if combined >= 60: return "fair"
        return "needs_improvement"

    def _identify_redundant_questions(self, questions_asked: List[Dict]) -> int:
        seen_topics, redundant = set(), 0
        for qa in questions_asked:
            q = qa['question'].lower()
            key_terms = set(word for word in q.split() if len(word) > 4 and word not in {'does', 'have', 'what', 'when', 'where'})
            if key_terms and key_terms.issubset(seen_topics):
                redundant += 1
            seen_topics.update(key_terms)
        return redundant

    def evaluate_differential_accuracy(
        self,
        differential_history: List[List[Dict]],
        correct_disease: str,
        disease_data: Dict
    ) -> Dict:
        if not differential_history:
            return {
                'accuracy_score': 0,
                'correct_disease_rank': None,
                'included_correct_disease': False,
                'differential_quality': 'not_generated',
                'early_accuracy': 0,
                'late_accuracy': 0,
                'improvement': False
            }
        expected_differential = disease_data.get('differential_diagnosis', {}).get('early_differential', [])
        final_differential = differential_history[-1]
        final_analysis = self._analyze_differential_list(final_differential, correct_disease, expected_differential)
        early_differential = differential_history[0]
        early_analysis = self._analyze_differential_list(early_differential, correct_disease, expected_differential)
        improvement = False
        if len(differential_history) > 1:
            improvement = (
                final_analysis['correct_disease_rank'] is not None and
                (early_analysis['correct_disease_rank'] is None or
                 final_analysis['correct_disease_rank'] < early_analysis['correct_disease_rank'])
            )
        accuracy_score = self._calculate_differential_accuracy_score(final_analysis, expected_differential, improvement)
        return {
            'accuracy_score': round(accuracy_score, 1),
            'correct_disease_rank': final_analysis['correct_disease_rank'],
            'included_correct_disease': final_analysis['included_correct_disease'],
            'differential_quality': final_analysis['quality_rating'],
            'expected_diseases_included': final_analysis['expected_count'],
            'total_expected_diseases': len(expected_differential),
            'early_rank': early_analysis['correct_disease_rank'],
            'final_rank': final_analysis['correct_disease_rank'],
            'showed_improvement': improvement,
            'differential_count': len(differential_history),
            'reasoning_quality': self._assess_reasoning_quality(final_differential)
        }

    def _analyze_differential_list(self, differential: List[Dict], correct_disease: str, expected_differential: List[str]) -> Dict:
        if not differential:
            return {'included_correct_disease': False, 'correct_disease_rank': None, 'expected_count': 0, 'quality_rating': 'not_generated'}
        correct_rank = None
        names = [d.get('disease', '').lower() for d in differential]
        true = correct_disease.lower()
        for i, name in enumerate(names, 1):
            if true in name or name in true:
                correct_rank = i
                break
        expected_count = 0
        for expected in expected_differential:
            el = expected.lower()
            if any(el in n or n in el for n in names):
                expected_count += 1
        if correct_rank == 1 and expected_count >= max(1, int(len(expected_differential) * 0.6)):
            quality = 'excellent'
        elif correct_rank and correct_rank <= 3:
            quality = 'good'
        elif correct_rank:
            quality = 'fair'
        else:
            quality = 'poor'
        return {
            'included_correct_disease': correct_rank is not None,
            'correct_disease_rank': correct_rank,
            'expected_count': expected_count,
            'quality_rating': quality
        }

    def _calculate_differential_accuracy_score(self, analysis: Dict, expected_differential: List[str], showed_improvement: bool) -> float:
        score = 0
        if analysis['included_correct_disease']:
            rank = analysis['correct_disease_rank']
            score += {1: 50, 2: 35, 3: 25}.get(rank, 15)
        if expected_differential:
            expected_ratio = analysis['expected_count'] / len(expected_differential)
            score += expected_ratio * 30
        if showed_improvement:
            score += 10
        if analysis['quality_rating'] == 'excellent':
            score += 10
        return min(100, score)

    def _assess_reasoning_quality(self, differential: List[Dict]) -> str:
        if not differential:
            return "not_provided"
        lengths = [len(d.get('reasoning', '')) for d in differential if d.get('reasoning')]
        if not lengths:
            return "minimal"
        avg = sum(lengths) / len(lengths)
        if avg > 50: return "detailed"
        if avg > 20: return "adequate"
        return "minimal"

    def generate_comprehensive_feedback(
        self,
        question_evaluation: Dict,
        differential_evaluation: Dict,
        disease_name: str,
        questions_asked: List[Dict]
    ) -> Dict:
        question_weight = 0.5
        differential_weight = 0.5
        overall_score = (
            (question_evaluation['completeness_score'] * 0.3 +
             question_evaluation['efficiency_score'] * 0.2) * question_weight +
            differential_evaluation['accuracy_score'] * differential_weight
        )
        strengths, areas = [], []
        if question_evaluation['quality_rating'] in ['excellent', 'good']:
            strengths.append(
                f"Asked {question_evaluation['essential_questions_asked']}/"
                f"{question_evaluation['essential_questions_total']} essential questions"
            )
        else:
            areas.append(
                f"Missed {question_evaluation['essential_questions_missed']} "
                f"essential questions: {', '.join(question_evaluation['essential_items_missed'][:3])}"
            )
        if question_evaluation['efficiency_score'] >= 80:
            strengths.append("Efficient questioning approach")
        elif question_evaluation['total_questions_asked'] > question_evaluation['optimal_question_count'] * 1.5:
            areas.append(
                f"Asked {question_evaluation['total_questions_asked']} questions; "
                f"optimal is around {question_evaluation['optimal_question_count']}"
            )
        if differential_evaluation['included_correct_disease']:
            rank = differential_evaluation['correct_disease_rank']
            strengths.append(
                f"{'Correctly identified' if rank == 1 else 'Included'} {disease_name}"
                f"{' as top diagnosis' if rank == 1 else f' in differential (rank {rank})'}"
            )
        else:
            areas.append(f"Did not include {disease_name} in differential diagnosis")
        if differential_evaluation['showed_improvement']:
            strengths.append("Differential diagnosis improved as more information gathered")
        recommendations = self._generate_recommendations(question_evaluation, differential_evaluation, disease_name)
        return {
            'overall_score': round(overall_score, 1),
            'performance_level': self._get_performance_level(overall_score),
            'strengths': strengths,
            'areas_for_improvement': areas,
            'recommendations': recommendations,
            'detailed_metrics': {
                'question_quality': question_evaluation,
                'differential_accuracy': differential_evaluation
            }
        }

    def _generate_recommendations(self, question_eval: Dict, differential_eval: Dict, disease_name: str) -> List[str]:
        recs = []
        if question_eval['essential_questions_missed'] > 0:
            missed = question_eval['essential_items_missed'][:2]
            recs.append(f"Remember to ask about: {', '.join(missed)}")
        if question_eval['redundant_questions'] > 3:
            recs.append("Avoid redundant questions - focus on distinct clinical aspects")
        if question_eval['efficiency_score'] < 70:
            recs.append("Practice creating a focused question strategy before starting")
        if not differential_eval['included_correct_disease']:
            recs.append(f"Review key features of {disease_name} to recognize it in future cases")
        if differential_eval['accuracy_score'] < 60:
            recs.append("Build differential diagnoses systematically as you gather information")
        if differential_eval['reasoning_quality'] == 'minimal':
            recs.append("Provide detailed reasoning for each differential diagnosis")
        if not recs:
            recs.append("Continue practicing systematic approaches to diagnosis")
        return recs[:5]

    def _get_performance_level(self, score: float) -> str:
        if score >= 90: return "outstanding"
        if score >= 80: return "excellent"
        if score >= 70: return "good"
        if score >= 60: return "satisfactory"
        return "needs_improvement"


class BayesianPerformanceEvaluator(PerformanceEvaluator):
    """
    Drop-in replacement that adds a Bayesian pass.
    Use evaluate_bayesian_performance() alongside the existing methods.
    """
    def __init__(self, llm_handler=None, diseases_data=None):
        super().__init__(llm_handler)
        self._diseases_data = diseases_data or []
        self._bayes = BayesianDiseaseEvaluator(self._diseases_data) if self._diseases_data else None

    def evaluate_bayesian_performance(
        self,
        questions_asked: List[Dict],
        disease_data: Dict,
        correct_disease: str
    ) -> Dict:
        if not self._bayes:
            return {
                "bayesian_confidence": 0,
                "information_gain": 0,
                "bayesian_score": 0
            }
        
        # Reset priors every evaluation
        self._bayes._initialize_priors()
        prev = self._bayes.posteriors.copy()
        total_ig = 0.0

        for qa in questions_asked:
            self._bayes.update_with_question(qa.get("question", ""), qa.get("answer", ""))
            total_ig += self._bayes.information_gain_from(prev)
            prev = self._bayes.posteriors.copy()

        optimal_q = disease_data.get("scoring_criteria", {}).get("optimal_question_count", 10)
        conf = self._bayes.confidence_of(correct_disease)
        bayes_score = self._bayes.final_bayesian_score(correct_disease, len(questions_asked), optimal_q=optimal_q)
        return {
            "bayesian_confidence": conf,
            "information_gain": round(total_ig, 3),
            "bayesian_score": bayes_score
        }


def format_evaluation_report(evaluation: Dict) -> str:
    report = []
    report.append("=" * 60)
    report.append("DIAGNOSTIC PERFORMANCE EVALUATION")
    report.append("=" * 60)
    report.append("")
    report.append(f"Overall Score: {evaluation['overall_score']}/100")
    report.append(f"Performance Level: {evaluation['performance_level'].upper()}")
    report.append("")
    if evaluation['strengths']:
        report.append("STRENGTHS:")
        for s in evaluation['strengths']: report.append(f"  - {s}")
        report.append("")
    if evaluation['areas_for_improvement']:
        report.append("AREAS FOR IMPROVEMENT:")
        for a in evaluation['areas_for_improvement']: report.append(f"  - {a}")
        report.append("")
    if evaluation['recommendations']:
        report.append("RECOMMENDATIONS:")
        for i, r in enumerate(evaluation['recommendations'], 1): report.append(f"  {i}. {r}")
        report.append("")
    report.append("=" * 60)
    return "\n".join(report)
