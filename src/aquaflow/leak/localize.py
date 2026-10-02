from dataclasses import dataclass
from math import log1p
@dataclass(frozen=True)
class Signal:
    sensor:str;pipe:str;drop:float;acoustic:float;night_delta:float
def rank(rows:list[Signal]):
    scores={};sensors={}
    for r in rows:
        s=max(0,r.drop)*.5+max(0,r.acoustic)*1.6+log1p(max(0,r.night_delta))*2
        scores[r.pipe]=scores.get(r.pipe,0)+s
        sensors.setdefault(r.pipe,set()).add(r.sensor)
    return[(p,s,len(sensors[p]))for p,s in sorted(scores.items(),key=lambda x:-x[1])]
