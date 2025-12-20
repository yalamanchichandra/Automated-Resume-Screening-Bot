import os
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.requests import Request
import shutil
from typing import List
from utils import preprocessing

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

os.makedirs("uploads", exist_ok=True)

def save_file(file: UploadFile, folder: str):
   os.makedirs(folder, exist_ok=True)
   save_path = os.path.join(folder, file.filename)
   with open(save_path, "wb") as f:
       shutil.copyfileobj(file.file, f)
   return save_path
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
   return templates.TemplateResponse("index.html", {"request": request})
@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
   request: Request,
   role_name: str = Form(...),
   jd_text: str = Form(""),
   jd_file: UploadFile = File(None),
   resumes: List[UploadFile] = File(...)
):
   
   role_folder = os.path.join("uploads", role_name)
   os.makedirs(role_folder, exist_ok=True)
   
   if jd_file:
       jd_path = save_file(jd_file, role_folder)
       with open(jd_path, "r", encoding="utf-8") as f:
           jd_text = f.read()
   
   saved_resumes = []
   for resume in resumes[:10]:
       path = save_file(resume, role_folder)
       saved_resumes.append(resume.filename)
   
   processed_jd = preprocessing.preprocess_text(jd_text)
   processed_resumes = [preprocessing.preprocess_text(open(os.path.join(role_folder, r), "r", encoding="utf-8").read()) for r in saved_resumes]
   
   results = [{"name": r, "score": "Pending", "details": "Processing to be added"} for r in saved_resumes]
   return templates.TemplateResponse("results.html", {
       "request": request,
       "role_name": role_name,
       "results": results
   })