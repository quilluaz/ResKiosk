"""Regression tests for the exact-term retrieval evaluation harness (Person 4 / Sprint 3 Story 6)."""

import unittest

from hub.eval.exact_term_retrieval_eval import load_eval_bundle, run_eval


class TestExactTermRetrievalEval(unittest.TestCase):
    def test_bundle_loads(self):
        bundle = load_eval_bundle()
        self.assertEqual(bundle["snapshot_id"], "exact_term_retrieval_eval_v1")
        self.assertEqual(len(bundle["articles"]), len(bundle["corpus_article_order"]))
        for q in bundle["queries"]:
            self.assertEqual(len(q["vector_cosine_scores"]), len(bundle["corpus_article_order"]))

    def test_hybrid_improves_or_matches_vector_metrics(self):
        report = run_eval()
        m_vec = report["metrics"]["vector_only"]
        m_hy = report["metrics"]["hybrid"]
        self.assertGreaterEqual(m_hy["top1_accuracy"], m_vec["top1_accuracy"])
        self.assertGreaterEqual(m_hy["topk_accuracy"], m_vec["topk_accuracy"])
        self.assertGreater(m_hy["top1_accuracy"], m_vec["top1_accuracy"])

    def test_stability_queries_semantic_safe(self):
        report = run_eval()
        st = report["metrics"]["stability"]
        self.assertGreater(st["checked_queries"], 0)
        self.assertEqual(st["stable_or_improved"], st["checked_queries"])

    def test_exact_term_queries_gain_from_hybrid(self):
        report = run_eval()
        improved = 0
        for row in report["per_query"]:
            if row["eval_class"] in ("proper_noun", "procedure", "location", "mixed"):
                if row["hybrid"]["top1_hit"] and not row["vector_only"]["top1_hit"]:
                    improved += 1
        self.assertGreaterEqual(improved, 1)


if __name__ == "__main__":
    unittest.main()
