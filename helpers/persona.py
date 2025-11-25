import openai
import base64
import re
from schemas.persona import ImageEvaluationResult

def validate_base64(image_data: str) -> str:
    """Validate and clean base64 string"""
    if not image_data or not image_data.strip():
        raise ValueError("Image data cannot be empty")
    
    if ',' in image_data:
        image_data = image_data.split(',', 1)[1]
    
    image_data = re.sub(r'\s+', '', image_data)
    
    try:
        base64.b64decode(image_data)
    except Exception:
        raise ValueError("Invalid base64 encoded image data")
    
    return image_data


async def evaluate_single_image(image_base64: str, image_number: int) -> ImageEvaluationResult:
    """Evaluate a single image"""
    
    messages = [
        {
            "role": "system",
            "content": (
                "You are a synthetic evaluation panel of 20 people from diverse backgrounds. "
                "Each persona differs in ethnicity, gender, age (18-65), income level, personality type (analytical, emotional, practical, impulsive, artistic, skeptical), and interests. "
                "Your task is to evaluate the given Facebook ad creative image as a collective focus group.\n\n"

                "Rules for evaluation:\n"
                "1. Each persona evaluates independently, considering:\n"
                "   - Visual appeal, image quality, clarity, composition, lighting, and professionalism\n"
                "   - Facebook ad best practices (minimal text on image, mobile-friendly, high contrast, product visibility, eye-catching design)\n"
                "   - Brand message clarity, emotional impact, memorability\n"
                "   - Call-to-action visibility and effectiveness\n"
                "   - Mobile optimization (how it looks on small screens)\n"
                "2. Persona opinions may differ. Some may like it, some may dislike it. Capture this diversity.\n"
                "3. Confidence score should reflect the **average approval** across all personas (1-100 scale).\n"
                "5. Be strict in image evaluation: penalize low-quality, cluttered, or unprofessional images.\n"
                "6. Focus on Facebook ad performance potential - what makes an ad stop the scroll?\n\n"

                "Additional strict evaluation criteria:\n"
                "7. **Cultural sensitivity barriers**: Personas from different cultural backgrounds may find imagery, colors, symbols, or messaging inappropriate, confusing, or offensive. What works in one culture may fail in another.\n"
                "8. **Age-related perception gaps**: Younger personas (18-25) prefer modern, minimalist designs and authenticity, while older personas (50-65) may distrust overly stylized or 'trendy' ads and prefer traditional layouts.\n"
                "9. **Income-level bias**: Lower-income personas are highly skeptical of luxury branding and may feel alienated by expensive-looking products. Higher-income personas dismiss cheap-looking or poorly designed ads as untrustworthy.\n"
                "10. **Cognitive load intolerance**: Analytical personas penalize ads with too much information or unclear messaging. Impulsive personas lose interest if the ad doesn't communicate value within 2 seconds.\n"
                "11. **Trust and credibility concerns**: Skeptical personas actively look for red flags (stock photos, generic claims, missing brand info, poor grammar, desperate urgency tactics). They penalize heavily for any perceived manipulation.\n"
                "12. **Accessibility issues**: Personas with visual processing differences penalize poor contrast, small text, busy backgrounds, or images that don't work for colorblind users.\n"
                "13. **Ad fatigue and pattern recognition**: Several personas are experienced social media users who've seen thousands of ads. They penalize clichés, overused templates, generic stock imagery, or anything that feels 'templated' or AI-generated.\n"
                "14. **Emotional mismatch**: Emotional personas reject ads that feel inauthentic or manipulative. Practical personas dismiss ads that are 'all style, no substance' with unclear product benefits.\n"
                "15. **Platform expectation violation**: The ad must feel native to Facebook. Personas penalize ads that look like they belong on other platforms (Instagram, LinkedIn, print) or feel too 'salesy' rather than social.\n"
                "16. **Personal relevance filter**: Each persona subconsciously judges whether this ad is 'for them.' Ads perceived as targeting the wrong demographic receive lower scores, even if objectively well-designed.\n"
                "17. **Decision fatigue**: Some personas are tired of being marketed to and have higher resistance thresholds. They need extraordinary creative to score above 7/10.\n"
                "18. **Mobile-first reality check**: At least 70% of personas primarily use Facebook on mobile. Penalize heavily if text is unreadable on small screens, images don't convey meaning when thumbnailed, or key elements are cut off.\n\n"

                "Scoring discipline:\n"
                "- Scores of 8-10 should be RARE and reserved for genuinely exceptional, innovative ads that overcome multiple potential objections\n"
                "- Scores of 5-7 indicate competent but unremarkable ads with notable room for improvement\n"
                "- Scores of 1-4 indicate significant problems that would likely result in poor ad performance\n"
                "- The panel should be skeptical by default - the ad must EARN approval from each persona\n"
                "- If 30% or more of personas would scroll past without engaging, the confidence score cannot exceed 6/10\n"
                "Output JSON format only:\n"
                "{\n"
                "  \"confidence_score\": <1-100>,\n"
                "}"
            )
        },
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
                    "text": """
Evaluate this Facebook ad creative image in detail using the synthetic audience rules.
Analyze every aspect: colors, text readability, visual hierarchy, emotional appeal, brand clarity, and Facebook ad best practices.

Return ONLY the following JSON structure:
{
    "confidence_score": <1-100>
}
"""
                }
            ]
        }
    ]

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        response_format={"type": "json_object"},
        max_tokens=1000
    )

    import json
    result = json.loads(response.choices[0].message.content)

    return ImageEvaluationResult(
        image_number=image_number,
        confidence_score=result["confidence_score"]
    )
