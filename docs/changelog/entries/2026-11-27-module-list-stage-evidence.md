---
date: 2026-11-27
kind: improved
prs: -
area: qc
title: check_one_module_list prints where the page's time went when the Home sentence is missing
---
Problem: check_one_module_list failed in busy full runs with "'4 modules' not found in ''" and nothing said why (green alone, and 40 of 40 with 10 copies at once).
Method: the page now marks each stage (loaded, rows ready, before and after each scan) with milliseconds since load, and a new assertion says whether the page reached the Home sentence at all and shows those stages, so the next crowd failure explains itself. The Home sentence itself is never empty in the page (it always says counting / looking / no modules / N modules), so an empty read means the page did not get that far.
Numbers: the check passes alone (16 s).
