# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from vision import analyze_image_nvidia
from agent import run_agent, nemotron_followup
import time, hashlib

app = FastAPI(title="VisionBuddy API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate limiting ─────────────────────────────────────────
last_request_time = 0
last_frame_hash = ""
COOLDOWN_SECONDS = 4

# ── Models ────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    image: str
    question: str = None
    force: bool = False

class QuestionRequest(BaseModel):
    question: str

# ── Routes ────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "VisionBuddy is running! 👁️"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    global last_request_time, last_frame_hash

    now = time.time()

    # Rate limit only auto scans
    if not request.force and not request.question:
        if now - last_request_time < COOLDOWN_SECONDS:
            return {
                "description": "",
                "should_speak": False,
                "action_taken": "rate_limited",
                "mode_used": "none"
            }

    # Frame change detection — only for auto scans
    frame_hash = hashlib.md5(request.image[:500].encode()).hexdigest()
    if not request.force and not request.question:
        if frame_hash == last_frame_hash:
            return {
                "description": "",
                "should_speak": False,
                "action_taken": "no_change",
                "mode_used": "none"
            }

    last_request_time = now
    last_frame_hash = frame_hash

    try:
        # ── FAST PATH: vision only (skip full agent for speed) ──
        if not request.question:
            description = analyze_image_nvidia(request.image, "general")
            if not description:
                description = "I can see your surroundings."
            return {
                "description": description,
                "should_speak": True,
                "action_taken": "general",
                "mode_used": "general",
                "hazard": False,
            }

        # ── FULL AGENT: when question asked ────────────────────
        result = run_agent(request.image, request.question)
        response_text = result.get("response", "")

        if not response_text:
            response_text = "I can see the scene but nothing specific to report."

        return {
            "description": response_text,
            "should_speak": True,
            "action_taken": result.get("action_taken", "general"),
            "mode_used": result.get("mode_used", "general"),
            "hazard": result.get("hazard", False),
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/question")
async def question_only(request: QuestionRequest):
    """Answer questions without image"""
    try:
        result = nemotron_followup(request.question)
        return {
            "answer": result.get("response", ""),
            "should_speak": True,
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
# # main.py
# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# import uvicorn, time, hashlib
# from agent import run_agent, nemotron_followup

# app = FastAPI(title="VisionBuddy API")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ── Rate limiting ─────────────────────────────────────────
# last_request_time = 0
# last_frame_hash = ""
# COOLDOWN_SECONDS = 4

# # ── Request models ────────────────────────────────────────
# class AnalyzeRequest(BaseModel):
#     image: str
#     question: str = None
#     force: bool = False

# class QuestionRequest(BaseModel):
#     question: str

# # ── Routes ────────────────────────────────────────────────
# @app.get("/")
# def root():
#     return {"status": "VisionBuddy is running! 👁️"}

# @app.get("/health")
# def health():
#     return {"status": "healthy"}

# @app.post("/analyze")
# async def analyze(request: AnalyzeRequest):
#     global last_request_time, last_frame_hash

#     now = time.time()

#     # Only rate limit AUTO scans — NEVER block manual taps
#     if not request.force and not request.question:
#         if now - last_request_time < COOLDOWN_SECONDS:
#             return {
#                 "description": "",
#                 "should_speak": False,
#                 "action_taken": "rate_limited",
#                 "mode_used": "none"
#             }

#     # Frame change only for auto — force=True always goes through
#     frame_hash = hashlib.md5(request.image[:500].encode()).hexdigest()
#     if not request.force and not request.question:
#         if frame_hash == last_frame_hash:
#             return {
#                 "description": "",
#                 "should_speak": False,
#                 "action_taken": "no_change",
#                 "mode_used": "none"
#             }

#     last_request_time = now
#     last_frame_hash = frame_hash

#     try:
#         result = run_agent(request.image, request.question)

#         response_text = result.get("response", "")

#         # ✅ Force should_speak=True for manual taps
#         should_speak = True if request.force else result.get("should_speak", True)

#         # ✅ If response empty, give fallback
#         if not response_text:
#             response_text = "I can see your surroundings but nothing notable to report."

#         return {
#             "description": response_text,
#             "should_speak": should_speak,
#             "action_taken": result.get("action_taken", "general"),
#             "mode_used": result.get("mode_used", "general"),
#             "hazard": result.get("hazard", False),
#             "rag_used": result.get("rag_used", False),
#         }

#     except Exception as e:
#         print(f"❌ Agent error: {e}")
#         raise HTTPException(status_code=500, detail=str(e))
# # @app.post("/analyze")
# # async def analyze(request: AnalyzeRequest):
# #     global last_request_time, last_frame_hash

# #     now = time.time()

# #     # ── Rate limit for auto scans ─────────────────────────
# #     if not request.force and not request.question:
# #         if now - last_request_time < COOLDOWN_SECONDS:
# #             return {
# #                 "description": "",
# #                 "should_speak": False,
# #                 "action_taken": "rate_limited",
# #                 "mode_used": "none"
# #             }

# #     # ── Frame change detection ────────────────────────────
# #     frame_hash = hashlib.md5(request.image[:500].encode()).hexdigest()

# #     if not request.force and not request.question:
# #         if frame_hash == last_frame_hash:
# #             return {
# #                 "description": "",
# #                 "should_speak": False,
# #                 "action_taken": "no_change",
# #                 "mode_used": "none"
# #             }

# #     last_request_time = now
# #     last_frame_hash = frame_hash

# #     try:
# #         # ── Run full agent loop ───────────────────────────
# #         # agent.py auto-detects mode, reasons, picks tools
# #         result = run_agent(request.image, request.question)

# #         return {
# #             "description": result.get("response", ""),
# #             "should_speak": result.get("should_speak", True),
# #             "action_taken": result.get("action_taken", "general"),
# #             "mode_used": result.get("mode_used", "general"),
# #             "hazard": result.get("hazard", False),
# #             "rag_used": result.get("rag_used", False),
# #             "reasoning": result.get("reasoning", "")
# #         }

# #     except Exception as e:
# #         print(f"❌ Agent error: {e}")
# #         raise HTTPException(status_code=500, detail=str(e))


# @app.post("/question")
# async def question_only(request: QuestionRequest):
#     """Answer questions without image — uses memory context"""
#     try:
#         result = nemotron_followup(request.question)
#         return {
#             "answer": result.get("response", ""),
#             "should_speak": True,
#             "success": True
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# if __name__ == "__main__":
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
# # from fastapi import FastAPI, HTTPException
# # from fastapi.middleware.cors import CORSMiddleware
# # from pydantic import BaseModel
# # from vision import analyze_image_nvidia, enhance_description_nemotron
# # import uvicorn, base64, os, time, hashlib
# # from typing import Optional
# # from utils import compress_image_base64

# # app = FastAPI(title="VisionBuddy API", version="1.0")

# # # Allow Flutter app to call this API
# # app.add_middleware(
# #     CORSMiddleware,
# #     allow_origins=["*"],
# #     allow_methods=["*"],
# #     allow_headers=["*"],
# # )
# # # ─── Request/Response Models ───────────────────────────────────────

# # class AnalyzeRequest(BaseModel):
# #     image: str        # base64 encoded image from Flutter
# #     mode: str = "general"  # general | medicine | navigation | text | money
# #     force: bool = False
# #     question: Optional[str] = None

# # class AnalyzeResponse(BaseModel):
# #     description: str   # Text that Flutter will speak aloud
# #     mode: str
# #     success: bool
# #     should_speak: bool = True

# # # Globals for rate-limiting and frame-change detection
# # last_request_time: float = 0.0
# # last_frame_hash: str = ""
# # COOLDOWN_SECONDS: float = 2.0
# # success: bool

# # # ─── Routes ────────────────────────────────────────────────────────

# # @app.get("/")
# # def root():
# #     return {"status": "VisionBuddy is running! 👁️"}

# # @app.get("/health")
# # def health():
# #     return {"status": "healthy", "nvidia": "connected"}

# # @app.post("/analyze", response_model=AnalyzeResponse)
# # async def analyze_image(request: AnalyzeRequest):
# #     global last_request_time, last_frame_hash

# #     now = time.time()

# #     # ── 1. RATE LIMIT — ignore if too soon (auto mode) ────
# #     if not request.force and not request.question:
# #         if now - last_request_time < COOLDOWN_SECONDS:
# #             return AnalyzeResponse(
# #                 description="",
# #                 should_speak=False,
# #                 mode=request.mode,
# #                 success=True
# #             )

# #     # ── 2. FRAME CHANGE DETECTION ─────────────────────────
# #     # Hash first 500 chars of image to detect if frame changed
# #     frame_hash = hashlib.md5(request.image[:500].encode()).hexdigest()
    
# #     if not request.force and not request.question:
# #         if frame_hash == last_frame_hash:
# #             return AnalyzeResponse(
# #                 description="",
# #                 should_speak=False,
# #                 mode=request.mode,
# #                 success=True
# #             )

# #     # Update trackers
# #     last_request_time = now
# #     last_frame_hash = frame_hash

# #     try:
# #         # ── 3. ANALYZE with vision model ──────────────────
# #         raw = analyze_image_nvidia(request.image, request.mode)

# #         # ── 4. If follow-up question, include it ──────────
# #         if request.question:
# #             enhanced = enhance_description_nemotron(
# #                 f"Scene: {raw}\nUser asked: {request.question}",
# #                 request.mode
# #             )
# #         else:
# #             enhanced = enhance_description_nemotron(raw, request.mode)

# #         return AnalyzeResponse(
# #             description=enhanced,
# #             should_speak=True,
# #             mode=request.mode,
# #             success=True
# #         )

# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=str(e))
    
# # # Add this to main.py after /analyze endpoint

# # class QuestionRequest(BaseModel):
# #     question: str

# # @app.post("/question")
# # async def answer_question(request: QuestionRequest):
# #     """Answer questions without needing an image"""
# #     try:
# #         response = client.chat.completions.create(
# #             model="nvidia/llama-3.3-nemotron-super-49b-v1",
# #             messages=[
# #                 {
# #                     "role": "system",
# #                     "content": "You are VisionBuddy, a helpful assistant for blind users. Answer in max 2 sentences."
# #                 },
# #                 {
# #                     "role": "user",
# #                     "content": request.question
# #                 }
# #             ],
# #             max_tokens=150,
# #             temperature=0.5
# #         )
# #         answer = response.choices[0].message.content
# #         return {"answer": answer, "success": True}
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=str(e))
# # # @app.post("/analyze", response_model=AnalyzeResponse)
# # # async def analyze_image(request: AnalyzeRequest):
# # #     try:
# # #         print(f"📸 Received image, mode: {request.mode}")
# # #         print(f"📏 Image size: {len(request.image)} chars")  # ← ADD

# # #         compressed = compress_image_base64(request.image, quality=60)
# # #         print(f"📏 Compressed size: {len(compressed)} chars")  # ← ADD

# # #         raw_description = analyze_image_nvidia(
# # #             compressed,
# # #             request.mode
# # #         )
# # #         print(f"👁️ Vision output: {raw_description}")  # ← ADD

# # #         final_description = enhance_description_nemotron(
# # #             raw_description,
# # #             request.mode
# # #         )
# # #         print(f"🧠 Final output: {final_description}")  # ← ADD

# # #         return AnalyzeResponse(
# # #             description=final_description,
# # #             mode=request.mode,
# # #             success=True
# # #         )
# # #     except Exception as e:
# # #         print(f"❌ FULL ERROR: {e}")
# # #         import traceback
# # #         traceback.print_exc()
# # #         raise HTTPException(status_code=500, detail=str(e))
# # # @app.post("/analyze", response_model=AnalyzeResponse)
# # # async def analyze_image(request: AnalyzeRequest):
# # #     try:
# # #         # Compress image first to reduce payload
# # #         compressed = compress_image_base64(request.image, quality=60)
# # #         raw_description = analyze_image_nvidia(
# # #             compressed,
# # #             # request.image,
# # #             request.mode
# # #         )
# # #         final_description = enhance_description_nemotron(
# # #             raw_description,
# # #             request.mode
# # #         )
# # #         return AnalyzeResponse(
# # #             description=final_description,
# # #             mode=request.mode,
# # #             success=True
# # #         )
# # #     except Exception as e:
# # #         print(f"❌ FULL ERROR: {e}")        # ← ADD THIS
# # #         import traceback
# # #         traceback.print_exc()               # ← ADD THIS
# # #         raise HTTPException(status_code=500, detail=str(e))
    
# # # @app.post("/analyze", response_model=AnalyzeResponse)
# # # async def analyze_image(request: AnalyzeRequest):
# # #     """
# # #     Main endpoint — Flutter sends base64 image, 
# # #     we return a description to speak aloud
# # #     """
# # #     try:
# # #         # Step 1: NVIDIA NIM Vision analyzes the image
# # #         raw_description = analyze_image_nvidia(
# # #             request.image,
# # #             request.mode
# # #         )
        
# # #         # Step 2: Nemotron makes it conversational for audio
# # #         final_description = enhance_description_nemotron(
# # #             raw_description,
# # #             request.mode
# # #         )
        
# # #         return AnalyzeResponse(
# # #             description=final_description,
# # #             mode=request.mode,
# # #             success=True
# # #         )
        
# # #     except Exception as e:
# # #         raise HTTPException(status_code=500, detail=str(e))

# # @app.post("/analyze/quick", response_model=AnalyzeResponse)  
# # async def analyze_quick(request: AnalyzeRequest):
# #     """
# #     Faster endpoint — skips Nemotron enhancement
# #     Use this if running out of time at hackathon
# #     """
# #     try:
# #         description = analyze_image_nvidia(request.image, request.mode)
# #         return AnalyzeResponse(
# #             description=description,
# #             mode=request.mode,
# #             success=True
# #         )
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=str(e))


# # if __name__ == "__main__":
# #     uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)


