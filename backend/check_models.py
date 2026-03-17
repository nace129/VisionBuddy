# Save as check_models.py in backend folder and run it
from openai import OpenAI
import os
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

models = client.models.list()
for m in models.data:
    print(m.id)