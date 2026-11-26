---
date: 2026-11-27
kind: new
prs: -
area: tooling
title: The PC assistant keeps itself running; usage limits fall back to Codex, Gemini 4 Argon and small-step Gemini
---
Problem: the remote-control session dropped and came back with unfinished work, and someone had to type the start command by hand each time; a usage limit left the work stuck.
Method: double-click "Start PC Assistant" (and "Stop PC Assistant"): a low-priority check every 3 minutes keeps one session running, restarts it if it lost its connection or stopped writing its heartbeat, never touches other Claude windows, backs off after 3 starts an hour, and removes itself when the PC shuts down, restarts or you log in again. A new session is told which tasks are still "Doing now". At a usage limit the existing AI watcher hands the work on in order: GPT Codex, Gemini 4 Argon (full), regular Gemini (small steps only), one AI at a time, back to Claude when it is free.
Numbers: how to use and turn it off: docs/pc_assistant.md. Not turned on by the change itself; you start it with the .bat.
