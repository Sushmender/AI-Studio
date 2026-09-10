import os
import sys
import asyncio
from dotenv import load_dotenv

"""
Test billing-gated 402 as expected/passing until manager signoff on paid credits.
Forces a real API call to fal-ai/flux/dev to verify workflow.
"""

# Force real API call
os.environ["MOCK_GENERATION_APIS"] = "false"

# Must load env before importing config/clients
load_dotenv(".env")

# Fix unicode encoding on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from backend.clients.fal_client import generate_image

async def test_fal():
    print("Starting fal.ai test...")
    if not os.environ.get("FAL_KEY"):
        print("❌ Auth error — FAL_KEY not found in environment.")
        sys.exit(1)

    prompt = "a red fox sitting in a snowy forest, cinematic lighting"
    
    try:
        # Use exact code path from real workflow
        res = await generate_image(prompt=prompt, width=1024, height=1024, num_inference_steps=28, job_id="test_job_123")
        print("✅ Full success — image generated (Model: fal-ai/flux/dev)")
        sys.exit(0)
    except Exception as e:
        # fal_client wrapper raises NonRetryableError or RetryableError
        cause = getattr(e, "__cause__", None)
        status_code = getattr(cause, "status_code", None)
        error_msg = str(e).lower() + " " + str(cause).lower()
        
        if status_code == 402 or "insufficient credits" in error_msg or "payment required" in error_msg or "top_up" in error_msg:
            print("✅ Workflow correct — blocked only by billing (403) (Model: fal-ai/flux/dev)")
            sys.exit(0)
        elif status_code in (401, 403) or "unauthorized" in error_msg or "forbidden" in error_msg:
            print("❌ Auth error — check FAL_KEY (Model: fal-ai/flux/dev)")
            sys.exit(1)
        elif status_code in (400, 422) or "bad request" in error_msg or "validation error" in error_msg:
            print("❌ Request malformed — check payload structure (Model: fal-ai/flux/dev)")
            print(f"Details: {e}")
            sys.exit(1)
        else:
            print(f"❌ Real failure — {type(e).__name__}: {e} (Model: fal-ai/flux/dev)")
            if cause:
                print(f"Cause: {type(cause).__name__}: {cause}")
            sys.exit(1)

if __name__ == "__main__":
    # Ensure working directory is project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    sys.path.insert(0, project_root)
    os.chdir(project_root)
    
    asyncio.run(test_fal())
