"""Outcome classification per docs/01-outcome-definitions.md.

Each per-carrier check (trailer.py, signature.py, attestation.py) resolves a
PresenceResult for the before-state and the after-state independently, then this
module combines the two into one of the outcomes fixed in the docs.

This module makes no git calls and reads no repository state itself: it is pure
classification logic so it can be unit tested without any fixture repos.
"""

from dataclasses import dataclass
from enum import Enum


class Outcome(Enum):
    RETAINED = "retained"
    SILENTLY_LOST = "silently_lost"
    LOST_SURFACED = "lost_surfaced"
    SPURIOUSLY_GAINED = "spuriously_gained"
    NEVER_EMITTED = "never_emitted"  # excluded from scoring, logged separately


@dataclass(frozen=True)
class PresenceResult:
    present: bool
    origin: str | None  # identity/agent/model/builder the claim names, if present
    surfaced_failure: bool = False  # tooling visibly warned/failed on this check


def classify(
    before: PresenceResult,
    after: PresenceResult,
    ground_truth_origin: str | None = None,
) -> Outcome:
    """Classify one carrier's fate across one operation.

    ground_truth_origin: the actual origin established independently of any carrier
    (e.g., the substantially-human rule's classification for the spurious-gain
    experiment). None means "not being checked for spurious gain" — ordinary
    measured-arm retention/loss scoring only compares before vs. after.
    """
    if not before.present:
        return Outcome.NEVER_EMITTED

    if after.present:
        if ground_truth_origin is not None and after.origin != ground_truth_origin:
            return Outcome.SPURIOUSLY_GAINED
        if after.origin == before.origin:
            return Outcome.RETAINED
        # Present both before and after, but the origin claim changed and there is
        # no independent ground truth to call it spurious against: still a form of
        # loss (the original claim didn't survive), scored as retained-carrier-slot
        # but different origin. Treat conservatively as lost, since the original
        # claim is what "retained" means.
        return Outcome.LOST_SURFACED if after.surfaced_failure else Outcome.SILENTLY_LOST

    return Outcome.LOST_SURFACED if after.surfaced_failure else Outcome.SILENTLY_LOST


def classify_spurious_only(
    before: PresenceResult,
    after: PresenceResult,
    actual_origin_is_human: bool,
) -> Outcome | None:
    """Spurious-gain experiment classification (docs/02).

    before is expected absent (module never had a model-attributed carrier).
    Returns SPURIOUSLY_GAINED if a model-attributed carrier now resolves on a module
    whose actual origin is human; None if the module doesn't qualify for this check
    (e.g., it already had a carrier before, which is out of scope for this
    experiment and should be excluded/logged upstream).
    """
    if before.present:
        return None
    if after.present and actual_origin_is_human:
        return Outcome.SPURIOUSLY_GAINED
    return None
