---
date: 2026-11-23
kind: new
prs: 208, 210, 212, 213, 222, 224
area: cameras
title: One camera system, one owner, apps run alone
---
Problem: ESP32-CAM, USB and network cameras each had their own path; two apps could fight for one webcam; apps needed the hub to run.
Method: One camera registry and one route; the first app claims a camera under its real name and shares the stream; every app got --alone and peer discovery so alone and together both work; busy-webcam message names the likely cause in 4 languages.
