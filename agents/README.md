Admin + 3 Workers scaffold

Start each component locally for testing:

- Admin:
  cd agents/admin
  python3 app.py

- Worker (each in own terminal):
  cd agents/worker_fetcher
  python3 app.py

  cd agents/worker_extractor
  python3 app.py

  cd agents/worker_planner
  python3 app.py

Notes:
- The admin exposes POST /task to queue tasks. Workers poll workspace/tasks.jsonl and append results to workspace/tasks_results.jsonl.
- Use scripts/setup_team.sh to create workspace and set permissions.
