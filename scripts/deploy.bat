@echo off
REM Deploy clude to Cloud Run (docs/web.md, "Deploying a new version").
REM Runs from any directory: the repo root is this script's parent.
REM Names the account and the project on the command, since Orbit's
REM active gcloud configuration is often another project's.
REM
REM The secrets and env vars are the service's whole configuration:
REM   FLASK_SECRET_KEY      the session secret (Secret Manager)
REM   ANTHROPIC_API_KEY     the workspace-scoped key for LLM seats (8.3a)
REM   CLUDE_WEB_LLM_BUDGET  dollars a table may spend on the model
REM   CLUDE_WEB_LLM_DAILY_CAP  dollars the service may spend a day
REM   CLUDE_MCP_SECRET      the path segment the MCP endpoint is mounted under (Phase 9)

pushd "%~dp0.."
gcloud run deploy clude --source . --region us-central1 ^
    --service-account clude-run@clude-game.iam.gserviceaccount.com ^
    --allow-unauthenticated --min-instances 0 --max-instances 1 --concurrency 8 ^
    --cpu 1 --memory 1Gi --timeout 300 ^
    --set-env-vars "CLUDE_WEB_HTTPS=1,CLUDE_WEB_STORE=gs://clude-game-data/llm,CLUDE_WEB_LLM_BUDGET=2.00,CLUDE_WEB_LLM_DAILY_CAP=10.00" ^
    --set-secrets "FLASK_SECRET_KEY=clude-flask-secret:latest,ANTHROPIC_API_KEY=clude-anthropic-key:latest,CLUDE_MCP_SECRET=clude-mcp-secret:latest" ^
    --quiet --account=clude-sa@clude-game.iam.gserviceaccount.com --project=clude-game
set RESULT=%ERRORLEVEL%
popd
exit /b %RESULT%
