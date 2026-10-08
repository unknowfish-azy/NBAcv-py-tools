import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from skeleton_labeler import parse_labelme, validate_pose, detect_temporal_jumps

class SkeletonTests(unittest.TestCase):
    def test_labelme_17_points(self):
        data={"imageWidth":100,"imageHeight":200,"shapes":[{"label":"player_7","shape_type":"points","points":[[i, i+1] for i in range(17)]}]}
        r=parse_labelme(data, expected_points=17)
        self.assertEqual(r["status"],"human_pending")
        self.assertEqual(len(r["people"][0]["keypoints"]),17)
    def test_missing_points_are_unknown(self):
        data={"imageWidth":100,"imageHeight":200,"shapes":[{"label":"player_7","shape_type":"points","points":[[1,2],[3,4]]}]}
        self.assertEqual(parse_labelme(data, expected_points=17)["people"][0]["status"],"invalid")
    def test_coordinate_and_visibility(self):
        kp=[[1,2,2] for _ in range(17)]
        self.assertEqual(validate_pose(kp,100,100)["invalid"],0)
        self.assertGreater(validate_pose([[101,2,2]]+kp[1:],100,100)["invalid"],0)
    def test_temporal_jump_enters_review(self):
        rows=[{"frame":1,"track_id":3,"keypoints":[[0,0,2]]*17},{"frame":2,"track_id":3,"keypoints":[[90,90,2]]*17}]
        self.assertEqual(detect_temporal_jumps(rows, max_displacement=20)[1]["status"],"review")
