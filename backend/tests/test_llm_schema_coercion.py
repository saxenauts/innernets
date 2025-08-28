from app.llm.schemas import EvaluateCandidatesOut


def test_candidate_score_coerces_float_scores():
    data = {
        "scores": [
            {"url": "https://example.com/", "score": 3.6, "read": True},
            {"url": "https://example.org/", "score": 4.2, "read": False},
            {"url": "https://example.net/", "score": "2.9"},
        ]
    }
    out = EvaluateCandidatesOut(**data)
    vals = [s.score for s in out.scores]
    # 3.6 -> 72, 4.2 -> 84, 2.9 -> 58 (rounded)
    assert vals == [72, 84, 58]
