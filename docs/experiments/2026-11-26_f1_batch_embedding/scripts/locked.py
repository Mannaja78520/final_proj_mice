"""Hold the PC-wide QC lock, run a script, release. usage: locked.py script.py [args]"""
import sys, runpy, importlib.util
spec = importlib.util.spec_from_file_location("runlock", r"E:\final_proj\mice\mice_system\qc\lib\runlock.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
lk = m.RunLock(say=lambda s: print(s, flush=True))
lk.acquire()
print("LOCK HELD", flush=True)
try:
    sys.argv = sys.argv[1:]
    runpy.run_path(sys.argv[0], run_name="__main__")
finally:
    lk.release(); print("LOCK RELEASED", flush=True)
