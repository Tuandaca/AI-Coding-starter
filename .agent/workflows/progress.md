---
description: Update project progress in CONTEXT.md
---

1. Read `.agent/CONTEXT.md`
2. Ask user: "What have you completed recently?" (if not provided in prompt)
3. Ask user: "What is your next focus?" (if not provided in prompt)
4. Update `CONTEXT.md`:
   - Mark completed items in "Completed Features"
   - Update "Current Focus"
   - Add new items to "Completed Features" if they weren't checked
   - Update "Last Updated" date
5. Show the updated sections to user for confirmation
