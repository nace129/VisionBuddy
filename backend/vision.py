from openai import OpenAI
import os, base64
def _simple_load_dotenv(dotenv_path="../.env"):
    try:
        with open(dotenv_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
    except FileNotFoundError:
        # no .env file present; that's fine
        pass

_simple_load_dotenv()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

# Shared prompts used by vision analysis functions
prompts = {
    "general": """You are VisionBuddy, an AI assistant for blind and visually impaired people.
            Describe what you see clearly and concisely in 2-3 sentences.
            Mention: objects present, their positions (left/right/center/near/far),
            any text visible, potential hazards, and anything urgent.
            Speak directly to the user as if guiding them.""",
    
    "medicine": """You are VisionBuddy helping a blind person identify medication.
            Read ALL text on this medicine bottle or packaging.
            State: medication name, dosage, instructions, expiry date, warnings.
            If you cannot read something clearly, say so explicitly.""",
    
    "navigation": """You are VisionBuddy helping a blind person navigate safely.
            Focus on: obstacles ahead, stairs, doors, signs, distances.
            Use directions like 'directly ahead', '2 feet to your left', 'behind you'.
            Warn about hazards FIRST before describing other things.""",
    
    "text": """You are VisionBuddy helping a blind person read text.
            Read ALL text visible in this image exactly as written.
            Include signs, labels, handwriting, printed text, prices, dates.
            Preserve the reading order (top to bottom, left to right).""",
    
    "money": """You are VisionBuddy helping a blind person identify currency.
            Identify the denomination and currency type of any bills or coins visible.
            State the total value if multiple bills/coins are present.
            Be very precise — this is critical for the user."""
}

def analyze_image_nvidia(image_base64: str, mode: str = "general") -> str:
    try:
        response = client.chat.completions.create(
            model="nvidia/nemotron-nano-12b-v2-vl",  # ✅ NVIDIA native vision
            messages=[
                {
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
                            "text": prompts.get(mode, prompts["general"])
                        }
                    ]
                }
            ],
            max_tokens=300,
            temperature=0.3
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"❌ Vision error: {e}")
        # Fallback to backup vision model
        try:
            response = client.chat.completions.create(
                model="nvidia/llama-3.1-nemotron-nano-vl-8b-v1",  # ✅ backup
                messages=[
                    {
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
                                "text": prompts.get(mode, prompts["general"])
                            }
                        ]
                    }
                ],
                max_tokens=300,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e2:
            return f"Unable to analyze image: {str(e2)}"


def enhance_description_nemotron(raw_description: str, mode: str = "general") -> str:
    try:
        response = client.chat.completions.create(
            model="nvidia/llama-3.3-nemotron-super-49b-v1",  # ✅ FIXED
            messages=[
                {
                    "role": "system",
                    "content": """You are VisionBuddy, a compassionate AI assistant 
                    for blind users. Take the raw scene description and rewrite it as 
                    warm, clear, natural spoken audio — like a trusted friend describing 
                    the scene. Keep it under 3 sentences. Remove technical language.
                    Start with the most important thing first."""
                },
                {
                    "role": "user",
                    "content": f"Raw description: {raw_description}"
                }
            ],
            max_tokens=200,
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Nemotron error: {e}")
        return raw_description  # fallback to raw if Nemotron fails
    

# def encode_image_to_base64(image_path: str) -> str:
#     """Convert image file to base64 string"""
#     with open(image_path, "rb") as f:
#         return base64.b64encode(f.read()).decode("utf-8")

# def analyze_image_nvidia(image_base64: str, mode: str = "general") -> str:
#     """
#     Send image to NVIDIA NIM vision model
#     Modes: general | medicine | navigation | text | money
#     """
    
#     prompts = {
#         "general": """You are VisionBuddy, an AI assistant for blind and visually impaired people.
#             Describe what you see clearly and concisely in 2-3 sentences.
#             Mention: objects present, their positions (left/right/center/near/far),
#             any text visible, potential hazards, and anything urgent.
#             Speak directly to the user as if guiding them.""",
        
#         "medicine": """You are VisionBuddy helping a blind person identify medication.
#             Read ALL text on this medicine bottle or packaging.
#             State: medication name, dosage, instructions, expiry date, warnings.
#             If you cannot read something clearly, say so explicitly.""",
        
#         "navigation": """You are VisionBuddy helping a blind person navigate safely.
#             Focus on: obstacles ahead, stairs, doors, signs, distances.
#             Use directions like 'directly ahead', '2 feet to your left', 'behind you'.
#             Warn about hazards FIRST before describing other things.""",
        
#         "text": """You are VisionBuddy helping a blind person read text.
#             Read ALL text visible in this image exactly as written.
#             Include signs, labels, handwriting, printed text, prices, dates.
#             Preserve the reading order (top to bottom, left to right).""",
        
#         "money": """You are VisionBuddy helping a blind person identify currency.
#             Identify the denomination and currency type of any bills or coins visible.
#             State the total value if multiple bills/coins are present.
#             Be very precise — this is critical for the user."""
#     }
    
#     try:
#         response = client.chat.completions.create(
#             model="nvidia/neva-22b",  # NVIDIA vision model
#             messages=[
#                 {
#                     "role": "user",
#                     "content": [
#                         {
#                             "type": "image_url",
#                             "image_url": {
#                                 "url": f"data:image/jpeg;base64,{image_base64}"
#                             }
#                         },
#                         {
#                             "type": "text",
#                             "text": prompts.get(mode, prompts["general"])
#                         }
#                     ]
#                 }
#             ],
#             max_tokens=300,
#             temperature=0.3  # Low = more factual, less creative
#         )
#         return response.choices[0].message.content
        
#     except Exception as e:
#         return f"I'm having trouble analyzing the image right now. Error: {str(e)}"


# def enhance_description_nemotron(raw_description: str, mode: str = "general") -> str:
#     """
#     Optional: Pass raw vision output through Nemotron 
#     to make it more natural and conversational for audio
#     """
    
#     system_prompt = """You are VisionBuddy, a compassionate AI assistant 
#     for blind users. Take the raw scene description and rewrite it as 
#     warm, clear, natural spoken audio — like a trusted friend describing 
#     the scene. Keep it under 3 sentences. Remove technical language.
#     Start with the most important thing first."""
    
#     response = client.chat.completions.create(
#         model="nvidia/llama-3.3-nemotron-super-49b-v1",
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": f"Raw description: {raw_description}"}
#         ],
#         max_tokens=200,
#         temperature=0.5
#     )
#     return response.choices[0].message.content