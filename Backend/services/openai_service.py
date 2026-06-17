import os
import httpx

IDEOGRAM_API_URL = "https://api.ideogram.ai/generate"
ASPECT_RATIO = "ASPECT_16_9"

STYLE_MAP = {
    "bold_dramatic": "REALISTIC",
    "clean_minimal": "DESIGN",
    "vibrant_energetic": "VIBRANT",
}

STYLE_PROMPTS = {
    "bold_dramatic": (
        "Cinematic high-contrast lighting. Deep shadows, punchy highlights. "
        "Dramatic facial expression with intense emotion. Strong foreground presence. "
        "Moody color grade — deep blues, oranges, reds. "
        "Composition: subject dominates 60% of frame, offset slightly left or right. "
        "Atmosphere: high stakes, tension, urgency."
    ),
    "clean_minimal": (
        "Modern, polished editorial aesthetic. Generous negative space. "
        "Limited palette: 2–3 colors maximum. Crisp, sharp details. "
        "Soft even lighting — no harsh shadows. "
        "Composition: balanced, breathing room around subject. "
        "Premium brand feel. Clean background — solid color or very subtle gradient."
    ),
    "vibrant_energetic": (
        "Bright, saturated colors. High energy, lively composition. "
        "Bold color contrast — complementary hues. Slight motion blur or dynamic diagonal lines. "
        "Subject looks confident and excited. "
        "Composition: subject large in frame, slightly angled for dynamism. "
        "Upbeat, clickable, fast-paced feel."
    ),
}

NEGATIVE_PROMPT = (
    "blurry, low resolution, pixelated, distorted face, extra limbs, "
    "deformed hands, ugly, watermark, logo, signature, text artifacts, "
    "bad anatomy, duplicate subjects, cluttered background, washed out colors, "
    "overexposed, underexposed, amateur, poorly lit"
)


def build_thumbnail_prompt(user_prompt: str, style_name: str, headshot_url: str | None) -> str:
    style_block = STYLE_PROMPTS.get(style_name, STYLE_PROMPTS["bold_dramatic"])

    user_lower = user_prompt.lower()
    has_text_request = any(
        kw in user_lower for kw in ["text", "write", "title", "label", "word", '"', "'"]
    )

    text_guidance = ""
    if has_text_request:
        text_guidance = (
            f"\n[TEXT OVERLAY]\n"
            f"Render the following text exactly as specified by the user inside the image. "
            f"Use a bold, legible font. Ensure high contrast between text and background.\n"
            f"User text instruction: {user_prompt}\n"
        )

    prompt = (
        f"[SUBJECT]\n"
        f"A real person shown clearly and prominently in the thumbnail. "
        f"{'Person shown in the reference image provided. Preserve exact facial features, skin tone, hair, and likeness. Do NOT alter the persons appearance.' if headshot_url else 'Charismatic presenter or host looking directly at camera.'}\n\n"
        f"[CONTENT PURPOSE]\n"
        f"YouTube video thumbnail. 16:9 aspect ratio. Designed to maximize click-through rate.\n"
        f"User's core instruction: {user_prompt}\n"
        f"{text_guidance}"
        f"\n[VISUAL STYLE]\n"
        f"{style_block}\n\n"
        f"[TECHNICAL REQUIREMENTS]\n"
        f"- Subject face must be sharp, well-lit, and clearly visible\n"
        f"- No watermarks or logos in the image itself\n"
        f"- Background should complement subject, not overpower\n"
        f"- Composition must not feel cropped or awkward\n"
        f"- Image must look intentional and designed, not AI-generated\n"
    )

    return prompt.strip()


async def generate_thumbnail(
    prompt: str,
    style_name: str,
    headshot_url: str | None = None,
) -> bytes:
    """Generate a YouTube thumbnail using Ideogram v2.

    Args:
        prompt:       User's natural language instruction
        style_name:   One of: bold_dramatic | clean_minimal | vibrant_energetic
        headshot_url: URL of person's reference headshot (optional)

    Returns:
        Raw image bytes (PNG/JPEG)
    """

    api_key = os.getenv("IDEOGRAM_API_KEY")
    if not api_key:
        raise RuntimeError(
            "IDEOGRAM_API_KEY not set in environment. "
            "Add it to your .env file."
        )

    full_prompt = build_thumbnail_prompt(prompt, style_name, headshot_url)
    ideogram_style = STYLE_MAP.get(style_name, "REALISTIC")

    payload = {
        "image_request": {
            "prompt": full_prompt,
            "negative_prompt": NEGATIVE_PROMPT,
            "aspect_ratio": ASPECT_RATIO,
            "model": "V_2",
            "style_type": ideogram_style,
            "magic_prompt_option": "AUTO",
            "num_images": 1,
        }
    }

    if headshot_url:
        payload["image_request"]["image_weight"] = 40
        payload["image_request"]["image_url"] = headshot_url

    headers = {
        "Api-Key": api_key,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                IDEOGRAM_API_URL,
                json=payload,
                headers=headers,
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"Ideogram API error {response.status_code}: {response.text[:300]}"
                )

            data = response.json()
            image_url = data["data"][0]["url"]

            img_response = await client.get(image_url)
            if img_response.status_code != 200:
                raise RuntimeError(
                    f"Failed to download generated image: {img_response.status_code}"
                )

            return img_response.content

    except httpx.TimeoutException:
        raise RuntimeError("Ideogram API timed out after 90 seconds. Try again.")
    except httpx.RequestError as e:
        raise RuntimeError(f"Network error calling Ideogram API: {str(e)}")
    except KeyError as e:
        raise RuntimeError(f"Unexpected Ideogram response structure. Missing key: {e}")