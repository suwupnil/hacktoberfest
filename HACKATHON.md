# HACKATHON.md
 
## Team name
Zig2
 
## Team members
Swapnil Pradhan (@suwupnil)
Akshat Kumar (@akshat-xe)
 
## Problem statement
### Problem 2: Evidence-Based Open Source Issue and Pull Request Triage (Triage that tests the claims)
Open-source maintainers receive large volumes of bug reports, security reports, and pull requests.
Unfortunately, many reports contain incorrect assumptions, fabricated issues, misleading descriptions, or claims that cannot be reproduced.
Reviewing such submissions consumes valuable maintainer time and slows down the development of legitimate contributions.
The challenge is not identifying whether a report was written by a human or AI. The real challenge is determining whether the technical claims made in the report are actually true.
 
## Models we use and why
- clef-flash (by Cloudflare): This is decisions model that is trained for raw decision making processes efficiently without overloading the main working agent.
- qwen3.5:9b (by Meta): This is a large language model that is trained for reasoning and understanding complex technical claims. It can analyze the content of bug reports and pull requests to determine the validity of the claims made.
