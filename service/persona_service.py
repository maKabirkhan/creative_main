from openai import OpenAI
import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()
logger = logging.getLogger(__name__)


class PersonaService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")
        self.openai_client = OpenAI(api_key=api_key)
    
    def create_persona(self, user_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate persona data, insights, and reach all in one AI call"""

        missing_fields = []
        if not input_data.get("life_stage"):
            missing_fields.append("life_stage")
        if not input_data.get("category_involvement"):
            missing_fields.append("category_involvement")
        if not input_data.get("decision_making_style"):
            missing_fields.append("decision_making_style")
        gender_value = input_data.get('gender', [])
        if isinstance(gender_value, list):
            gender_display = ", ".join(gender_value) if gender_value else "Any"
        else:
            gender_display = gender_value if gender_value else "Any"
        
        prompt = f"""
            You are a senior audience research analyst. 
            Your role is to analyze the provided audience profile and generate structured, insight-driven data.  
            If some attributes (life_stage, category_involvement, decision_making_style) are missing, infer them logically from the context provided. Never leave them empty.  

            ### Audience Profile:
            - Audience Type: {input_data.get('audience_type')}
            - Geography: {input_data.get('geography')}
            - Age Range: {input_data.get('age_min')} - {input_data.get('age_max')}
            - Income Range: {input_data.get('income_min')} - {input_data.get('income_max')}
            - Gender: {gender_display}
            - Interests: {input_data.get('interests')}
            - Purchase Frequency: {input_data.get('purchase_frequency')}
            - Life Stage: {input_data.get('life_stage')}
            - Category Involvement: {input_data.get('category_involvement')}
            - Decision Making Style: {input_data.get('decision_making_style')}

            ### Instructions for generation:

            1. **Generated Fields**  
            - Only infer values if missing in the input.  
            - If already provided, retain the given values.  
            - Base assumptions on age, interests, income, and purchase frequency.  
            Example: A 22-year-old student with low income may map to "life_stage": "Student", "category_involvement": "Low", "decision_making_style": "Price-conscious".

            2. **Audience Insights**  
            - Provide a concise label that captures the audience’s efficiency or defining trait (e.g., "Tech-Savvy Young Adults").  
            - Recommend 3–4 online platforms where this audience is most reachable.  
            - Suggest their peak online activity time.  
            - Propose the most effective engagement style (e.g., short-form video, long-form article, visual-first).  

            3. **Estimated Reach**  
            - Provide a realistic audience size range (with commas).  
            - Justify the estimate with a one-sentence rationale based on geography, age, and interests.  

            4. **Performance Scores**  
            - Assign each score on a scale of 1 to 10, where 10 indicates excellent alignment.  
            - Ratings must be grounded in the provided audience profile and insights.  
            - Definitions:  
                - **clarity** → How clearly the audience’s needs and behaviors are defined.  
                - **relevance** → How relevant the profile is to the category/brand context.  
                - **distinctiveness** → How unique this audience segment is compared to others.  
                - **brand_fit** → How well the audience aligns with a potential brand positioning.  
                - **emotion** → The extent to which emotional drivers influence this audience.  
                - **cta** → Strength of likely response to clear calls-to-action.  
                - **inclusivity** → How inclusive and representative the segment is across demographics.  

            ### Output Requirements:
            Return **only valid JSON** in the following structure:

            {{
            "generated_fields": {{
                "life_stage": "string",
                "category_involvement": "string",
                "decision_making_style": "string"
            }},
            "audience_insights": {{
                "efficiency": "string",
                "platforms": ["string", "string", "string"],
                "peak_activity": "string",
                "engagement": "string"
            }},
            "estimated_reach": {{
                 "min": "integer (with commas allowed for readability)",
                 "max": "integer (with commas allowed for readability)",
                "description": "string"
            }},
            "performance_scores": {{
                "clarity": number,
                "relevance": number,
                "distinctiveness": number,
                "brand_fit": number,
                "emotion": number,
                "cta": number,
                "inclusivity": number
            }}
            }}
            """

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a structured data generator for market research. Always return valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            content = response.choices[0].message.content.strip()
            content = self._clean_response(content)

            ai_output = json.loads(content)

            response = {
                "message": "Audience analysis completed successfully",
                "user_id": user_id,
                "audience_insights": ai_output.get("audience_insights", {}),
                "estimated_reach": ai_output.get("estimated_reach", {}),
                "performance_scores": ai_output.get("performance_scores", {}),
                "created_at": datetime.utcnow().isoformat()
            }


            logger.info(f"Generated persona for user {user_id}")
            return response

        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            return {
                "message": "Audience analysis failed, fallback values used",
                "user_id": user_id,
                "generated_fields": {
                    "life_stage": input_data.get("life_stage") or "General",
                    "category_involvement": input_data.get("category_involvement") or "Medium",
                    "decision_making_style": input_data.get("decision_making_style") or "Balanced"
                },
                "audience_insights": {
                    "efficiency": "General Consumers",
                    "platforms": ["Facebook", "Instagram"],
                    "peak_activity": "Evenings",
                    "engagement": "Mixed content"
                },
                "estimated_reach": {
                    "range": "100,000 - 200,000",
                    "description": "Default reach estimate (fallback)"
                },
                "created_at": datetime.utcnow().isoformat()
            }

    def _clean_response(self, content: str) -> str:
        """Clean up OpenAI response"""
        if content.startswith('```json'):
            content = content.replace('```json', '').replace('```', '').strip()
        elif content.startswith('```'):
            content = content.replace('```', '').strip()
        return content
