from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from vision import analyze_image_nvidia, enhance_description_nemotron
import uvicorn, base64, os, time, hashlib
from typing import Optional
from utils import compress_image_base64

app = FastAPI(title="VisionBuddy API", version="1.0")

# Allow Flutter app to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# ─── Request/Response Models ───────────────────────────────────────

class AnalyzeRequest(BaseModel):
    image: str        # base64 encoded image from Flutter
    mode: str = "general"  # general | medicine | navigation | text | money
    force: bool = False
    question: Optional[str] = None

class AnalyzeResponse(BaseModel):
    description: str   # Text that Flutter will speak aloud
    mode: str
    success: bool
    should_speak: bool = True

# Globals for rate-limiting and frame-change detection
last_request_time: float = 0.0
last_frame_hash: str = ""
COOLDOWN_SECONDS: float = 2.0
success: bool

# ─── Routes ────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "VisionBuddy is running! 👁️"}

@app.get("/health")
def health():
    return {"status": "healthy", "nvidia": "connected"}

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_image(request: AnalyzeRequest):
    global last_request_time, last_frame_hash

    now = time.time()

    # ── 1. RATE LIMIT — ignore if too soon (auto mode) ────
    if not request.force and not request.question:
        if now - last_request_time < COOLDOWN_SECONDS:
            return AnalyzeResponse(
                description="",
                should_speak=False,
                mode=request.mode,
                success=True
            )

    # ── 2. FRAME CHANGE DETECTION ─────────────────────────
    # Hash first 500 chars of image to detect if frame changed
    frame_hash = hashlib.md5(request.image[:500].encode()).hexdigest()
    
    if not request.force and not request.question:
        if frame_hash == last_frame_hash:
            return AnalyzeResponse(
                description="",
                should_speak=False,
                mode=request.mode,
                success=True
            )

    # Update trackers
    last_request_time = now
    last_frame_hash = frame_hash

    try:
        # ── 3. ANALYZE with vision model ──────────────────
        raw = analyze_image_nvidia(request.image, request.mode)

        # ── 4. If follow-up question, include it ──────────
        if request.question:
            enhanced = enhance_description_nemotron(
                f"Scene: {raw}\nUser asked: {request.question}",
                request.mode
            )
        else:
            enhanced = enhance_description_nemotron(raw, request.mode)

        return AnalyzeResponse(
            description=enhanced,
            should_speak=True,
            mode=request.mode,
            success=True
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# @app.post("/analyze", response_model=AnalyzeResponse)
# async def analyze_image(request: AnalyzeRequest):
#     try:
#         print(f"📸 Received image, mode: {request.mode}")
#         print(f"📏 Image size: {len(request.image)} chars")  # ← ADD

#         compressed = compress_image_base64(request.image, quality=60)
#         print(f"📏 Compressed size: {len(compressed)} chars")  # ← ADD

#         raw_description = analyze_image_nvidia(
#             compressed,
#             request.mode
#         )
#         print(f"👁️ Vision output: {raw_description}")  # ← ADD

#         final_description = enhance_description_nemotron(
#             raw_description,
#             request.mode
#         )
#         print(f"🧠 Final output: {final_description}")  # ← ADD

#         return AnalyzeResponse(
#             description=final_description,
#             mode=request.mode,
#             success=True
#         )
#     except Exception as e:
#         print(f"❌ FULL ERROR: {e}")
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=str(e))
# @app.post("/analyze", response_model=AnalyzeResponse)
# async def analyze_image(request: AnalyzeRequest):
#     try:
#         # Compress image first to reduce payload
#         compressed = compress_image_base64(request.image, quality=60)
#         raw_description = analyze_image_nvidia(
#             compressed,
#             # request.image,
#             request.mode
#         )
#         final_description = enhance_description_nemotron(
#             raw_description,
#             request.mode
#         )
#         return AnalyzeResponse(
#             description=final_description,
#             mode=request.mode,
#             success=True
#         )
#     except Exception as e:
#         print(f"❌ FULL ERROR: {e}")        # ← ADD THIS
#         import traceback
#         traceback.print_exc()               # ← ADD THIS
#         raise HTTPException(status_code=500, detail=str(e))
    
# @app.post("/analyze", response_model=AnalyzeResponse)
# async def analyze_image(request: AnalyzeRequest):
#     """
#     Main endpoint — Flutter sends base64 image, 
#     we return a description to speak aloud
#     """
#     try:
#         # Step 1: NVIDIA NIM Vision analyzes the image
#         raw_description = analyze_image_nvidia(
#             request.image,
#             request.mode
#         )
        
#         # Step 2: Nemotron makes it conversational for audio
#         final_description = enhance_description_nemotron(
#             raw_description,
#             request.mode
#         )
        
#         return AnalyzeResponse(
#             description=final_description,
#             mode=request.mode,
#             success=True
#         )
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/quick", response_model=AnalyzeResponse)  
async def analyze_quick(request: AnalyzeRequest):
    """
    Faster endpoint — skips Nemotron enhancement
    Use this if running out of time at hackathon
    """
    try:
        description = analyze_image_nvidia(request.image, request.mode)
        return AnalyzeResponse(
            description=description,
            mode=request.mode,
            success=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)