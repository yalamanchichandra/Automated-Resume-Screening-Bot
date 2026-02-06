import os
import time
import shutil
import re
from typing import List

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from processing.cleaner import clean_text
from processing.hasher import get_hash
from processing.resume_loader import load_resume_text
from processing.tfidf import compute_tfidf_similarity

from llm.hf_runner import run_llm
from llm.prompts import (
    JD_STRUCTURING_PROMPT,
    RESUME_STRUCTURING_PROMPT,
    SCORING_PROMPT
)

from db.database import (
    init_db,
    save_jd,
    save_resume,
    save_score,
    get_score_by_jd_and_resume
)

from config import GROQ_MODEL


# --------------------------------------------------
# FASTAPI SETUP
# --------------------------------------------------
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# --------------------------------------------------
# INIT DB
# --------------------------------------------------
init_db()


# --------------------------------------------------
# 🔥 MODEL WARM-UP (SAFE)
# --------------------------------------------------
print("Warming up model...")
try:
    run_llm("Say READY", "ping", 5)
except Exception:
    pass


# --------------------------------------------------
# ROUTES
# --------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    request: Request,
    jd_text: str = Form(...),
    resumes: List[UploadFile] = File(...)
):
    results = []

    # --------------------------------------------------
    # 📄 JD PROCESSING
    # --------------------------------------------------
    jd_clean = clean_text(jd_text)
    jd_hash = get_hash(jd_clean)

    try:
        jd_structured = run_llm(
            JD_STRUCTURING_PROMPT,
            jd_clean,
            max_tokens=300
        )
    except Exception:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "JD structuring failed"}
        )

    save_jd(
        jd_hash=jd_hash,
        raw_text=jd_clean,
        structured_text=jd_structured
    )

    time.sleep(2)

    # --------------------------------------------------
    # 📑 RESUME PROCESSING
    # --------------------------------------------------
    for file in resumes:
        filename = file.filename
        print(f"Analyzing {filename}")

        try:
            file_path = os.path.join(UPLOAD_DIR, filename)
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)

            resume_raw = load_resume_text(file_path)
            resume_clean = clean_text(resume_raw)
            resume_hash = get_hash(resume_clean)

        except Exception as e:
            print(f"Skipping {filename}: read_failed | {e}")
            continue

        # ---------- Resume Structuring ----------
        try:
            resume_structured = run_llm(
                RESUME_STRUCTURING_PROMPT,
                resume_clean,
                max_tokens=450
            )
        except Exception as e:
            print(f"Skipping {filename}: structuring_failed | {e}")
            continue

        save_resume(
            resume_hash=resume_hash,
            filename=filename,
            raw_text=resume_clean,
            structured_text=resume_structured
        )

        time.sleep(2)

        # ---------- TF-IDF Similarity (LOGGING ONLY) ----------
        tfidf_similarity = compute_tfidf_similarity(
            jd_clean,
            resume_clean
        )

        save_score(
            jd_hash=jd_hash,
            resume_hash=resume_hash,
            score_type="tfidf",
            score_value=tfidf_similarity,
            remarks="TF-IDF cosine similarity"
        )

        # ---------- LLM Scoring ----------
        score = 0
        reason = "LLM scoring failed"

        existing_score = get_score_by_jd_and_resume(jd_hash, resume_hash, "llm")

        if existing_score:
            score = existing_score["score_value"]
            reason = existing_score["remarks"]
            print(f"✅ Using cached LLM score: {score}")
        else:
            try:
                score_text = run_llm(
                    SCORING_PROMPT,
                    "JOB REQUIREMENTS:\n"
                    + jd_structured
                    + "\n\nCANDIDATE PROFILE:\n"
                    + resume_structured,
                    max_tokens=200
                )

                # ---------- 🔧 FIXED: ROBUST SCORE + REASON EXTRACTION ----------
                score_match = re.search(r"\b(1[5-9]|[2-8][0-9]|90)\b", score_text)

                if score_match:
                    score = int(score_match.group(1))
                    reason = score_text[score_match.end():].strip()
                else:
                    score = 15
                    reason = score_text.strip()

                score = min(90, max(15, score))
                # ---------------------------------------------------------------

                save_score(
                    jd_hash=jd_hash,
                    resume_hash=resume_hash,
                    score_type="llm",
                    score_value=score,
                    remarks=reason,
                    model_name=GROQ_MODEL
                )

            except Exception as e:
                print(f"LLM scoring failed for {filename}: {e}")

        results.append({
            "name": filename,
            "score": score,
            "similarity": tfidf_similarity,
            "reason": reason
        })

        print("--------------------------------------------------")
        print(f"Resume     : {filename}")
        print(f"LLM Score  : {score}")
        print(f"TF-IDF %   : {tfidf_similarity}")
        print(f"Reason     : {reason}")
        print("--------------------------------------------------\n")

        time.sleep(2)

    # --------------------------------------------------
    # FINAL SORT (LLM SCORE FIRST, TF-IDF AS TIEBREAKER)
    # --------------------------------------------------
    results.sort(
        key=lambda x: (x["score"], x["similarity"]),
        reverse=True
    )

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "jd_summary": jd_structured,
            "results": results
        }
    )