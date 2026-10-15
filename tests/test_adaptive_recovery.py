import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from fast_fetch_support import RequestGate,GatedSession

class AdaptiveRecoveryTests(unittest.TestCase):
    def test_old_225_profile_recovers_gradually_and_never_below_safe_floor(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'profile.json';path.write_text(json.dumps({'min_spacing':2.25,'retry_after_epoch':0}))
            logs=[];gate=RequestGate(lambda:None,logs.append,baseline=1.0,state_path=path)
            ok=SimpleNamespace(status_code=200)
            self.assertEqual(gate.baseline,1.0);self.assertEqual(gate.interval,2.25)
            for _ in range(19):gate.response(ok)
            self.assertEqual(gate.interval,2.25)
            gate.response(ok);self.assertEqual(gate.interval,1.6875)
            for _ in range(20*12):gate.response(ok)
            self.assertEqual(gate.interval,1.0)
            self.assertTrue(logs)
            reloaded=RequestGate(lambda:None,logs.append,baseline=1.0,state_path=path)
            self.assertEqual(reloaded.interval,1.0)
    def test_429_and_inflight_success_do_not_erase_persistent_cooldown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'profile.json';gate=RequestGate(lambda:None,lambda x:None,baseline=1.0,state_path=path)
            gate.interval=2.25;gate.success_streak=19
            ready=threading.Barrier(2)
            def response(item):ready.wait();gate.response(item)
            a=threading.Thread(target=response,args=(SimpleNamespace(status_code=200),))
            b=threading.Thread(target=response,args=(SimpleNamespace(status_code=429,headers={'Retry-After':'120'}),))
            a.start();b.start();a.join();b.join()
            self.assertTrue(gate.limited);self.assertEqual(gate.success_streak,0)
            self.assertTrue(RequestGate(lambda:None,lambda x:None,baseline=1.0,state_path=path).limited)
            for _ in range(160):gate.response(SimpleNamespace(status_code=200))
            self.assertTrue(gate.limited)
    def test_failures_reset_window_and_cached_responses_do_not_accelerate(self):
        gate=RequestGate(lambda:None,lambda x:None);gate.interval=2.25
        for _ in range(19):gate.response(SimpleNamespace(status_code=200))
        gate.response(SimpleNamespace(status_code=404));gate.response(SimpleNamespace(status_code=200))
        self.assertEqual(gate.interval,2.25);self.assertEqual(gate.success_streak,1)
        gate.network_failure();self.assertEqual(gate.success_streak,0)
        session=SimpleNamespace(get=lambda url,**kwargs:SimpleNamespace(status_code=200))
        cache=SimpleNamespace(get=lambda url:object())
        tls=SimpleNamespace(fast_gate=gate,saved_response_cache=cache)
        proxy=GatedSession(session,tls,lambda:None)
        for _ in range(100):proxy.get('https://shop/products/p')
        self.assertEqual(gate.success_streak,0)

    def test_five_workers_share_one_request_start_budget(self):
        gate=RequestGate(lambda:None,lambda x:None,baseline=0.03)
        starts=[];lock=threading.Lock()
        def worker():
            for _ in range(3):
                gate.wait()
                with lock:starts.append(time.monotonic())
        threads=[threading.Thread(target=worker) for _ in range(5)]
        for thread in threads:thread.start()
        for thread in threads:thread.join()
        starts.sort()
        self.assertEqual(len(starts),15)
        self.assertTrue(all(b-a>=0.025 for a,b in zip(starts,starts[1:])))
