# Project conventions for hackathon 101

Several developers are building this project in parallel, each with their own assistant on their own laptop, from one repository.
These are the working conventions for everyone, including you.

1. Your own assignment is in `.kode/TASK.md` in your working folder. Read it and the contract files it lists before writing code.
   The contract files define the shared interfaces and are frozen: do not edit them.
2. Only create or edit the files listed as yours in TASK.md. Teammates own everything else; edits elsewhere are reverted automatically.
3. Commit sensibly: a small task is one clear commit; bigger work commits at natural steps, as many as it needs. Messages like `feat(api): add GET /ideas`. No padding commits, no giant mixed ones.
4. Work on your task branch only, never on `main`. Push it with `git push -u origin <your-branch>` after your first commit and again at the end.
5. Work on your own: the team lead is not available for questions during the task. If something is unclear, follow the contract and pick the simplest sensible option.
6. When everything is committed and pushed, print one line `KODE_DONE <number of commits>` so the lead's dashboard can see that you finished.
7. If your agent has skills or plugins installed (testing, code review, security review, frontend design, debugging), use the ones that fit your task: TASK.md lists the relevant ones. Prefer them to improvising.
8. You are one long-lived session that may be given several tasks one after another: finish each task completely, then wait for the next one; never start other sessions or sub-agents unless the task needs them.
