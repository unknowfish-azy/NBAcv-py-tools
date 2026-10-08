"""Evidence-scored identity resolver; unknown is the safe result."""
from collections import defaultdict
def resolve_identity(track,roster,min_confidence=.8):
    number=str(track.get("jersey_number")) if track.get("jersey_number") is not None else None
    team=track.get("team");matches=[p for p in roster if number and str(p.get("jersey_number"))==number and (not team or p.get("team")==team)]
    if len(matches)!=1:return {"track_id":track.get("track_id"),"identity":"unknown","confidence":0.0,"evidence":[]}
    p=matches[0];return {"track_id":track.get("track_id"),"identity":p.get("player_id","unknown"),"name":p.get("name"),"confidence":1.0,"evidence":["jersey_number","team"]}
def build_identity_report(rows):
    by=defaultdict(list)
    for r in rows:by[r.get("track_id")].append(r)
    switches=0;unknown=0;resolved=0
    for vals in by.values():
        prev=None
        for r in sorted(vals,key=lambda x:x.get("frame",0)):
            ident=r.get("identity","unknown")
            if ident=="unknown":unknown+=1
            else:
                resolved+=1
                if prev and ident!=prev:switches+=1
                prev=ident
    return {"tracks":len(by),"id_switches":switches,"unknown_observations":unknown,"resolved_observations":resolved,"identity_unknown_rate":unknown/max(1,unknown+resolved)}
