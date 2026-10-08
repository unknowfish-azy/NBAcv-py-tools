import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_identity_cv import resolve_identity, build_identity_report

class IdentityTests(unittest.TestCase):
    def test_unknown_when_evidence_missing(self):
        r=resolve_identity({"track_id":1,"jersey_number":None,"team":None}, [])
        self.assertEqual(r["identity"],"unknown"); self.assertEqual(r["confidence"],0.0)
    def test_number_team_candidate(self):
        roster=[{"player_id":"p7","name":"Player Seven","team":"HOU","jersey_number":"7"}]
        r=resolve_identity({"track_id":1,"jersey_number":"7","team":"HOU"},roster)
        self.assertEqual(r["identity"],"p7"); self.assertGreaterEqual(r["confidence"],0.8)
    def test_conflicting_candidates_stay_unknown(self):
        roster=[{"player_id":"a","name":"A","team":"HOU","jersey_number":"7"},{"player_id":"b","name":"B","team":"HOU","jersey_number":"7"}]
        self.assertEqual(resolve_identity({"track_id":1,"jersey_number":"7","team":"HOU"},roster)["identity"],"unknown")
    def test_report_counts_switches(self):
        self.assertEqual(build_identity_report([{"track_id":1,"frame":1,"identity":"a"},{"track_id":1,"frame":2,"identity":"b"}])["id_switches"],1)
