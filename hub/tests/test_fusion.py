import unittest

from hub.retrieval.fusion import RankedCandidate, rrf_fuse


class TestReciprocalRankFusion(unittest.TestCase):
    def test_overlapping_candidate_receives_both_contributions(self):
        output = rrf_fuse(
            vector_candidates=[
                RankedCandidate(article_id=1, score=0.91, rank=1),
                RankedCandidate(article_id=2, score=0.80, rank=2),
            ],
            lexical_candidates=[
                RankedCandidate(article_id=2, score=4.2, rank=1),
                RankedCandidate(article_id=3, score=3.7, rank=2),
            ],
            top_k=5,
            rrf_k=60,
        )

        self.assertEqual(output.strategy, "rrf")
        self.assertEqual(output.parameters, {"rrf_k": 60, "top_k": 5})
        self.assertEqual(output.results[0].article_id, 2)
        self.assertEqual(output.results[0].overlap_count, 2)
        self.assertEqual(output.results[0].vector_rank, 2)
        self.assertEqual(output.results[0].lexical_rank, 1)

    def test_lexical_only_and_vector_only_candidates_are_included(self):
        output = rrf_fuse(
            vector_candidates=[RankedCandidate(article_id=10, score=0.7, rank=1)],
            lexical_candidates=[RankedCandidate(article_id=20, score=2.1, rank=1)],
            top_k=5,
            rrf_k=60,
        )

        ids = {r.article_id for r in output.results}
        self.assertEqual(ids, {10, 20})

    def test_tie_breaks_are_deterministic(self):
        output = rrf_fuse(
            vector_candidates=[RankedCandidate(article_id=8, score=0.9, rank=1)],
            lexical_candidates=[RankedCandidate(article_id=4, score=9.0, rank=1)],
            top_k=5,
            rrf_k=60,
        )

        self.assertEqual([r.article_id for r in output.results], [8, 4])
        self.assertEqual(output.tie_breaks[0]["article_id"], 8)

    def test_top_k_limits_output(self):
        output = rrf_fuse(
            vector_candidates=[
                RankedCandidate(article_id=1, score=0.9, rank=1),
                RankedCandidate(article_id=2, score=0.8, rank=2),
                RankedCandidate(article_id=3, score=0.7, rank=3),
            ],
            lexical_candidates=[],
            top_k=2,
            rrf_k=10,
        )

        self.assertEqual([r.article_id for r in output.results], [1, 2])
        self.assertEqual(output.parameters, {"rrf_k": 10, "top_k": 2})


if __name__ == "__main__":
    unittest.main()
