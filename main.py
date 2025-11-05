# main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from solver import solve_quiz
import os
import time
import logging

# ========== CONFIGURATION ==========
SECRET = os.getenv("QUIZ_SECRET", "your_secret_here")  # set via .env for safety
MAX_WORKERS = 3                                        # concurrent quizzes
QUIZ_TIMEOUT_SECONDS = 180                             # must finish within 3 mins
# ===================================

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


@app.post("/")
async def handle_quiz_request(request: Request):
    """Main entrypoint — handles quiz POST requests."""
    start_time = time.time()

    # Step 1: Parse JSON
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    email = payload.get("email")
    secret = payload.get("secret")
    url = payload.get("url")

    # Step 2: Validate required fields
    if not email or not secret or not url:
        raise HTTPException(status_code=400, detail="Missing email, secret, or url")

    # Step 3: Validate secret
    if secret != SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    # Step 4: Define async wrapper to run sync code (Selenium, pandas, etc.)
    loop = asyncio.get_event_loop()

    def run_solver():
        logger.info(f"🚀 Received new quiz request from {email}")
        logger.info(f"🔗 URL: {url}")
        result = solve_quiz(email=email, secret=secret, url=url)
        return result

    # Step 5: Run solver in thread executor with timeout (3 min)
    try:
        result = await asyncio.wait_for(loop.run_in_executor(executor, run_solver), timeout=QUIZ_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        logger.error("⏰ Quiz solving exceeded 3-minute limit.")
        raise HTTPException(status_code=504, detail="Quiz solving timed out")
    except Exception as e:
        logger.exception("❌ Unexpected error while solving quiz")
        raise HTTPException(status_code=500, detail=str(e))

    elapsed = round(time.time() - start_time, 2)
    logger.info(f"✅ Quiz solved in {elapsed}s → Result: {result}")

    # Step 6: Return JSON response to evaluator
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "time_taken_sec": elapsed,
            "result": result
        }
    )


# Optional root GET route
@app.get("/")
def home():
    return {"message": "LLM Analysis Quiz API running successfully 🚀"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
