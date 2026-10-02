from dataclasses import dataclass
from math import log1p
@dataclass(frozen=True)
class Signal:
    sensor:str;pipe:str;drop:float;acoustic:float;night_delta:float
def _score(s:Signal):
    return max(0,s.drop)*.5+max(0,s.acoustic)*1.6+log1p(max(0,s.night_delta))*2
def rank(rows:list[Signal]):
    per_sensor={}
    for r in rows:
        sensors=per_sensor.setdefault(r.pipe,{})
        s=_score(r)
        if r.sensor not in sensors or s>sensors[r.sensor]:
            sensors[r.sensor]=s
    scores=[(pipe,sum(by_sensor.values()),len(by_sensor)) for pipe,by_sensor in per_sensor.items()]
    scores.sort(key=lambda x:-x[1])
    return scores
