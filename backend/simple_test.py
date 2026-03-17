# from openai import OpenAI
# import os

# def _simple_load_dotenv(dotenv_path="../.env"):
#     try:
#         with open(dotenv_path, "r") as f:
#             for line in f:
#                 line = line.strip()
#                 if not line or line.startswith("#"):
#                     continue
#                 if "=" in line:
#                     key, val = line.split("=", 1)
#                     key = key.strip()
#                     val = val.strip().strip('"').strip("'")
#                     if key and key not in os.environ:
#                         os.environ[key] = val
#     except FileNotFoundError:
#         pass

# _simple_load_dotenv()

# print("API Key loaded:", "Yes" if os.getenv("NVIDIA_API_KEY") else "No")

# client = OpenAI(
#     base_url="https://integrate.api.nvidia.com/v1",
#     api_key=os.getenv("NVIDIA_API_KEY")
# )

# print("Client created successfully")

# try:
#     print("Making API request...")
#     response = client.chat.completions.create(
#         model="nvidia/llama-3.1-nemotron-70b-instruct",
#         messages=[{"role": "user", "content": "Say hello in one word."}],
#         max_tokens=10
#     )
#     print("✅ Success:", response.choices[0].message.content)

# except Exception as e:
#     print("❌ Error:", str(e))
#     print("Error type:", type(e).__name__)


# Backend should already be running from Step 1
# Test the full analyze endpoint with a real image

# Quick Python test (run in new terminal)

from openai import OpenAI
import os, base64, requests

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
        pass

_simple_load_dotenv()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/280px-PNG_transparency_demonstration_1.png"

headers = {
    "User-Agent": "Mozilla/5.0"
}

r = requests.get(image_url, headers=headers, timeout=30)
r.raise_for_status()

with open("test.png", "wb") as f:
    f.write(r.content)

with open("test.png", "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode()

response = client.chat.completions.create(
    model="nvidia/nemotron-nano-12b-v2-vl",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_b64}"
                    }
                },
                {
                    "type": "text",
                    "text": "What do you see in this image in one sentence?"
                }
            ]
        }
    ],
    max_tokens=100
)

# Quick check script
client.chat.completions.create(
    model="nvidia/llama-3.3-nemotron-super-49b-v1",
    messages=[{"role": "user", "content": "Say hello"}],
    max_tokens=20
)
print("SUCESS 2")
print("SUCCESS:", response.choices[0].message.content)
