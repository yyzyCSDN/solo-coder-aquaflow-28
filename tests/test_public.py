import unittest
from datetime import datetime,timezone
from decimal import Decimal
from math import log1p
from aquaflow.api import AquaFlowService
from aquaflow.treatment.chlorine_ct import Segment
from aquaflow.network.isolation import Pipe
from aquaflow.meters.balance import Meter
from aquaflow.leak.localize import Signal
from aquaflow.operations.control_tower import leak_dispatch
from aquaflow.simulation.hydraulics import Node,Link,solve
class T(unittest.TestCase):
    def test_health(self):self.assertEqual(AquaFlowService().health()["runtime_dependencies"],0)
    def test_ct(self):self.assertTrue(AquaFlowService().ct([Segment(20,1,.8,20)],10))
    def test_isolation(self):
        self.assertEqual(AquaFlowService().isolate({"S","A","B"},[Pipe("1","S","A"),Pipe("2","A","B")],{"2"},{"S"}),{"B"})
    def test_balance(self):
        i=[Meter("i",Decimal(0),Decimal(20),Decimal(1))]
        o=[Meter("o",Decimal(0),Decimal(15),Decimal(1))]
        self.assertEqual(AquaFlowService().water_balance(i,o,Decimal(1)),Decimal(4))
    def test_solver(self):
        r=solve([Node("S",0,60),Node("A",5,None)],[Link("L","S","A",2)])
        self.assertTrue(r.converged)
    def test_leak_corroborating_sensors_beat_single_strong(self):
        rows=[Signal("s1","P-A",2.0,1.0,0.0),Signal("s2","P-A",2.0,1.0,0.0),Signal("s3","P-B",6.0,1.0,0.0)]
        r=AquaFlowService().leak_rank(rows)
        self.assertEqual([p for p,_,_ in r],["P-A","P-B"])
        self.assertAlmostEqual(r[0][1],5.2)
        self.assertEqual(r[0][2],2)
        self.assertAlmostEqual(r[1][1],4.6)
        self.assertEqual(r[1][2],1)
    def test_leak_same_sensor_not_double_counted(self):
        r=AquaFlowService().leak_rank([Signal("s1","P-A",4.0,0.0,0.0),Signal("s1","P-A",1.0,0.0,0.0)])
        self.assertEqual(r,[("P-A",2.0,1)])
    def test_leak_all_zero_signals_stable(self):
        r=AquaFlowService().leak_rank([Signal("s1","P2",0.0,0.0,0.0),Signal("s2","P1",0.0,0.0,0.0)])
        self.assertEqual(r,[("P2",0.0,1),("P1",0.0,1)])
    def test_leak_negative_drop_and_night_delta_truncated(self):
        r=AquaFlowService().leak_rank([Signal("s1","P-A",-4.0,0.0,-3.0),Signal("s2","P-B",1.0,0.0,0.0)])
        self.assertEqual(r,[("P-B",0.5,1),("P-A",0.0,1)])
    def test_leak_workflow_end_to_end(self):
        out=AquaFlowService().run_workflow("leak_localization",{"signals":[
            {"sensor":"s1","pipe":"P-A","drop":0,"acoustic":0,"night_delta":3},
            {"sensor":"s2","pipe":"P-A","drop":1,"acoustic":0,"night_delta":0},
            {"sensor":"s3","pipe":"P-B","drop":0,"acoustic":2,"night_delta":0}]})
        self.assertEqual(out["audit"]["contract"],"v1")
        self.assertEqual(out["evidence"]["sensors"],3)
        self.assertEqual(out["value"][0][0],"P-A")
        self.assertAlmostEqual(out["value"][0][1],2*log1p(3)+0.5)
        self.assertEqual(out["value"][0][2],2)
        self.assertEqual(out["value"][1],("P-B",3.2,1))
    def test_leak_dispatch(self):
        rows=[Signal("s1","P-A",2.0,1.0,0.0),Signal("s2","P-A",2.0,1.0,0.0),Signal("s3","P-B",6.0,1.0,0.0)]
        self.assertEqual(leak_dispatch(rows,1,5.0),["P-A"])
if __name__=="__main__":unittest.main()
