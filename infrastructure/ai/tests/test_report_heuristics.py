from django.test import SimpleTestCase

from infrastructure.ai.report_heuristics import heuristic_report_analysis, is_legacy_placeholder_analysis


class ReportHeuristicsTests(SimpleTestCase):
    def test_feedback_is_content_aware_not_api_placeholder(self):
        text = (
            'Introduction\nThis project aims to build a library system.\n'
            'Literature Review\nPrior work shows similar systems (Smith, 2020).\n'
            'Methodology\nWe used Django and MySQL for implementation.\n'
            'Results\nTesting showed improved performance in 80% of cases.\n'
            'Conclusion\nObjectives were met and future work is planned.\n'
            'References\nSmith, 2020.'
        )
        criteria = [
            {'id': 1, 'name': 'Technical content', 'max_score': 20},
            {'id': 2, 'name': 'Presentation', 'max_score': 10},
        ]
        result = heuristic_report_analysis('Library System', text, criteria)
        feedback = result['suggested_feedback']

        self.assertNotIn('no AI API key', feedback.lower())
        self.assertNotIn('automated draft: review the pdf carefully', feedback.lower())
        self.assertIn('Strengths:', feedback)
        self.assertTrue(result['suggested_criterion_scores'])
        self.assertEqual(result['provider'], 'local_analysis')

    def test_empty_text_gives_actionable_feedback(self):
        result = heuristic_report_analysis('Empty Report', '', [{'id': 1, 'name': 'Content', 'max_score': 10}])
        self.assertIn('could not extract', result['suggested_feedback'].lower())

    def test_legacy_placeholder_detection(self):
        legacy = {
            'suggested_feedback': (
                'Automated draft: review the PDF carefully and adjust rubric scores before approving. '
                'This suggestion used local heuristics because no AI API key is configured.'
            ),
            'provider': 'heuristic',
        }
        self.assertTrue(is_legacy_placeholder_analysis(legacy))
        self.assertFalse(is_legacy_placeholder_analysis({'provider': 'local_analysis', 'suggested_feedback': 'Strengths:\n• Good work.'}))
