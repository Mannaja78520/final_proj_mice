# Review of recent Sonnet work (scheduler, lease, QC pool/lock, Voice lock, #269)

Owner: Claude (Opus) cloud thread "Review hard designs with Opus". Read-only review + fixes of clear bugs.

## Doing now
Done; PR open on claude/project-thread-ahsb4a.

## Facts found
- tools/jobsched.py Scheduler.gate: nested gate took a 2nd hub lease (waited 20 s on itself). Fixed.
- tools/jobsched.py _Both.checkpoint kept the hub lease while stepping aside locally. Fixed.
- tools/jobsched.py LeaseClient: HTTP 408 (hub busy) marked the hub down 30 s. Fixed.
- tools/jobsched.py _Resource.acquire: no wake-up for the next waiter when a slot stayed free (cpu, 4 slots). Fixed.
- main_python/hub_api_scheduler.py gate(): hub's own GPU-class work would lease from itself over HTTP. Fixed (lease=False).
- apps/voice/service.py watch_faq_audio: exclusive profile lock every 5 s blocked new questions. Now shared.
- Not fixed (findings): lease ttl 60 s has no renew; runlock takeover race + pid reuse; check_pool kill on Linux kills only the pid; isolate_data temp dir leaks on hard kill; #269 findings sent to scheduler thread.

## File status
| File | Change | State | Verification | Commit |
|---|---|---|---|---|
| tools/jobsched.py | 4 fixes | committed | check_job_scheduler(+_lease) green; new asserts fail on old code | this PR |
| main_python/hub_api_scheduler.py | lease=False | committed | check_job_scheduler_lease | this PR |
| apps/voice/service.py | watcher shared lock | committed | check_job_scheduler | this PR |
| qc/checks/check_job_scheduler.py | +3 asserts | committed | sabotage by reverting fixes: fail | this PR |
| qc/checks/check_job_scheduler_lease.py | +2 asserts | committed | same | this PR |
