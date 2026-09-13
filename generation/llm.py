"""Client gọi Groq (cloud, free tier). Hỗ trợ stream để trả lời mượt."""
from groq import Groq

from config import settings
from generation.prompts import SYSTEM, build_user_prompt

_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        if not settings.GROQ_API_KEY:
            raise RuntimeError(
                "Chưa có GROQ_API_KEY. Tạo file .env (xem .env.example) "
                "và lấy key free tại https://console.groq.com/keys"
            )
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


def complete(system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
    """Gọi Groq một lượt (không stream), trả về text. Dùng cho query-rewrite v.v."""
    resp = _get_client().chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return (resp.choices[0].message.content or "").strip()


def answer(question: str, chunks: list[dict], stream: bool = True):
    """Sinh câu trả lời từ câu hỏi + chunk ngữ cảnh.

    stream=True -> generator yield từng mẩu text; False -> trả về str.
    """
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": build_user_prompt(question, chunks)},
    ]
    client = _get_client()
    if not stream:
        resp = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=settings.LLM_TEMPERATURE,
        )
        return resp.choices[0].message.content

    def _gen():
        s = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=settings.LLM_TEMPERATURE,
            stream=True,
        )
        for chunk in s:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    return _gen()
