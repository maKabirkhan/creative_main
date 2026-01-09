
from typing import List, Optional, Dict, Any
import json
import uuid
from datetime import datetime
import logging
from openai import OpenAI
import os
import base64
import requests
import cv2
import ffmpeg
import yt_dlp
import tempfile
import librosa
import numpy as np
import asyncio
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class SimulationService:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def create_simulation(self, user_id: str, request, user_tier) -> dict:
        """Create and run A/B simulation analysis with multiple creative assets"""
        try:
          
            start_time = datetime.now()
            simulation_id = str(uuid.uuid4())
            
            if hasattr(request, 'model_dump'):
                request_data = request.model_dump()
            elif hasattr(request, 'dict'):
                request_data = request.dict()
            else:
                request_data = request
            
            variant_a_task = self._process_variant_assets("variant_a", request_data['variant_a'])
            variant_b_task = self._process_variant_assets("variant_b", request_data['variant_b'])
            
            variant_a_data, variant_b_data = await asyncio.gather(
                variant_a_task, variant_b_task, return_exceptions=True
            )
            
            if isinstance(variant_a_data, Exception):
                logger.error(f"Variant A processing failed: {variant_a_data}")
                raise Exception(f"Variant A processing failed: {variant_a_data}")
            
            if isinstance(variant_b_data, Exception):
                logger.error(f"Variant B processing failed: {variant_b_data}")
                raise Exception(f"Variant B processing failed: {variant_b_data}")
            
            analysis_result = await self._generate_comparative_analysis(
                variant_a_data, variant_b_data, request_data, user_tier
            )

            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            analysis_result["simulation_id"] = simulation_id
            analysis_result["created_at"] = start_time.isoformat()
            analysis_result["processing_time"] = processing_time
            analysis_result["user_id"] = user_id
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in create_simulation: {str(e)}")
            raise e

    async def _process_variant_assets(self, variant_name: str, variant: dict) -> Dict[str, Any]:
        """Process all creative assets for a single variant"""
        try:
            creative_assets = variant.get('creative_assets', [])
            
            if not creative_assets:
                raise Exception(f"{variant_name} has no creative assets")
            
            tasks = [
                self._process_single_asset(asset) 
                for asset in creative_assets
            ]
            processed_assets = await asyncio.gather(*tasks, return_exceptions=True)  
            valid_assets = []
            for i, result in enumerate(processed_assets):
                if isinstance(result, Exception):
                    logger.warning(f"Asset {i} failed: {result}")
                else:
                    valid_assets.append(result)
            
            if not valid_assets:
                raise Exception(f"All assets in {variant_name} failed to process")
            
            return {
                "persona": variant.get('persona', {}),
                "processed_assets": valid_assets,
                "headline": variant.get('headline'),
                "title": variant.get('title'),
                "description": variant.get('description'),
                "asset_count": len(valid_assets)
            }
            
        except Exception as e:
            logger.error(f"Error processing {variant_name}: {str(e)}")
            raise e

    async def _process_single_asset(self, asset: dict) -> Dict[str, Any]:
        """Process a single creative asset"""
        try:
            asset_type = asset.get('type', '').upper()
            
            if asset_type == "IMAGE" and asset.get('file_url'):
                image_content = await self._download_image_content_async(asset['file_url'])
                return {
                    "id": asset.get('id'),
                    "type": "image",
                    "content": image_content,
                    "url": asset['file_url']
                }
                
            elif asset_type == "VIDEO" and asset.get('file_url'):
                loop = asyncio.get_event_loop()
                transcript, sample_frames, duration = await loop.run_in_executor(
                    self.executor, self._process_video_sync, asset['file_url']
                )
                return {
                    "id": asset.get('id'),
                    "type": "video",
                    "transcript": transcript,
                    "sample_frames": sample_frames,
                    "duration_seconds": duration,
                    "url": asset['file_url']
                }
                
            elif asset_type == "AUDIO" and asset.get('file_url'):
                loop = asyncio.get_event_loop()
                audio_analysis = await loop.run_in_executor(
                    self.executor, self._process_audio_sync, asset['file_url']
                )
                return {
                    "id": asset.get('id'),
                    "type": "audio",
                    "transcript": audio_analysis.get("transcript", ""),
                    "acoustic_features": audio_analysis.get("acoustic_features", {}),
                    "url": asset['file_url']
                }
                
            elif asset_type == "TEXT":
                return {
                    "id": asset.get('id'),
                    "type": "text",
                    "ad_copy": asset.get('ad_copy'),
                    "voice_script": asset.get('voice_script')
                }
                
            else:
                raise Exception(f"Unsupported asset type: {asset_type}")
                
        except Exception as e:
            logger.error(f"Error processing asset {asset.get('id')}: {str(e)}")
            raise e

    async def _generate_comparative_analysis(
        self, 
        variant_a: Dict[str, Any], 
        variant_b: Dict[str, Any],
        request_data: Dict[str, Any],
        user_tier: str
    ) -> Dict[str, Any]:
        """Generate AI-powered comparative analysis with 3 perspectives and extended metrics"""
        try:
           
            prompt = self._build_comparative_prompt(variant_a, variant_b, user_tier, request_data)
            
            messages = [
                {
                    "role": "system",
                    "content": """You are an expert creative strategist analyzing advertising assets from THREE distinct perspectives:

1. **Persona-Based Perspective** - Deep analysis through the lens of the defined target persona, incorporating their demographics, behaviors, preferences, platform habits, and psychological triggers.

2. **Creative Director Perspective** - Professional industry evaluation focusing on creative quality, strategic effectiveness, brand alignment, and campaign optimization.

3. **General Audience Perspective** - Unbiased viewpoint representing everyday people without specialized knowledge or persona constraints. This reflects how the average person scrolling social media would naturally react.

Your analysis must:
- Treat all assets collectively as a unified campaign
- Provide distinct insights from each perspective
- Use realistic scores based on actual marketing effectiveness
- Give actionable, specific feedback
- Sound like multiple voices, not a single narrator
- Evaluate comprehensive metrics including clarity, brand linkage, distinctiveness, emotional response, and execution craft
- Generate detailed research-style data including emotional engagement curves, scene-by-scene diagnostics, and normative comparisons
- For videos: Adapt all timepoints and scene divisions to the actual video duration"""
                },
                {"role": "user", "content": prompt}
            ]
            
            for variant_name, variant_data in [("Variant A", variant_a), ("Variant B", variant_b)]:
                for asset in variant_data.get("processed_assets", []):
                    if asset.get("type") == "image" and asset.get("content"):
                        messages.append({
                            "role": "user",
                            "content": [
                                {"type": "text", "text": f"Visual asset from {variant_name}:"},
                                {"type": "image_url", "image_url": {
                                    "url": f"data:image/jpeg;base64,{asset['content']}",
                                    "detail": "high"
                                }}
                            ]
                        })
                    
                    elif asset.get("type") == "video" and asset.get("sample_frames"):
                        for idx, frame_base64 in enumerate(asset['sample_frames']):
                            messages.append({
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": f"Video frame {idx+1} from {variant_name}:"},
                                    {"type": "image_url", "image_url": {
                                        "url": f"data:image/jpeg;base64,{frame_base64}",
                                        "detail": "low"
                                    }}
                                ]
                            })
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                response_format={"type": "json_object"}
            )
            
            ai_response = response.choices[0].message.content.strip()
            parsed_json = json.loads(ai_response)
            print("AI Response JSON:", parsed_json)
            
            return self._validate_response(parsed_json, user_tier)
            
        except Exception as e:
            logger.error(f"Error in comparative analysis: {str(e)}")
            raise Exception(f"AI analysis failed: {str(e)}")
   
    def _build_comparative_prompt(self, variant_a: Dict[str, Any], variant_b: Dict[str, Any], user_tier, request_data) -> str:
        """Build comprehensive prompt with project context and variant data"""
        asset = request_data["variant_a"]["creative_assets"][0]

        project_context = {
            "project_name": asset.get("project_name"),
            "brand": asset.get("brand"),
            "product": asset.get("product"),
            "product_service_type": asset.get("product_service_type"),
            "category": asset.get("category"),
            "market_maturity": asset.get("market_maturity"),
            "campaign_objective": asset.get("campaign_objective"),
            "value_propositions": asset.get("value_propositions"),
            "media_channels": asset.get("media_channels"),
            "kpis": asset.get("kpis"),
            "kpi_target": asset.get("kpi_target")
        }

        def format_variant_content(variant):
            content_sections = []
            
            persona = variant.get('persona', {})
            
            if persona:
                age_min = persona.get('age_min', 25)
                age_max = persona.get('age_max', 45)
                persona_gender_raw = persona.get('gender', ['all genders'])
                persona_gender_list = [persona_gender_raw] if isinstance(persona_gender_raw, str) else (persona_gender_raw or ['all genders'])
                persona_gender = ', '.join(persona_gender_list)
                
                persona_text = f"""
    **Target Persona:**
    Demographics: {persona.get('audience_type', 'N/A')} | {persona.get('geography', 'N/A')} | Age {age_min}-{age_max} | Income ${persona.get('income_min', 'N/A'):,}-${persona.get('income_max', 'N/A'):,} | {persona_gender} | {persona.get('life_stage', 'N/A')}
    Behavior: {persona.get('purchase_frequency', 'N/A')} buyer | Interests: {', '.join(persona.get('interests', [])) if persona.get('interests') else 'N/A'} | {persona.get('category_involvement', 'N/A')} involvement | {persona.get('decision_making_style', 'N/A')} decision-maker
    Platform: {persona.get('platforms', 'N/A')} | Reach {persona.get('min_reach', 'N/A'):,}-{persona.get('max_reach', 'N/A'):,} | Active: {persona.get('peak_activity', 'N/A')} | {persona.get('engagement', 'N/A')} engagement | {persona.get('efficiency', 'N/A')} efficiency
    Creative Preferences (1-10): Clarity {persona.get('clarity', 'N/A')} | Relevance {persona.get('relevance', 'N/A')} | Distinctiveness {persona.get('distinctiveness', 'N/A')} | Brand Fit {persona.get('brand_fit', 'N/A')} | Emotion {persona.get('emotion', 'N/A')} | CTA {persona.get('cta', 'N/A')} | Inclusivity {persona.get('inclusivity', 'N/A')}
    """
                content_sections.append(persona_text)
            
            content_sections.append(f"""
    **Campaign Content:**
    Headline: {variant.get('headline', 'N/A')} | Title: {variant.get('title', 'N/A')}
    Description: {variant.get('description', 'N/A')} | Assets: {variant.get('asset_count', 0)}
    """)
            
            assets = variant.get('processed_assets', [])
            if assets:
                content_sections.append("\n**Creative Assets:**")
                for i, asset in enumerate(assets, 1):
                    asset_type = asset.get('type', 'unknown')
                    content_sections.append(f"\nAsset {i} ({asset_type.upper()}):")
                    
                    if asset_type == 'text':
                        content_sections.append(f"  Ad Copy: {asset.get('ad_copy', 'N/A')}")
                        if asset.get('voice_script'):
                            content_sections.append(f"  Voice: {asset.get('voice_script')}")
                    elif asset_type == 'image':
                        content_sections.append(f"  URL: {asset.get('url', 'N/A')}")
                    elif asset_type == 'video':
                        duration = asset.get('duration_seconds', 0)
                        content_sections.append(f"  URL: {asset.get('url', 'N/A')} | Duration: {duration:.1f}s | Transcript: {asset.get('transcript', 'N/A')} | Frames: {len(asset.get('sample_frames', []))}")
                    elif asset_type == 'audio':
                        content_sections.append(f"  URL: {asset.get('url', 'N/A')} | Transcript: {asset.get('transcript', 'N/A')} | Duration: {asset.get('acoustic_features', {}).get('duration_seconds', 0):.1f}s")
            
            return '\n'.join(content_sections)
        

        
        variant_a_content = format_variant_content(variant_a)
        variant_b_content = format_variant_content(variant_b)
        
        persona_a, persona_b = variant_a.get('persona', {}), variant_b.get('persona', {})
        age_min_a, age_max_a = persona_a.get('age_min', 25), persona_a.get('age_max', 45)
        age_min_b, age_max_b = persona_b.get('age_min', 25), persona_b.get('age_max', 45)
        
        persona_gender_raw_a = persona_a.get('gender', ['all genders'])
        persona_gender_list_a = [persona_gender_raw_a] if isinstance(persona_gender_raw_a, str) else (persona_gender_raw_a or ['all genders'])
        
        persona_gender_raw_b = persona_b.get('gender', ['all genders'])
        persona_gender_list_b = [persona_gender_raw_b] if isinstance(persona_gender_raw_b, str) else (persona_gender_raw_b or ['all genders'])
        
        is_starter = user_tier.lower() == 'starter'
        
        # Get video durations if available
        def get_video_duration(variant_data):
            for asset in variant_data.get('processed_assets', []):
                if asset.get('type') == 'video':
                    return True, int(asset.get('duration_seconds', 60))
            return False, 0
        
        has_video_a, duration_a = get_video_duration(variant_a)
        has_video_b, duration_b = get_video_duration(variant_b)
        
        # Generate dynamic video analysis instructions with enhanced structure
        def generate_video_instructions(has_video, duration, variant_name):
            if not has_video:
                return f'{variant_name}: SET TO null (no video)'
            
            # Calculate 8 evenly distributed timepoints for emotional journey
            num_points = 8
            timepoints = [int((duration / (num_points - 1)) * i) for i in range(num_points)]
            timepoints_str = ', '.join([f"{t}s" for t in timepoints])
            
            # Calculate scene boundaries (7 scenes for comprehensive analysis)
            num_scenes = 7
            scene_duration = duration / num_scenes
            scenes_list = []
            for i in range(num_scenes):
                start = int(i * scene_duration)
                end = int((i + 1) * scene_duration) if i < num_scenes - 1 else int(duration)
                scenes_list.append(f"Scene {i+1} ({start}-{end}s)")
            
            return f'''{variant_name}: REQUIRED - COMPLETE VIDEO ANALYSIS
            
    **EMOTIONAL JOURNEY (8 timepoints at: {timepoints_str}):**
    - Each timepoint MUST include: timestamp (format: "Xs"), primary_emotion (string), intensity (float 1.0-10.0)
    - Emotions must reflect ad content and build a narrative arc
    - Common emotions: inspired, motivated, curious, excited, confident, determined, joyful, hopeful, energized, focused
    - Intensity should vary realistically (not all 8.0+) with peaks and valleys

    **EMOTIONAL ENGAGEMENT SUMMARY:**
    - peak_emotion: Strongest emotion from journey
    - peak_time_seconds: Timestamp of peak (float)
    - low_engagement_scenes: 1-3 scene names with lower attention/emotion
    - method: Always "facial coding simulation"
    - summary: 1-2 sentence narrative of emotional arc

    **SCENE-BY-SCENE ANALYSIS ({num_scenes} scenes: {', '.join(scenes_list)}):**
    Each scene MUST include:
    - scene_name: Descriptive 2-4 word name of what's happening
    - timestamp_range: "X-Ys" format (use exact ranges above)
    - attention_score: Integer 1-10 (how captivating)
    - positive_emotion: Integer 1-10 (emotional positivity)
    - confusion_level: Integer 0-100 (% viewers confused)
    - branding_visibility: Integer 0-100 (% brand presence)

    CRITICAL REQUIREMENTS:
    ✓ Generate ALL {num_points} emotional journey points (no truncation)
    ✓ Generate ALL {num_scenes} scene analyses (no "..." or placeholders)
    ✓ Scores must align with variant's overall performance
    ✓ Scenes with low attention/emotion should match low_engagement_scenes
    ✓ Higher quality creative = higher attention/positive emotion scores
    ✓ Stronger branding in video = higher branding_visibility scores'''
        
        video_instructions_a = generate_video_instructions(has_video_a, duration_a, "Variant A")
        video_instructions_b = generate_video_instructions(has_video_b, duration_b, "Variant B")
        
        project_info = f"""
    **PROJECT CONTEXT:**
    Brand: {project_context['brand']} | Product: {project_context['product']} ({project_context['product_service_type']})
    Category: {project_context['category']} | Market: {project_context['market_maturity']}
    Objective: {project_context['campaign_objective']} | Value Props: {project_context['value_propositions']}
    Channels: {project_context['media_channels']} | KPIs: {project_context['kpis']} (Target: {project_context['kpi_target']})
    """
        
        if is_starter:
            perspectives = """### EVALUATION PERSPECTIVES (2 required)
    1. PERSONA ALIGNMENT (50%): Check age, income, interests, platform, decision style. FLAG mismatches explicitly.
    2. GENERAL AUDIENCE (50%): Unbiased consumer viewpoint."""
            
            variant_template = """{
        "persona_perspective": {"description": "2-3 sentences with mismatch analysis", "feedback": "First-person as persona", "sentiment": "positive/neutral/negative", "persona_match_score": 65},
        "creative_director_perspective": null,
        "general_audience_perspective": {"description": "2-3 sentences", "feedback": "First-person casual", "sentiment": "positive/neutral/negative"},
        "engagement_score": 70, "relevance_score": 65, "click_through_score": 68, "conversion_potential": 60, "overall_performance": 65.75,
        "clarity_score": 5, "brand_linkage_score": 4, "relevance_detail_score": 5, "distinctiveness_score": 5, "persuasion_score": 5, "cta_clarity_score": 5, "craft_score": 5,
        "emotions_triggered": ["curious", "confused"], "primary_takeaway": "Main message", "technical_assessment": ["persona fit", "product relevance", "execution"],
        "persona_misalignment_flags": ["specific mismatch"]
    }"""
            tier_note = "CRITICAL: creative_director_perspective MUST be null for Starter. ALL creative scores (clarity, brand_linkage, relevance_detail, distinctiveness, persuasion, cta_clarity, craft) MUST be integers 1-7."
        else:
            perspectives = """### EVALUATION PERSPECTIVES (3 required)
    1. PERSONA ALIGNMENT (40%): Check age, income, interests, platform, decision style. FLAG mismatches explicitly.
    2. CREATIVE DIRECTOR (35%): Product-message relevance, brand linkage, strategic fit, execution. PENALIZE poor relevance.
    3. GENERAL AUDIENCE (25%): Unbiased consumer viewpoint."""
            
            variant_template = """{
        "persona_perspective": {"description": "2-3 sentences with mismatch analysis", "feedback": "First-person as persona", "sentiment": "positive/neutral/negative", "persona_match_score": 65},
        "creative_director_perspective": {"description": "2-3 sentences with relevance eval", "feedback": "Professional analysis", "sentiment": "positive/neutral/negative", "product_message_fit_score": 60},
        "general_audience_perspective": {"description": "2-3 sentences", "feedback": "First-person casual", "sentiment": "positive/neutral/negative"},
        "engagement_score": 70, "relevance_score": 65, "click_through_score": 68, "conversion_potential": 60, "overall_performance": 65.75,
        "clarity_score": 5, "brand_linkage_score": 4, "relevance_detail_score": 5, "distinctiveness_score": 5, "persuasion_score": 5, "cta_clarity_score": 5, "craft_score": 5,
        "emotions_triggered": ["curious", "confused"], "primary_takeaway": "Main message", "technical_assessment": ["persona fit", "product relevance", "execution"],
        "persona_misalignment_flags": ["specific mismatch"]
    }"""
            tier_note = "CRITICAL: creative_director_perspective MUST include product_message_fit_score. ALL creative scores (clarity, brand_linkage, relevance_detail, distinctiveness, persuasion, cta_clarity, craft) MUST be integers 1-7."
        
        return f"""
    Analyze these advertising variants as an expert evaluator. Consider the project context and evaluate each variant's assets collectively.

    {project_info}

    ═══════════════════════════════════════════════════════════════
    VARIANT A
    {variant_a_content}
    ═══════════════════════════════════════════════════════════════
    VARIANT B
    {variant_b_content}
    ═══════════════════════════════════════════════════════════════

    {perspectives}

    **WINNER CALCULATION:**
    - Starter: (Persona × 0.50) + (General Overall × 0.50)
    - Premium: (Persona × 0.40) + (Product Fit × 0.35) + (General Overall × 0.25)
    - Poor alignment (<60) or product fit (<60) = CANNOT win

    **SCORING REQUIREMENTS (be REALISTIC, penalize mismatches):**

    TIER 1 - Percentage Scores (0-100):
    - persona_match_score: 0-100
    - product_message_fit_score: 0-100 (Premium only)
    - engagement_score: 0-100
    - relevance_score: 0-100
    - click_through_score: 0-100
    - conversion_potential: 0-100
    - overall_performance: 0-100

    TIER 2 - Creative Metrics (MUST be integers 1-7 ONLY):
    - clarity_score: 1-7 (how clear is the message)
    - brand_linkage_score: 1-7 (brand visibility/recall)
    - relevance_detail_score: 1-7 (relevance to audience)
    - distinctiveness_score: 1-7 (uniqueness/standout)
    - persuasion_score: 1-7 (convincing power)
    - cta_clarity_score: 1-7 (call-to-action clarity)
    - craft_score: 1-7 (execution quality)

    CRITICAL: Creative metrics MUST be whole numbers from 1 to 7. DO NOT use 0, 8, 9, 10 or any number outside 1-7.

    OTHER:
    - emotions_triggered: Array of emotions (include negative if misaligned: confused, skeptical, indifferent)
    - persona_misalignment_flags: Array of specific mismatch issues

    ═══════════════════════════════════════════════════════════════
    **VIDEO ANALYSIS REQUIREMENTS (CRITICAL - NO TRUNCATION ALLOWED):**

    {video_instructions_a}

    {video_instructions_b}

    **VIDEO DATA STRUCTURE ENFORCEMENT:**
    - If variant has video: Generate complete emotional_journey, emotional_engagement_summary, and scene_by_scene_analysis
    - If variant has NO video: Set all three fields to null
    - DO NOT generate partial data, placeholders, or "..." 
    - ALL timepoints and ALL scenes must be fully generated
    - Timepoints and scenes must use EXACT timestamps calculated from video duration

    **EXAMPLE COMPLETE VIDEO STRUCTURE (if video exists):**
    {{
        "emotional_journey": [
            {{"timestamp": "0s", "primary_emotion": "inspired", "intensity": 8.0}},
            {{"timestamp": "7s", "primary_emotion": "motivated", "intensity": 7.5}},
            {{"timestamp": "15s", "primary_emotion": "focused", "intensity": 7.0}},
            {{"timestamp": "22s", "primary_emotion": "determined", "intensity": 8.5}},
            {{"timestamp": "30s", "primary_emotion": "energized", "intensity": 7.0}},
            {{"timestamp": "37s", "primary_emotion": "excited", "intensity": 7.5}},
            {{"timestamp": "45s", "primary_emotion": "enthusiastic", "intensity": 8.0}},
            {{"timestamp": "52s", "primary_emotion": "inspired", "intensity": 8.5}}
        ],
        "emotional_engagement_summary": {{
            "peak_emotion": "inspired",
            "peak_time_seconds": 52.0,
            "low_engagement_scenes": ["Volleyball action", "Basketball leap"],
            "method": "facial coding simulation",
            "summary": "The ad maintains high emotional engagement throughout, peaking with inspiration in the final moments."
        }},
        "scene_by_scene_analysis": [
            {{"scene_name": "Urban sports action", "timestamp_range": "0-8s", "attention_score": 7, "positive_emotion": 8, "confusion_level": 20, "branding_visibility": 80}},
            {{"scene_name": "Focused athlete", "timestamp_range": "8-17s", "attention_score": 8, "positive_emotion": 7, "confusion_level": 15, "branding_visibility": 85}},
            {{"scene_name": "Football intensity", "timestamp_range": "17-25s", "attention_score": 8, "positive_emotion": 7, "confusion_level": 10, "branding_visibility": 90}},
            {{"scene_name": "Basketball determination", "timestamp_range": "25-34s", "attention_score": 9, "positive_emotion": 8, "confusion_level": 10, "branding_visibility": 85}},
            {{"scene_name": "Volleyball action", "timestamp_range": "34-43s", "attention_score": 7, "positive_emotion": 7, "confusion_level": 20, "branding_visibility": 80}},
            {{"scene_name": "Basketball leap", "timestamp_range": "43-51s", "attention_score": 8, "positive_emotion": 8, "confusion_level": 15, "branding_visibility": 85}},
            {{"scene_name": "Baseball slide", "timestamp_range": "51-60s", "attention_score": 8, "positive_emotion": 7, "confusion_level": 15, "branding_visibility": 90}}
        ]
    }}

    **IF NO VIDEO:** Set emotional_journey, emotional_engagement_summary, and scene_by_scene_analysis to null
    ═══════════════════════════════════════════════════════════════

    **RESEARCH DATA (ALWAYS GENERATE):**
    1. objectives: Test objectives statement
    2. methodology: Sample description, design, metrics
    3. key_takeaways_table: Comparative metrics with norms
    4. verbatim_highlights: 5-6 realistic quotes per variant
    5. recommendations: keep/improve/adjust actions
    6. normative_comparison: Category percentiles
    7. demographics: Generate realistic age and gender distributions based on persona ranges
    8. respondent_data: 10 respondents per variant reflecting EXACT persona specifications
    - Variant A: Age {age_min_a}-{age_max_a}, Gender: {', '.join(persona_gender_list_a)}
    - Variant B: Age {age_min_b}-{age_max_b}, Gender: {', '.join(persona_gender_list_b)}
    - CRITICAL: If persona specifies single gender (e.g., only "male"), ALL respondents must be that gender
    - If persona specifies multiple genders or "all genders", distribute naturally
    - Scores align with variant performance (appeal↔engagement, brand_recall↔brand_linkage, message_clarity↔clarity×1.4, purchase_intent↔conversion/100)
    - Add ±10-15% variance. If misalignment exists, 3-4 respondents show lower scores. Quality assets = higher scores.
    ═══════════════════════════════════════════════════════════════
    **RESPONDENT DATA GENERATION (CRITICAL - ALWAYS REQUIRED):**

    IMPORTANT: Unlike video data which can be null, respondent data MUST ALWAYS be generated for BOTH variants, even if one or both variants have no video content.

    - Generate EXACTLY 10 complete respondent records for EACH variant separately
    - Field name MUST be "respondent_data_variant_a" and "respondent_data_variant_b" (not "respondent_data")
    - respondent_id: Sequential 1-10 for each variant
    - age: Randomized within persona range (Variant A: {age_min_a}-{age_max_a}, Variant B: {age_min_b}-{age_max_b})
    - gender: Must match persona specification exactly
    * Variant A: {', '.join(persona_gender_list_a)}
    * Variant B: {', '.join(persona_gender_list_b)}
    * If single gender specified (e.g., "male"), ALL 10 must be that gender
    * If multiple/all genders, distribute naturally
    - Scores must align with variant performance with ±10-15% variance
    - NO placeholders, NO "...", NO null values - generate ALL 10 complete records for BOTH variants

    WRONG ❌:
    "respondent_data": [10 records]  // Single combined array

    CORRECT ✓:
    "respondent_data_variant_a": [10 records],  // Separate array for Variant A
    "respondent_data_variant_b": [10 records]   // Separate array for Variant B

    EXAMPLE STRUCTURE (you must generate 10 like this):
    "respondent_data_variant_a": [
        {{"respondent_id": 1, "age": 28, "gender": "male", "appeal_score": 7.2, "brand_recall_aided": 1, "message_clarity": 7.5, "purchase_intent": 0.68}},
        {{"respondent_id": 2, "age": 32, "gender": "female", "appeal_score": 6.8, "brand_recall_aided": 0, "message_clarity": 7.2, "purchase_intent": 0.65}},
        {{"respondent_id": 3, "age": 29, "gender": "male", "appeal_score": 7.5, "brand_recall_aided": 1, "message_clarity": 7.8, "purchase_intent": 0.72}},
        {{"respondent_id": 4, "age": 31, "gender": "female", "appeal_score": 7.0, "brand_recall_aided": 1, "message_clarity": 7.4, "purchase_intent": 0.70}},
        {{"respondent_id": 5, "age": 27, "gender": "male", "appeal_score": 6.5, "brand_recall_aided": 0, "message_clarity": 6.9, "purchase_intent": 0.62}},
        {{"respondent_id": 6, "age": 33, "gender": "female", "appeal_score": 7.3, "brand_recall_aided": 1, "message_clarity": 7.6, "purchase_intent": 0.71}},
        {{"respondent_id": 7, "age": 30, "gender": "male", "appeal_score": 7.1, "brand_recall_aided": 1, "message_clarity": 7.3, "purchase_intent": 0.67}},
        {{"respondent_id": 8, "age": 26, "gender": "female", "appeal_score": 6.9, "brand_recall_aided": 0, "message_clarity": 7.1, "purchase_intent": 0.64}},
        {{"respondent_id": 9, "age": 34, "gender": "male", "appeal_score": 7.4, "brand_recall_aided": 1, "message_clarity": 7.7, "purchase_intent": 0.73}},
        {{"respondent_id": 10, "age": 29, "gender": "female", "appeal_score": 7.2, "brand_recall_aided": 1, "message_clarity": 7.5, "purchase_intent": 0.69}}
    ]
    ═══════════════════════════════════════════════════════════════

    RETURN ONLY VALID JSON (no markdown, no code blocks):

    {{
        "variant_a_results": {variant_template},
        "variant_b_results": {variant_template},
        "comparative_insights": {{
            "winner": "variant_a", "confidence_score": 75,
            "preference_reason": "Explain based on weighted scores and alignment",
            "performance_prediction": "Mention persona fit and product relevance",
            "flip_to_win_variant_a": "Changes for better fit",
            "flip_to_win_variant_b": "Changes for better fit",
            "key_differences": ["persona alignment", "product relevance", "execution", "appeal"],
            "recommendations": ["targeting", "messaging", "creative", "strategy"],
            "why_winner_won": ["persona fit reason", "product relevance reason", "execution reason"]
        }},
        "overall_effectiveness_comparison": {{
            "variant_a_score": 65.75, "variant_b_score": 78.5, "relative_increase": 19.39,
            "interpretation": "Performance explanation with persona/product fit analysis"
        }},
        "research_data": {{
            "objectives": "Test objectives",
            "methodology": {{"sample_description": "20 respondents matching persona demographics", "design": "Monadic exposure, online", "metrics_measured": ["Ad Appeal", "Brand Recall", "Message Clarity", "Purchase Intent", "Emotional Engagement"]}},
            "key_takeaways_table": {{"metrics": [{{"metric": "Ad Appeal", "variant_a": 7.2, "variant_b": 8.5, "category_norm": 7.0}}, {{"metric": "Brand Recall", "variant_a": 78, "variant_b": 92, "category_norm": 80}}, {{"metric": "Message Clarity", "variant_a": 82, "variant_b": 89, "category_norm": 83}}, {{"metric": "Purchase Intent", "variant_a": 64, "variant_b": 73, "category_norm": 65}}]}},
            "emotional_journey_variant_a": <null if no video, or array of 8 complete timepoint objects>,
            "emotional_engagement_summary_variant_a": <null if no video, or complete summary object>,
            "scene_by_scene_analysis_variant_a": <null if no video, or array of 7 complete scene objects>,
            "emotional_journey_variant_b": <null if no video, or array of 8 complete timepoint objects>,
            "emotional_engagement_summary_variant_b": <null if no video, or complete summary object>,
            "scene_by_scene_analysis_variant_b": <null if no video, or array of 7 complete scene objects>,
            "verbatim_highlights_variant_a": ["Quote 1", "Quote 2", "Quote 3", "Quote 4", "Quote 5", "Quote 6"],
            "verbatim_highlights_variant_b": ["Quote 1", "Quote 2", "Quote 3", "Quote 4", "Quote 5", "Quote 6"],
            "recommendations": {{"keep": ["Element 1", "Element 2", "Element 3"], "improve": ["Area 1", "Area 2", "Area 3"], "adjust": ["Change 1", "Change 2", "Change 3"]}},
            "normative_comparison": {{"variant_a_percentile": 45, "variant_b_percentile": 78, "category_benchmark": "{project_context['category']}"}},
            "demographics": {{
                "age_segments": [
                    {{"segment": "25-34", "percent": 45}}, {{"segment": "35-44", "percent": 55}}
                ],
                "gender_split": {{
                    "male": 48, "female": 52
                }}
            }},
            "respondent_data_variant_a": [
                {{"respondent_id": 1, "age": 28, "gender": "male", "appeal_score": 7.2, "brand_recall_aided": 1, "message_clarity": 7.5, "purchase_intent": 0.68}},
                ... (10 total respondents matching Variant A persona: Age {age_min_a}-{age_max_a}, Gender: {', '.join(persona_gender_list_a)})
            ],
            "respondent_data_variant_b": [
                {{"respondent_id": 1, "age": 25, "gender": "female", "appeal_score": 8.5, "brand_recall_aided": 1, "message_clarity": 8.9, "purchase_intent": 0.85}},
                ... (10 total respondents matching Variant B persona: Age {age_min_b}-{age_max_b}, Gender: {', '.join(persona_gender_list_b)})
            ]
        }}
    }}

    {tier_note}
    Calculate relative_increase = ((B_score - A_score) / A_score) × 100

    FINAL VALIDATION CHECKLIST:
    ✓ ALL creative_scores are integers 1-7 (no 0, 8, 9, 10)
    ✓ Video variants have COMPLETE emotional_journey (8 points), emotional_engagement_summary, scene_by_scene_analysis (7 scenes)
    ✓ Non-video variants have all three fields set to null
    ✓ ALL 10 respondents generated per variant with correct age ranges and gender specifications
    ✓ NO "..." or placeholders anywhere in the response
    ✓ Valid JSON structure with no markdown formatting
    ✓ Timestamps in video data match calculated intervals from actual video duration
    """

    def _validate_response(self, parsed_json: dict, user_tier) -> dict:
        """Validate response structure with extended metrics"""
        
        is_starter = user_tier and user_tier.lower() == 'starter'
        
        required_top_level = [
            "variant_a_results", "variant_b_results", "comparative_insights", 
            "overall_effectiveness_comparison", "research_data"
        ]
        
        required_variant_fields = [
            "persona_perspective", "creative_director_perspective", "general_audience_perspective",
            "engagement_score", "relevance_score", "click_through_score", 
            "conversion_potential", "overall_performance", "technical_assessment",
            "clarity_score", "relevance_detail_score",
            "distinctiveness_score", "persuasion_score", "cta_clarity_score",
            "craft_score", "emotions_triggered", "primary_takeaway"
        ]
        
        required_perspective_fields = ["description", "feedback", "sentiment"]
        
        required_comparative_fields = [
            "winner", "confidence_score", "preference_reason", "performance_prediction",
            "flip_to_win_variant_a", "flip_to_win_variant_b", "key_differences",
            "recommendations", "why_winner_won"
        ]
        
        required_effectiveness_comparison = [
            "variant_a_score", "variant_b_score", "relative_increase", "interpretation"
        ]
        
        required_research_data_fields = [
            "objectives", "methodology", "key_takeaways_table", "verbatim_highlights_variant_a",
            "verbatim_highlights_variant_b", "recommendations", "normative_comparison",
            "demographics", "respondent_data_variant_a", "respondent_data_variant_b"
        ]
        
        for field in required_top_level:
            if field not in parsed_json:
                raise Exception(f"Missing required field: {field}")
        
        for field in required_effectiveness_comparison:
            if field not in parsed_json["overall_effectiveness_comparison"]:
                raise Exception(f"Missing field in overall_effectiveness_comparison: {field}")
        
        for field in required_comparative_fields:
            if field not in parsed_json["comparative_insights"]:
                raise Exception(f"Missing field in comparative_insights: {field}")
        
        for field in required_research_data_fields:
            if field not in parsed_json["research_data"]:
                raise Exception(f"Missing field in research_data: {field}")
        for variant_key in ["variant_a_results", "variant_b_results"]:
            variant = parsed_json[variant_key]
            
            for field in required_variant_fields:
                if field not in variant:
                    raise Exception(f"Missing field {field} in {variant_key}")
            
            for perspective in ["persona_perspective", "general_audience_perspective"]:
                perspective_data = variant[perspective]
                
                for field in required_perspective_fields:
                    if field not in perspective_data:
                        raise Exception(f"Missing field {field} in {variant_key}.{perspective}")
                
                if perspective_data["sentiment"] not in ["positive", "neutral", "negative"]:
                    raise Exception(f"Invalid sentiment in {variant_key}.{perspective}: {perspective_data['sentiment']}")
            
            creative_director_data = variant["creative_director_perspective"]
            
            if is_starter:
                if creative_director_data is not None:
                    raise Exception(f"creative_director_perspective should be null for starter tier in {variant_key}")
            else:
                if creative_director_data is None:
                    raise Exception(f"creative_director_perspective cannot be null for {user_tier} tier in {variant_key}")
                
                for field in required_perspective_fields:
                    if field not in creative_director_data:
                        raise Exception(f"Missing field {field} in {variant_key}.creative_director_perspective")
                
                if creative_director_data["sentiment"] not in ["positive", "neutral", "negative"]:
                    raise Exception(f"Invalid sentiment in {variant_key}.creative_director_perspective")
            
            for score_field in ["engagement_score", "relevance_score", "click_through_score", "conversion_potential", "overall_performance"]:
                score = variant[score_field]
                if not isinstance(score, (int, float)) or score < 0 or score > 100:
                    raise Exception(f"Invalid score {score_field} in {variant_key}: {score}")
            
            for score_field in ["clarity_score","relevance_detail_score", 
                            "distinctiveness_score", "persuasion_score", "cta_clarity_score", "craft_score"]:
                score = variant[score_field]
                if not isinstance(score, (int, float)) or score < 1 or score > 7:
                    raise Exception(f"Invalid score {score_field} in {variant_key}: {score} (must be 1-7)")
            
            if not isinstance(variant["emotions_triggered"], list):
                raise Exception(f"Invalid emotions_triggered in {variant_key}")
            
            if not isinstance(variant["primary_takeaway"], str) or not variant["primary_takeaway"]:
                raise Exception(f"Invalid primary_takeaway in {variant_key}")
            
            if not isinstance(variant["technical_assessment"], list) or len(variant["technical_assessment"]) < 1:
                raise Exception(f"Invalid technical_assessment in {variant_key}")
        
        return parsed_json
    
    async def _download_image_content_async(self, image_url: str) -> Optional[str]:
        try:
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                self.executor, self._download_image_sync, image_url
            )
            if content:
                return base64.b64encode(content).decode('utf-8')
            return None
        except Exception as e:
            logger.error(f"Error downloading image from {image_url}: {str(e)}")
            raise e

    def _download_image_sync(self, image_url: str) -> Optional[bytes]:
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Sync download failed for {image_url}: {str(e)}")
            raise e

    def _process_audio_sync(self, audio_url: str) -> dict:
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                audio_path = self._download_audio(audio_url, temp_dir)
                if not audio_path:
                    raise Exception("Failed to download audio")
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as local_executor:
                    transcript_future = local_executor.submit(self._transcribe_audio_sync, audio_path)
                    acoustic_future = local_executor.submit(self._analyze_audio_acoustics, audio_path)
                    
                    transcript = transcript_future.result()
                    acoustic_features = acoustic_future.result()
                
                return {
                    "transcript": transcript,
                    "acoustic_features": acoustic_features
                }
        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")
            raise e

    def _transcribe_audio_sync(self, audio_path: str) -> str:
        try:
            with open(audio_path, "rb") as f:
                transcript = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f
                )
            return transcript.text
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            raise e

    def _analyze_audio_acoustics(self, audio_path: str) -> dict:
        try:
            y, sr = librosa.load(audio_path, sr=22050, mono=True)
            duration = len(y) / sr
            
            return {
                "duration_seconds": float(duration),
                "sample_rate": int(sr),
                "average_energy": float(np.mean(librosa.feature.rms(y=y)[0]))
            }
        except Exception as e:
            logger.error(f"Error analyzing audio acoustics: {str(e)}")
            raise e

    def _process_video_sync(self, video_url: str) -> tuple:
        """OPTIMIZED: Process video with smart frame sampling"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                video_path = self._download_video(video_url, temp_dir)
                if not video_path:
                    raise Exception("Failed to download video")
                
                # Get video duration
                cap = cv2.VideoCapture(video_path)
                if not cap.isOpened():
                    raise Exception("Cannot open video file for duration check")
                
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
                cap.release()
                
                # Process audio extraction and transcription in parallel with frame extraction
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as local_executor:
                    transcript_future = local_executor.submit(
                        self._extract_and_transcribe, video_path, temp_dir
                    )
                    frames_future = local_executor.submit(
                        self._extract_smart_frames, video_path, max_frames=5
                    )
                    
                    transcript = transcript_future.result()
                    sample_frames = frames_future.result()
                
                return transcript, sample_frames, duration
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}")
            raise e
    def _download_video(self, url: str, output_dir: str) -> Optional[str]:
        """OPTIMIZED: Faster video download with better format selection"""
        try:
            output_template = os.path.join(output_dir, "video.%(ext)s")

            ydl_opts = {
                # Prioritize formats with lower file size for faster download
                'format': 'worst[ext=mp4]/worst',  # Use lower quality for faster processing
                'outtmpl': output_template,
                'merge_output_format': 'mp4',
                'quiet': True,  # Reduce logging overhead
                'no_warnings': True,
                'nocheckcertificate': True,
                'geo_bypass': True,
                'skip_unavailable_fragments': True,
                'retries': 5,  # Reduced from 10
                'fragment_retries': 5,
                'extractor_retries': 3,
                'http_chunk_size': 10485760,  # 10MB chunks for faster download
                'concurrent_fragment_downloads': 3,  # Download fragments in parallel
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                },
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Attempting to download video from: {url}")
                info = ydl.extract_info(url, download=True)
                if not info:
                    raise Exception("Failed to extract video info")

                filename = ydl.prepare_filename(info)
                for ext in ['mp4', 'webm', 'mkv']:
                    test_filename = filename.replace('.%(ext)s', f".{ext}")
                    if os.path.exists(test_filename):
                        logger.info(f"Successfully downloaded: {test_filename}")
                        return test_filename

            raise Exception("Downloaded file not found")

        except Exception as e:
            logger.error(f"Error downloading video from {url}: {str(e)}")
            raise e

    def _download_audio(self, url: str, output_dir: str) -> Optional[str]:
        try:
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            if 'audio/mpeg' in content_type:
                ext = 'mp3'
            elif 'audio/wav' in content_type:
                ext = 'wav'
            else:
                ext = 'mp3'
            
            audio_path = os.path.join(output_dir, f"audio.{ext}")
            with open(audio_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if os.path.exists(audio_path):
                return audio_path
            raise Exception("Audio file not saved properly")
            
        except Exception as e:
            logger.error(f"Error downloading audio: {str(e)}")
            raise e

    def _extract_and_transcribe(self, video_path: str, temp_dir: str) -> str:
        """
        OPTIMIZED: Extract audio and transcribe with chunking for large files
        Whisper API has a 25MB file size limit
        """
        try:
            audio_path = os.path.join(temp_dir, "audio.mp3")
            (
                ffmpeg
                .input(video_path)
                .output(
                    audio_path, 
                    ac=1,  # Mono
                    ar=16000,  # 16kHz sample rate
                    audio_bitrate='64k',  # Compressed bitrate
                    format='mp3'
                )
                .run(overwrite_output=True, quiet=True, capture_stderr=True)
            )
            if not os.path.exists(audio_path):
                raise Exception("Audio extraction failed")
            file_size = os.path.getsize(audio_path) / (1024 * 1024)  # Size in MB
            logger.info(f"Extracted audio file size: {file_size:.2f}MB")
            if file_size > 24:
                return self._transcribe_large_audio(audio_path, temp_dir)
            else:
                return self._transcribe_audio_sync(audio_path)
            
        except Exception as e:
            logger.warning("Returning empty transcript due to error")
            return ""
    
    def _transcribe_large_audio(self, audio_path: str, temp_dir: str) -> str:
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            chunk_length_ms = 10 * 60 * 1000
            chunks = []
            for i in range(0, len(audio), chunk_length_ms):
                chunk = audio[i:i + chunk_length_ms]
                chunk_path = os.path.join(temp_dir, f"chunk_{i}.mp3")
                chunk.export(chunk_path, format="mp3", bitrate="64k")
                chunks.append(chunk_path)
            
            logger.info(f"Split audio into {len(chunks)} chunks")
            transcripts = []
            for idx, chunk_path in enumerate(chunks):
                try:
                    transcript = self._transcribe_audio_sync(chunk_path)
                    transcripts.append(transcript)
                    logger.info(f"Transcribed chunk {idx + 1}/{len(chunks)}")
                except Exception as e:
                    logger.warning(f"Failed to transcribe chunk {idx + 1}: {str(e)}")
                    continue
            full_transcript = " ".join(transcripts)
            return full_transcript
            
        except ImportError:
            logger.error("pydub not installed, cannot chunk large audio files")
            # Fallback: try to transcribe anyway
            try:
                return self._transcribe_audio_sync(audio_path)
            except:
                return ""
        except Exception as e:
            logger.error(f"Error transcribing large audio: {str(e)}")
            return ""

    def _extract_smart_frames(self, video_path: str, max_frames: int = 5) -> List[str]:
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception("Cannot open video file")
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames <= max_frames:
                frame_positions = list(range(total_frames))
            else:
                frame_positions = [
                    0,  
                    total_frames // 4,  # 25%
                    total_frames // 2,  # 50% (middle)
                    (3 * total_frames) // 4,  # 75%
                    total_frames - 1  # Last frame
                ]
            encoded_frames = []
            for pos in frame_positions:
                cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
                ret, frame = cap.read()
                if ret:
                    # Resize frame to reduce size (max width 800px)
                    height, width = frame.shape[:2]
                    if width > 800:
                        ratio = 800 / width
                        new_width = 800
                        new_height = int(height * ratio)
                        frame = cv2.resize(frame, (new_width, new_height))
                    
                    success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    if success:
                        frame_base64 = base64.b64encode(buffer).decode('utf-8')
                        encoded_frames.append(frame_base64)
            
            cap.release()
            
            logger.info(f"Extracted {len(encoded_frames)} representative frames from video")
            return encoded_frames
            
        except Exception as e:
            logger.error(f"Error extracting frames: {str(e)}")
            raise e

    async def close(self):
        """Clean up resources"""
        self.executor.shutdown(wait=True)
