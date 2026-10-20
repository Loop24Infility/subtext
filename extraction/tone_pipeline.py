"""
NOTE: downloads model weights from huggingface.co, which this sandbox
can't reach. Correctly structured and ready to run on your own machine or in
Claude Code, where it'll pull the weights once and cache them locally.

Base-layer extraction: per-speaker tone scoring from a transcript. This is the
"good ML model" layer described in the project plan — necessary, not the
differentiator. Its output (tone_score per executive per quarter) is what
feeds divergence/baseline_model.py.

Starting point: ProsusAI/finbert, a public FinBERT checkpoint, as the base
classifier before any fine-tuning on an Indian-transcript corpus (Phase 1).
"""

from dataclasses import dataclass
from transformers import pipeline


@dataclass
class SpeakerTurn:
    speaker: str     # e.g. "CFO"
    text: str


def load_tone_classifier():
    # swap "ProsusAI/finbert" for your own fine-tuned checkpoint once Phase 1
    # training is done
    return pipeline("sentiment-analysis", model="ProsusAI/finbert")


def score_transcript(turns: list[SpeakerTurn], classifier) -> dict[str, float]:
    """
    Returns an average tone_score per speaker, mapped to a -1..1 scale
    (positive - negative probability), matching the scale
    divergence/baseline_model.py expects.
    """
    scores_by_speaker: dict[str, list[float]] = {}

    for turn in turns:
        result = classifier(turn.text[:512])[0]  # truncate to model's max length
        signed = result["score"] if result["label"] == "positive" else -result["score"]
        if result["label"] == "neutral":
            signed = 0.0
        scores_by_speaker.setdefault(turn.speaker, []).append(signed)

    return {
        speaker: sum(scores) / len(scores)
        for speaker, scores in scores_by_speaker.items()
    }


if __name__ == "__main__":
    sample_turns = [
        SpeakerTurn("CFO", "Revenue growth this quarter was steady, in line with our guidance."),
        SpeakerTurn("CFO", "We remain cautious on near-term margins given input cost pressure."),
        SpeakerTurn("CEO", "This was an outstanding quarter and we are extremely confident in our trajectory."),
    ]

    clf = load_tone_classifier()
    scores = score_transcript(sample_turns, clf)
    print(scores)

    # Next: persist these into speaker_tone_scores (db/schema.sql), then
    # accumulate 3+ quarters per executive before divergence/baseline_model.py
    # has enough history to score against.
