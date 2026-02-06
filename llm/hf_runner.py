import time
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is missing. Please set it in config.py")

client = Groq(api_key=GROQ_API_KEY)


def run_llm(prompt: str, content: str, max_tokens: int = 300) -> str:
    """
    Unified LLM call wrapper for Groq.
    Handles retries, trimming, and safe output parsing.
    """

    if not prompt or not content:
        raise ValueError("Empty prompt or content sent to LLM")

    combined_content = (
        prompt.strip() + "\n\n" + content.strip()
    )

    combined_content = combined_content[:12000]

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": combined_content
                    }
                ],
                temperature=0,
                max_tokens=min(max_tokens, 300)
            )

            if not response.choices:
                raise RuntimeError("Groq returned empty choices")

            output = response.choices[0].message.content
            if not output:
                raise RuntimeError("Groq returned empty content")

            return output.strip()

        except Exception as e:
            print(f"⏳ Groq retry {attempt + 1}/3 due to: {e}")
            time.sleep(2 * (attempt + 1))

    raise RuntimeError("Groq request failed after 3 retries")
