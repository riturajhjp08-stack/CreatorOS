from flask import Blueprint, current_app, request, Response, stream_with_context
from flask_jwt_extended import jwt_required
import logging
import re
import json
from google import genai
from google.genai import types

from extensions import limiter
logger = logging.getLogger(__name__)

ai_bp = Blueprint("ai", __name__)


def _extract_hashtags(text):
    tags = re.findall(r"#([A-Za-z0-9_]+)", text or "")
    normalized = []
    seen = set()
    for tag in tags:
        value = f"#{tag.lower()}"
        if value not in seen:
            seen.add(value)
            normalized.append(value)
    return normalized[:20]


def _keywords_to_hashtags(prompt, platform):
    words = re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", (prompt or "").lower())
    stop = {
        "this", "that", "with", "from", "about", "into", "your", "have", "will", "what",
        "when", "where", "which", "while", "there", "their", "make", "just", "than", "then",
    }
    picks = []
    for word in words:
        if word in stop:
            continue
        if word not in picks:
            picks.append(word)
        if len(picks) >= 10:
            break
    if not picks:
        picks = ["creator", "content", "growth", "socialmedia", "marketing"]
    tags = [f"#{w}" for w in picks]
    if platform:
        tags.append(f"#{platform.lower().replace('/', '').replace(' ', '')}")
    return tags[:15]


def _fallback_response(task, prompt, platform, tone, mode=None):
    platform_txt = platform or "social media"
    tone_txt = tone or "engaging"
    prompt_txt = prompt or "creator growth"

    if task == "hashtags":
        tags = _keywords_to_hashtags(prompt_txt, platform_txt)
        return {"text": " ".join(tags), "hashtags": tags}

    if task == "ideas":
        ideas = [
            f"3 myths about {prompt_txt} most creators still believe",
            f"Behind-the-scenes: how I plan {platform_txt} content for 30 days",
            f"Beginner-to-pro roadmap for {prompt_txt}",
            f"Mistakes I made in {prompt_txt} and how to avoid them",
            f"Fast workflow: create, edit, publish {platform_txt} content in 1 hour",
        ]
        return {"text": "\n".join(f"- {idea}" for idea in ideas), "ideas": ideas}

    if task == "virality":
        score = 72
        analysis = (
            "Strong topic relevance, but improve first-line hook, add a clearer CTA, "
            "and include one concrete benefit in the first 120 characters."
        )
        return {"text": analysis, "score": score, "analysis": analysis}

    if task == "trends":
        trends = [
            {"title": "AI workflow breakdowns", "meta": "Tech · +310% this week", "score": 9.2},
            {"title": "Short-form storytelling", "meta": "Creator Economy · +275%", "score": 8.9},
            {"title": "Build in public milestones", "meta": "Business · +241%", "score": 8.5},
            {"title": "Creator pricing transparency", "meta": "Marketing · +198%", "score": 8.2},
            {"title": "One-person content systems", "meta": "Productivity · +176%", "score": 7.8},
        ]
        tags = _keywords_to_hashtags(prompt_txt, platform_txt)
        text = "\n".join(f"- {item['title']} ({item['meta']})" for item in trends)
        return {"text": text, "trends": trends, "hashtags": tags}

    if task == "optimize":
        text = (
            f"{prompt_txt}\n\n"
            f"Save this for later and follow for more {platform_txt} playbooks."
        )
        return {"text": text}

    if task == "caption":
        text = (
            f"{prompt_txt}\n\n"
            f"If this helped, drop a comment and share with one creator.\n"
            f"#creatortips #{platform_txt.lower().replace('/', '').replace(' ', '')}"
        )
        return {"text": text, "hashtags": _extract_hashtags(text)}

    # writer default (dynamic so it does not repeat the same response)
    topic = prompt_txt[:140]
    mode_txt = (mode or "post").lower()
    hook_map = {
        "hook": f"Most creators overcomplicate {topic} and lose attention in 3 seconds.",
        "script": f"If you want better {platform_txt} results, stop posting random content about {topic}.",
        "thread": f"Thread: 5 hard truths about {topic} nobody tells creators.",
        "caption": f"Quick take on {topic} that can improve your next post today.",
    }
    hook_line = hook_map.get(mode_txt, f"Here is a smarter way to approach {topic} as a creator.")
    text = (
        f"Hook ({tone_txt}): {hook_line}\n\n"
        f"Body: For {platform_txt}, build content around one problem and one promise: {topic}. "
        f"Open strong, give one practical framework, and close with one clear action.\n\n"
        f"CTA: Comment 'TEMPLATE' and I will send a ready-to-use version."
    )
    return {"text": text}


def _call_gemini(messages, temperature=0.7, max_tokens=700):
    api_key = (current_app.config.get("GEMINI_API_KEY") or "").strip()
    enabled = bool(current_app.config.get("AI_ENABLED", True))
    if not enabled or not api_key:
        return None

    try:
        client = genai.Client(api_key=api_key)
        
        # Convert our {"role": "system"/"user", "content": ""} to what Gemini expects.
        # Gemini handles System Instructions natively in the API via configs.
        system_instruction = ""
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                system_instruction += msg["content"] + "\n"
            else:
                contents.append(msg["content"])
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction.strip() if system_instruction else None,
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        return (response.text or "").strip()
    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}")
        return None


def _build_prompt(task, prompt, platform, tone):
    system = (
        "You are CreatorOS AI. Write practical social content. "
        "Keep responses concise, concrete, and ready to publish."
    )
    user = (
        f"Task: {task}\n"
        f"Platform: {platform or 'general'}\n"
        f"Tone: {tone or 'balanced'}\n"
        f"User input: {prompt or ''}\n\n"
    )

    if task == "hashtags":
        user += "Return only hashtags separated by spaces. Provide 12-18 hashtags."
    elif task == "ideas":
        user += "Return 6 content ideas as a numbered list."
    elif task == "virality":
        user += (
            "Give a virality score out of 100 and a short improvement plan. "
            "Format first line exactly: SCORE: <number>."
        )
    elif task == "trends":
        user += "Return 5 trend ideas as numbered list with brief growth note."
    elif task == "optimize":
        user += "Rewrite and optimize this caption for engagement and clarity."
    elif task == "caption":
        user += "Write a high-performing caption and include 5-8 relevant hashtags."
    else:
        user += "Generate high-quality creator content for this request."

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


@ai_bp.route("/generate", methods=["POST"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_AI", "30 per hour"))
def generate_ai():
    payload = request.get_json(silent=True) or {}
    task = (payload.get("task") or "writer").strip().lower()
    prompt = (payload.get("prompt") or "").strip()
    platform = (payload.get("platform") or "").strip()
    tone = (payload.get("tone") or "").strip()
    mode = (payload.get("mode") or "").strip()

    if task not in {"writer", "caption", "hashtags", "ideas", "optimize", "virality", "trends"}:
        return {"error": "Invalid AI task"}, 400

    if task not in {"trends"} and not prompt:
        return {"error": "Prompt is required"}, 400

    try:
        messages = _build_prompt(task, prompt, platform, tone)
        model_text = _call_gemini(messages, temperature=0.7, max_tokens=800)
        provider = "gemini"
    except Exception:
        logger.exception("Gemini request failed, using fallback response")
        model_text = None
        provider = "fallback"

    if not model_text:
        fallback = _fallback_response(task, prompt, platform, tone, mode=mode)
        return {
            "ok": True,
            "provider": "fallback",
            "task": task,
            **fallback,
        }, 200

    result = {"text": model_text}

    if task == "hashtags":
        result["hashtags"] = _extract_hashtags(model_text) or _keywords_to_hashtags(prompt, platform)
    elif task == "ideas":
        lines = [re.sub(r"^\s*\d+[\).\-\s]*", "", line).strip() for line in model_text.splitlines()]
        ideas = [line for line in lines if line]
        result["ideas"] = ideas[:8]
    elif task == "virality":
        match = re.search(r"SCORE:\s*(\d{1,3})", model_text, flags=re.IGNORECASE)
        score = int(match.group(1)) if match else 70
        score = max(0, min(100, score))
        result["score"] = score
        result["analysis"] = model_text
    elif task in {"caption", "trends"}:
        result["hashtags"] = _extract_hashtags(model_text)

    return {
        "ok": True,
        "provider": provider,
        "task": task,
        **result,
    }, 200

@ai_bp.route("/chat", methods=["POST"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("RATELIMIT_AI", "30 per hour"))
def chat_ai():
    """Endpoint for the free-form Chat interface using streaming"""
    payload = request.get_json(silent=True) or {}
    history = payload.get("history", [])
    prompt = payload.get("prompt", "").strip()

    if not prompt:
        return {"error": "Prompt is required"}, 400

    api_key = (current_app.config.get("GEMINI_API_KEY") or "").strip()
    enabled = bool(current_app.config.get("AI_ENABLED", True))

    if not enabled or not api_key:
        return {"error": "AI features are currently disabled or missing API key."}, 503

    def generate():
        try:
            client = genai.Client(api_key=api_key)
            
            # Format history for Gemini
            contents = []
            for msg in history:
                role = "user" if msg.get("role") == "user" else "model"
                contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg.get("content", ""))]))
            
            # Add latest prompt
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))
            
            response = client.models.generate_content_stream(
                model='gemini-2.5-flash',
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction="You are CreatorOS AI, a helpful social media and creator assistant. Provide practical, concise advice."
                )
            )
            
            for chunk in response:
                if chunk.text:
                    yield f"data: {json.dumps({'text': chunk.text})}\n\n"
            
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Chat streaming error: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(stream_with_context(generate()), content_type='text/event-stream')
