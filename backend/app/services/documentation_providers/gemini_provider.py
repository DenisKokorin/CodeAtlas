import httpx
from fastapi import HTTPException


GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


async def generate_gemini_documentation(
    prompt: str,
    api_key: str,
    model: str,
    max_output_tokens: int,
) -> str:
    url = f"{GEMINI_API_URL}/{model}:generateContent"
    params = {"key": api_key}
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": max_output_tokens,
            "temperature": 0.3,
        },
    }

    timeout = httpx.Timeout(25.0, connect=8.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, params=params, json=payload)

        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Gemini API is unavailable. Try again later.",
        ) from exc

    data = response.json()
    candidates = data.get("candidates") or []

    for candidate in candidates:
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        text_parts = [
            part.get("text", "")
            for part in parts
            if part.get("text")
        ]

        if text_parts:
            return "\n".join(text_parts).strip()

    raise HTTPException(
        status_code=502,
        detail="Gemini API returned an empty documentation response.",
    )
