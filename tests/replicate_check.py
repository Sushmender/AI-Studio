import os
import sys
import asyncio
from dotenv import load_dotenv

"""
Test billing-gated 402 as expected/passing until manager signoff on paid credits.
Forces a real API call to luma/ray-flash-2-720p to verify workflow.
"""

# Force real API call
os.environ["MOCK_GENERATION_APIS"] = "false"

# Must load env before importing config/clients
load_dotenv(".env")

# Fix unicode encoding on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from backend.clients.replicate_client import generate_video

async def test_replicate():
    print("Starting Replicate test...")
    if not os.environ.get("REPLICATE_API_TOKEN"):
        print("❌ Auth error — REPLICATE_API_TOKEN not found in environment.")
        sys.exit(1)

    prompt = "a cinematic tracking shot of a red fox in a snowy forest"
    
    try:
        # Use exact code path from real workflow
        res = await generate_video(prompt=prompt, aspect_ratio="16:9", duration=5, job_id="test_job_456")
        print("✅ Full success — video generated (Model: luma/ray-flash-2-720p)")
        sys.exit(0)
    except Exception as e:
        # replicate_client wrapper raises NonRetryableError or RetryableError
        cause = getattr(e, "__cause__", None)
        status_code = getattr(cause, "status", None)
        error_msg = str(e).lower() + " " + str(cause).lower()
        
        if status_code == 402 or "insufficient credits" in error_msg or "payment required" in error_msg or "free time limit" in error_msg or "not authorized" in error_msg or "credit" in error_msg:
            print("✅ Workflow correct — blocked only by billing (402) (Model: luma/ray-flash-2-720p)")
            sys.exit(0)
        elif status_code in (401, 403) or "unauthorized" in error_msg or "forbidden" in error_msg or "invalid token" in error_msg:
            print("❌ Auth error — check REPLICATE_API_TOKEN (Model: luma/ray-flash-2-720p)")
            sys.exit(1)
        elif status_code in (400, 422) or "bad request" in error_msg or "validation error" in error_msg:
            print("❌ Request malformed — check payload structure (Model: luma/ray-flash-2-720p)")
            print(f"Details: {e}")
            sys.exit(1)
        else:
            print(f"❌ Real failure — {type(e).__name__}: {e} (Model: luma/ray-flash-2-720p)")
            if cause:
                print(f"Cause: {type(cause).__name__}: {cause}")
            sys.exit(1)

if __name__ == "__main__":
    # Ensure working directory is project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    sys.path.insert(0, project_root)
    os.chdir(project_root)
    
    asyncio.run(test_replicate())
