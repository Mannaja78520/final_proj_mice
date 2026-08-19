"""The suite itself must not fail for reasons that are not the code under test.

Every browser check reports its result back over one fake serial port, from
JavaScript, with fetch. That report used to be fire-and-forget: a bare
`.catch(function(){})` around the fetch. Under load — several browser checks in
one run, Edge starting slowly, many marks arriving at once on a port that takes
one caller at a time — a report could simply be dropped, and the check then
failed with "measurements missing" or "the driver never reported".

That is the worst kind of failure. It points at code that is fine, it moves
around between runs, and `promote.py` is gated on the suite, so it blocks work
that is actually finished. Observed on 2026-08-18: three separate full runs
failed on three DIFFERENT browser checks, each of which passed on its own.

So a mark retries, and this drives that against a hostile network: the page's
fetch is made to fail its first two attempts, and every mark must still arrive.
"""
import browser
import fake_serial
import qc as F

AREA = "qc"
TITLE = "a browser check cannot fail because a report was dropped"
SLOW = True

MARKS = 6

# Fail the first two fetches the page makes, then let them through. If qcMark
# gives up on the first refusal, the marks it lost never arrive and the counts
# below do not add up — which is exactly the flake, reproduced on purpose.
PAGE = """
<script>
(function(){
  var real = window.fetch.bind(window), n = 0;
  window.fetch = function(u, o){
    if (++n <= 2) return Promise.reject(new Error("dropped on purpose"));
    return real(u, o);
  };
})();
window.addEventListener("load", async function(){
  for (var i = 1; i <= %d; i++) await qcMark("R" + i);
  qcMark("done");
});
</script>
""" % MARKS


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()

    browser.raw_page(PAGE, base, seconds=25)

    got = [m for m in fake_serial.qc_marks if m.startswith("R")]
    t.eq(len(got), MARKS,
         "every report arrived even though the first two were refused")
    for i in range(1, MARKS + 1):
        t.ok(("R%d" % i) in got, "report R%d survived the drop" % i)
    t.ok("done" in fake_serial.qc_marks,
         "and the page still says it finished",
         "without done the runner waits the full timeout on every check")
