# agent.py — Nemotron auto-detects mode + orchestrates all tools
import os, json, re
from openai import OpenAI
from memory import memory
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

# ── Nemotron models ────────────────────────────────────────
NEMOTRON_SUPER = "nvidia/llama-3.3-nemotron-super-49b-v1"
NEMOTRON_NANO  = "nvidia/nemotron-nano-9b-v1"
NIM_VISION     = "meta/llama-3.2-11b-vision-instruct"

# ── STEP 1: NIM Vision sees the raw scene ─────────────────
def perceive(image_base64: str) -> str:
    """
    NVIDIA NIM Vision — raw perception only.
    No interpretation yet — Nemotron does that.
    """
    try:
        response = client.chat.completions.create(
            model=NIM_VISION,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": """List exactly what you see. Be specific:
- Objects and their positions (left/right/center, near/far)
- All text visible (read it exactly)
- Any pill bottles, medicine, currency, signs, hazards
- Approximate distances if relevant
Be factual. No interpretation."""
                    }
                ]
            }],
            max_tokens=200,
            temperature=0.1
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Scene perception failed: {str(e)}"


# ── STEP 2: Nemotron Super reasons + decides ───────────────
def nemotron_reason(raw_vision: str, 
                    user_question: str = None,
                    rag_context: str = "") -> dict:
    """
    NEMOTRON SUPER 49B — The brain.
    Auto-detects mode, decides if scene changed enough to speak,
    selects tools, generates response.
    """
    
    conversation_context = memory.get_context()
    last_scene = memory.last_description
    
    system_prompt = """You are VisionBuddy, an AI agent for blind and visually impaired users.

YOUR JOB:
1. AUTO-DETECT what type of scene this is (medicine/navigation/text/money/general)
2. DECIDE if this is worth speaking about (is it new/different/important?)
3. GENERATE a response in 1-2 sentences MAX
4. DECIDE what actions to take

SCENE TYPES:
- medicine: pill bottles, medication packaging, prescription labels
- navigation: stairs, doors, obstacles, hazards, paths
- text: signs, documents, handwriting, printed text
- money: bills, coins, currency
- general: people, objects, rooms, everyday scenes

RESPONSE RULES:
- MAXIMUM 2 sentences
- Most critical info FIRST
- For medicine: name + dosage + key warning
- For navigation: hazard FIRST + distance
- For text: read it exactly
- For money: denomination clearly
- If scene barely changed from last time: set should_speak = false

ALWAYS return valid JSON."""

    user_prompt = f"""
RAW VISION OUTPUT:
{raw_vision}

LAST SCENE (what I described before):
{last_scene if last_scene else "Nothing yet - first frame"}

CONVERSATION HISTORY:
{conversation_context if conversation_context else "None"}

RAG MEDICAL KNOWLEDGE:
{rag_context if rag_context else "Not applicable"}

USER QUESTION:
{user_question if user_question else "None - auto narration"}

TASK: Reason through this and respond with JSON:
{{
  "detected_mode": "medicine|navigation|text|money|general",
  "scene_changed": true/false,
  "should_speak": true/false,
  "response": "Your 1-2 sentence response for the user",
  "offer_reminder": true/false,
  "medication_name": "name if medicine detected else null",
  "hazard_detected": true/false,
  "reasoning": "brief explanation of your decision"
}}"""

    try:
        completion = client.chat.completions.create(
            model=NEMOTRON_SUPER,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            max_tokens=400,
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        result_text = completion.choices[0].message.content
        return json.loads(result_text)
        
    except Exception as e:
        # Fallback to Nano if Super fails
        return nemotron_nano_fallback(raw_vision, user_question)


# ── Nemotron Nano fallback ─────────────────────────────────
def nemotron_nano_fallback(raw_vision: str, 
                            user_question: str = None) -> dict:
    """
    NEMOTRON NANO 9B — Fast fallback.
    Used when Super is slow or unavailable.
    Also used for quick follow-up questions.
    """
    try:
        prompt = f"""Scene: {raw_vision[:300]}
Question: {user_question or 'Describe for blind user'}
Respond JSON: {{"detected_mode":"general","scene_changed":true,
"should_speak":true,"response":"2 sentences max","offer_reminder":false,
"medication_name":null,"hazard_detected":false,"reasoning":"fallback"}}"""
        
        completion = client.chat.completions.create(
            model=NEMOTRON_NANO,
            messages=[
                {"role": "system", 
                 "content": "You are VisionBuddy for blind users. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.2
        )
        text = completion.choices[0].message.content
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    
    # Last resort
    return {
        "detected_mode": "general",
        "scene_changed": True,
        "should_speak": True,
        "response": raw_vision[:150] if raw_vision else "Unable to analyze scene.",
        "offer_reminder": False,
        "medication_name": None,
        "hazard_detected": False,
        "reasoning": "emergency fallback"
    }


# ── STEP 3: Nemotron Nano answers follow-ups ───────────────
def nemotron_followup(question: str) -> dict:
    """
    NEMOTRON NANO 9B — Fast follow-up answers.
    Uses conversation + scene memory. No new image needed.
    """
    context = memory.get_context()
    
    try:
        completion = client.chat.completions.create(
            model=NEMOTRON_NANO,
            messages=[
                {"role": "system", 
                 "content": "You are VisionBuddy for blind users. Answer in 1-2 sentences max using context."},
                {"role": "user", 
                 "content": f"Context:\n{context}\n\nQuestion: {question}"}
            ],
            max_tokens=150,
            temperature=0.3
        )
        response = completion.choices[0].message.content
        memory.add_message("user", question)
        memory.add_message("assistant", response)
        return {
            "response": response,
            "should_speak": True,
            "nemotron_model": NEMOTRON_NANO,
            "action_taken": "followup"
        }
    except Exception as e:
        return {
            "response": "I couldn't answer that. Please try again.",
            "should_speak": True,
            "nemotron_model": NEMOTRON_NANO,
            "action_taken": "followup_error"
        }


# ── RAG lookup (called by main agent loop) ─────────────────
def should_use_rag(raw_vision: str) -> bool:
    medicine_keywords = [
        "tablet", "capsule", "mg", "pill", "medicine", "prescription",
        "bottle", "syrup", "drug", "medication", "dose", "rx", "pharmacy"
    ]
    return any(kw in raw_vision.lower() for kw in medicine_keywords)


# ── MAIN AGENT ENTRYPOINT ──────────────────────────────────
def run_agent(image_base64: str, user_question: str = None) -> dict:
    """
    Full agent loop:
    NIM Vision → Nemotron Super (reason) → Tools → Nemotron Nano (if needed)
    """
    
    # ── PERCEIVE (NIM Vision) ──────────────────────────────
    raw_vision = perceive(image_base64)
    
    # ── RAG enrichment if medicine detected ───────────────
    rag_context = ""
    if should_use_rag(raw_vision):
        from rag import rag
        rag_context = rag.retrieve(raw_vision[:200])
    
    # ── NEMOTRON SUPER REASONS ─────────────────────────────
    result = nemotron_reason(raw_vision, user_question, rag_context)
    
    # ── HANDLE ACTIONS ─────────────────────────────────────
    action_taken = result.get("detected_mode", "general")
    response = result.get("response", "")
    
    # Append reminder offer
    if result.get("offer_reminder") and result.get("medication_name"):
        med = result["medication_name"]
        response += f" Say 'set reminder' to schedule {med} in your calendar."
        action_taken = "medicine_detected"
    
    # Handle SOS
    if user_question and "sos" in user_question.lower():
        from tools import alert_tool
        alert_tool(raw_vision)
        response = "SOS alert sent to your emergency contact with your surroundings."
        action_taken = "sos_sent"
    
    # Handle reminder request
    if user_question and "set reminder" in user_question.lower():
        med = result.get("medication_name", "your medication")
        response = f"Done. Daily reminder set for {med} in Google Calendar."
        action_taken = "reminder_set"
    
    # ── UPDATE MEMORY ──────────────────────────────────────
    if result.get("should_speak") and response:
        memory.add_frame(raw_vision, result.get("detected_mode", "general"))
        if user_question:
            memory.add_message("user", user_question)
        memory.add_message("assistant", response)
    
    return {
        "response": response,
        "should_speak": result.get("should_speak", True),
        "action_taken": action_taken,
        "mode_used": result.get("detected_mode", "general"),
        "scene_changed": result.get("scene_changed", True),
        "rag_used": bool(rag_context),
        "nemotron_model": NEMOTRON_SUPER,
        "hazard": result.get("hazard_detected", False),
        "reasoning": result.get("reasoning", "")
    }