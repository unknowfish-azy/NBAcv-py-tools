"""Conservative identity evidence; scores are NOT calibrated probabilities.

Only repeated, high-confidence team + jersey observations can produce a
provisional name. Appearance is a candidate retrieval cue only. Track IDs are
scoped to a shot; absence from video never establishes absence from the court.
"""
from collections import defaultdict
import math


def histogram_similarity(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    try:
        a, b = [float(x) for x in a], [float(x) for x in b]
    except (ValueError, TypeError):
        return 0.0
    if any(not math.isfinite(x) or x < 0 for x in a + b):
        return 0.0
    na, nb = sum(a), sum(b)
    if na <= 0 or nb <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - sum(abs(x/na-y/nb) for x, y in zip(a, b))/2))


def _score(value):
    try:
        value = float(value)
        return max(0.0, min(.999, value)) if math.isfinite(value) else 0.0
    except (TypeError, ValueError):
        return 0.0


class IdentityResolver:
    def __init__(self, gallery=None, min_team=.8, min_jersey=.8,
                 min_repeats=3, min_interval=.25):
        self.gallery = gallery or []
        self.min_team, self.min_jersey = min_team, min_jersey
        self.min_repeats = max(2, min_repeats)
        self.min_interval = max(.001, min_interval)
        self._evidence = defaultdict(list)
        self._results = {}
        self._roster = []

    def update(self, obs, roster):
        ts = obs.get('timestamp')
        if not isinstance(ts, (int, float)) or not math.isfinite(ts) or ts < 0:
            raise ValueError('timestamp must be finite nonnegative seconds')
        tid, shot = obs.get('track_id'), obs.get('shot_id', 0)
        if tid is None:
            raise ValueError('track_id is required')
        self._roster = roster or []
        key = (tid, shot)
        evidence = self._evidence[key]
        reasons = []
        team, number = obs.get('team'), obs.get('jersey_number')
        tc, jc = _score(obs.get('team_score')), _score(obs.get('jersey_score'))
        matches = [p for p in self._roster if team and number is not None
                   and p.get('team') == team and str(p.get('jersey_number')) == str(number)
                   and p.get('player_id') not in (None, '', 'unknown')]
        independent = not any(abs(e['timestamp']-ts) < self.min_interval for e in evidence)
        if len(matches) > 1:
            reasons.append('ambiguous_roster_match')
        if len(matches) == 1 and tc >= self.min_team and jc >= self.min_jersey and independent:
            evidence.append(dict(timestamp=ts, player_id=matches[0]['player_id'],
                                 weight=min(tc, jc), team=team, jersey_number=str(number),
                                 source=obs.get('evidence_source', 'unspecified_team_jersey'),
                                 frame=obs.get('frame')))
        groups = defaultdict(list)
        for e in evidence:
            groups[e['player_id']].append(e)
        identity, score = 'unknown', 0.0
        if len(groups) > 1:
            reasons.append('conflicting_identity_evidence')
        elif groups:
            pid, rows = next(iter(groups.items()))
            score = min(.99, sum(e['weight'] for e in rows)/len(rows) * min(1, len(rows)/self.min_repeats))
            if len(rows) >= self.min_repeats and not reasons:
                identity = pid
        candidates = [dict(player_id=pid, score=round(sum(e['weight'] for e in rows)/len(rows), 4),
                           basis='team_jersey', observations=len(rows)) for pid, rows in groups.items()]
        features = obs.get('features') or {}
        for item in self.gallery:
            similarities = []
            for field in ('jersey_histogram', 'shoe_histogram', 'appearance_histogram'):
                sim = histogram_similarity(features.get(field, []), (item.get('features') or {}).get(field, []))
                if sim > 0:
                    similarities.append(sim)
            if similarities:
                candidates.append(dict(player_id=item.get('player_id'), score=round(sum(similarities)/len(similarities), 4), basis='appearance_only'))
        result = dict(track_id=tid, shot_id=shot, timestamp=ts, identity=identity,
                      identity_status='provisional' if identity != 'unknown' else 'unknown',
                      evidence_score=round(score, 4), score_calibrated=False,
                      independent_observations=len(evidence), evidence=[dict(e) for e in evidence],
                      candidates=sorted(candidates, key=lambda c:c['score'], reverse=True),
                      review_reasons=reasons)
        self._results[key] = result
        return result

    def presence(self, timestamp, visible_track_ids, shot_id=0, coverage='partial', substitution_events=None):
        """Explicit visible IDs are required; official/human confirmed events alone
        determine substitution. Full coverage still cannot prove substitution.
        """
        visible, out = set(visible_track_ids or []), []
        for player in self._roster:
            pid = player.get('player_id')
            tracks = [tid for (tid, shot), result in self._results.items()
                      if shot == shot_id and result['identity'] == pid]
            screen = 'unknown'
            if tracks and coverage not in ('unknown', 'cutaway'):
                screen = 'on_screen' if visible.intersection(tracks) else 'off_screen'
            events = [e for e in substitution_events or [] if e.get('player_id') == pid
                      and e.get('confirmed') is True and e.get('source')
                      and isinstance(e.get('timestamp'), (int,float)) and 0 <= e['timestamp'] <= timestamp
                      and e.get('status') in ('in','out')]
            event = max(events, key=lambda e:e['timestamp']) if events else None
            court = 'unknown'
            if event:
                court = 'confirmed_substituted_out' if event['status'] == 'out' else 'confirmed_on_court'
            out.append(dict(player_id=pid, screen_state=screen, court_state=court,
                            court_evidence=event, timestamp=timestamp, shot_id=shot_id))
        return out
