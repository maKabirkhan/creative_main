import logging
from fastapi import Depends, APIRouter, HTTPException
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import List, Optional
import os
import json
import base64
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor
from openai import AsyncOpenAI
from app.helpers.security import get_current_user
from app.helpers.validators import validate_required_field
from app.helpers.db import supabase
import cv2
import numpy as np
import yt_dlp
import aiohttp
from asyncio import Semaphore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
executor = ThreadPoolExecutor(max_workers=8)  # Increased workers

# Semaphore to limit concurrent API calls
API_SEMAPHORE = Semaphore(5)

class MarketingAdviceRequest(BaseModel):
    text: str
    project_id: int
    analyze_media: bool = True

class TimelineItem(BaseModel):
    duration: str
    description: str

class MarketingAdviceResponse(BaseModel):
    advice: str
    dos: List[str]
    donts: List[str]
    recommendations: List[str]
    timeline: List[TimelineItem]
    testing_period: str
    assets_analyzed: Optional[dict] = None
_aiohttp_session = None

async def get_aiohttp_session():
    """Get or create aiohttp session"""
    global _aiohttp_session
    if _aiohttp_session is None or _aiohttp_session.closed:
        timeout = aiohttp.ClientTimeout(total=30)
        _aiohttp_session = aiohttp.ClientSession(timeout=timeout)
    return _aiohttp_session

async def verify_project_ownership(project_id: int, user_id: str) -> dict:
    """Verify that the project belongs to the user and return project data"""
    try:
        project_response = (
            supabase.table("projects")
            .select("*")
            .eq("id", project_id)
            .eq("user_id", user_id)
            .execute()
        )
        
        if not project_response.data:
            logger.warning(f"Unauthorized access attempt: User {user_id} tried to access project {project_id}")
            raise HTTPException(
                status_code=404, 
                detail="Project not found or you don't have permission to access it"
            )
        
        return project_response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying project ownership: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to verify project ownership")

async def download_and_encode_image(image_url: str) -> Optional[str]:
    """Download and base64 encode image using aiohttp"""
    try:
        session = await get_aiohttp_session()
        async with session.get(image_url) as response:
            response.raise_for_status()
            content = await response.read()
            return base64.b64encode(content).decode('utf-8')
    except Exception as e:
        logger.error(f"Error downloading image: {str(e)}")
        return None

async def transcribe_audio(audio_url: str) -> str:
    """Download and transcribe audio file"""
    try:
        session = await get_aiohttp_session()
        async with session.get(audio_url) as response:
            response.raise_for_status()
            content = await response.read()
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, "rb") as f:
                async with API_SEMAPHORE:
                    transcript = await client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f
                    )
            return transcript.text
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        return ""

async def analyze_audio_deeply(transcript: str, asset_id: int) -> dict:
    """Deep analysis of audio content using GPT-4"""
    try:
        if not transcript or len(transcript.strip()) < 10:
            return {
                "tone": "Unable to analyze",
                "emotion": "Unable to analyze",
                "message_clarity": "Unable to analyze",
                "call_to_action": "Unable to analyze",
                "target_audience_fit": "Unable to analyze",
                "recommendations": []
            }
        
        analysis_prompt = f"""Analyze this audio advertisement transcript deeply:

TRANSCRIPT:
"{transcript}"

Provide a detailed analysis in the following JSON format:
{{
    "tone": "Describe the overall tone (professional, casual, urgent, emotional, etc.)",
    "emotion": "What emotions does it evoke? (excitement, trust, fear, joy, etc.)",
    "message_clarity": "Rate 1-10 and explain how clear the message is",
    "call_to_action": "What action does it ask for? Is it clear and compelling?",
    "target_audience_fit": "Who is this best suited for? Demographics and psychographics",
    "pacing": "How's the pacing? Too fast, too slow, or just right?",
    "word_choice": "Analysis of language used - simple, technical, emotional, etc.",
    "strengths": ["List 3-4 key strengths"],
    "weaknesses": ["List 3-4 areas for improvement"],
    "recommendations": ["Specific recommendations to improve this audio ad"]
}}"""

        async with API_SEMAPHORE:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert audio marketing analyst. Provide detailed, actionable insights."},
                    {"role": "user", "content": analysis_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                timeout=30
            )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Error analyzing audio {asset_id}: {str(e)}")
        return {
            "tone": "Analysis failed",
            "emotion": "Analysis failed",
            "message_clarity": "Analysis failed",
            "recommendations": []
        }

def extract_frames_fast(video_path: str, temp_dir: str, max_frames: int = 3) -> List[str]:
    """Extract frames using OpenCV - optimized for speed"""
    try:
        frames_dir = os.path.join(temp_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            return []
        
        # Extract 3 frames evenly distributed
        frame_indices = np.linspace(0, total_frames - 1, max_frames, dtype=int)
        
        frames = []
        for i, frame_idx in enumerate(frame_indices):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if ret:
                # Resize for faster processing
                height, width = frame.shape[:2]
                if width > 1280:
                    scale = 1280 / width
                    frame = cv2.resize(frame, None, fx=scale, fy=scale)
                
                frame_filename = os.path.join(frames_dir, f"frame_{i:03d}.jpg")
                cv2.imwrite(frame_filename, frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                
                if os.path.exists(frame_filename):
                    frames.append(frame_filename)
        
        cap.release()
        return frames
        
    except Exception as e:
        logger.error(f"Error extracting frames: {str(e)}")
        return []

async def process_video_fast(video_url: str) -> tuple:
    """Process video: extract single frame only, skip transcription for speed"""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            loop = asyncio.get_event_loop()
            
            # Download video
            video_path = await loop.run_in_executor(
                executor,
                download_video_fast,
                video_url,
                temp_dir
            )
            
            if not video_path:
                return "", []
            
            # Extract only middle frame for speed
            frame_paths = await loop.run_in_executor(
                executor,
                extract_frames_fast,
                video_path,
                temp_dir,
                1  # Single frame only
            )
            
            # Encode frame to base64
            frames_base64 = []
            for frame_path in frame_paths:
                try:
                    with open(frame_path, 'rb') as f:
                        frame_data = base64.b64encode(f.read()).decode('utf-8')
                        frames_base64.append(frame_data)
                except Exception as e:
                    logger.error(f"Error encoding frame: {str(e)}")
            
            return "", frames_base64  # Skip transcript for speed
            
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        return "", []

def download_video_fast(url: str, output_dir: str) -> Optional[str]:
    """Download video using yt-dlp with speed optimizations"""
    try:
        output_template = os.path.join(output_dir, "video.%(ext)s")
        ydl_opts = {
            'format': 'worst[ext=mp4]/worst',  # Use worst quality for speed
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 15,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            for ext in ['mp4', 'webm', 'mkv']:
                test_file = filename.replace('.%(ext)s', f'.{ext}')
                if os.path.exists(test_file):
                    return test_file
                    
        return None
    except Exception as e:
        logger.error(f"Error downloading video: {str(e)}")
        return None

async def analyze_video_deeply(video_url: str, asset_id: int) -> dict:
    """Deep analysis of video content - optimized version"""
    try:
        # Use fast video processing
        transcript, frames = await process_video_fast(video_url)
        
        if not frames:
            return {
                "visual_analysis": "Unable to extract frames",
                "recommendations": ["Manual review required"],
                "error": "frame_extraction_failed"
            }
        
        # Simplified analysis for speed
        analysis_prompt = """Analyze this video frame in detail:

Provide comprehensive analysis in JSON format:
{
    "visual_analysis": "Detailed description of what you see in the video",
    "visual_elements": "Key visual elements, colors, composition, subjects",
    "emotional_impact": "What emotional response does this evoke?",
    "production_quality": "Assessment of video quality, lighting, framing",
    "brand_presence": "How is branding displayed? Is it effective?",
    "message_clarity": "What message is being conveyed? Is it clear?",
    "target_audience": "Who is this video targeting?",
    "strengths": ["3-4 key strengths of this video"],
    "weaknesses": ["3-4 areas that could be improved"],
    "recommendations": ["3-5 specific, actionable recommendations"]
}"""

        async with API_SEMAPHORE:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert video marketing analyst. Provide detailed, actionable insights about video content."},
                    {"role": "user", "content": [
                        {"type": "text", "text": analysis_prompt},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{frames[0]}",
                            "detail": "high"  # Use high detail for better analysis
                        }}
                    ]}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                timeout=30
            )
        
        analysis_result = json.loads(response.choices[0].message.content)
        
        # Store the frame for later use in the prompt
        analysis_result['frame_base64'] = frames[0] if frames else None
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"Error analyzing video {asset_id}: {str(e)}")
        return {
            "visual_analysis": "Analysis error",
            "recommendations": ["Manual review required"],
            "error": str(e)
        }

async def analyze_image_deeply(image_base64: str, asset_id: int) -> dict:
    """Deep analysis of image content"""
    try:
        analysis_prompt = """Analyze this marketing image in detail:

Provide comprehensive analysis in JSON format:
{
    "visual_description": "Detailed description of the image",
    "visual_elements": "Key elements: colors, typography, subjects, layout",
    "composition": "Analysis of composition and design principles",
    "emotional_appeal": "What emotions does this evoke?",
    "brand_presence": "How is branding displayed?",
    "message_clarity": "What message is conveyed? Is it clear?",
    "target_audience": "Who is this targeting?",
    "strengths": ["3-4 key strengths"],
    "weaknesses": ["3-4 areas for improvement"],
    "recommendations": ["3-5 specific, actionable recommendations"]
}"""

        async with API_SEMAPHORE:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert visual marketing analyst. Provide detailed, actionable insights."},
                    {"role": "user", "content": [
                        {"type": "text", "text": analysis_prompt},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}",
                            "detail": "high"
                        }}
                    ]}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                timeout=30
            )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        logger.error(f"Error analyzing image {asset_id}: {str(e)}")
        return {
            "visual_description": "Analysis failed",
            "recommendations": []
        }

async def analyze_project_assets(project_id: int, project: dict, analyze_media: bool) -> dict:
    """Fetch and analyze all assets with optimized parallel processing"""
    try:
        assets_response = (
            supabase.table("creative_assets")
            .select("*")
            .eq("project_id", project_id)
            .execute()
        )
        
        assets = assets_response.data if assets_response.data else []
        
        if not assets:
            return {
                "project": project,
                "assets": [],
                "processed_content": {
                    "text_assets": [],
                    "image_assets": [],
                    "video_assets": [],
                    "audio_assets": []
                }
            }
        
        processed_content = {
            "text_assets": [],
            "image_assets": [],
            "video_assets": [],
            "audio_assets": []
        }
        
        if analyze_media:
            # Process all assets in parallel
            tasks = [process_asset_content_deeply(asset) for asset in assets]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Asset processing failed: {result}")
                    continue
                if result:
                    asset_type = result.get("asset_type")
                    if asset_type == "text":
                        processed_content["text_assets"].append(result)
                    elif asset_type == "image":
                        processed_content["image_assets"].append(result)
                    elif asset_type == "video":
                        processed_content["video_assets"].append(result)
                    elif asset_type == "audio":
                        processed_content["audio_assets"].append(result)
        else:
            for asset in assets:
                asset_type = asset.get("type", "").lower()
                basic_info = {
                    "asset_id": asset["id"],
                    "asset_type": asset_type
                }
                
                if asset_type == "text":
                    basic_info["ad_copy"] = asset.get("ad_copy", "")
                    processed_content["text_assets"].append(basic_info)
                elif asset_type == "image":
                    processed_content["image_assets"].append(basic_info)
                elif asset_type == "video":
                    processed_content["video_assets"].append(basic_info)
                elif asset_type == "audio":
                    processed_content["audio_assets"].append(basic_info)
        
        return {
            "project": project,
            "assets": assets,
            "processed_content": processed_content
        }
        
    except Exception as e:
        logger.error(f"Error analyzing project assets: {str(e)}")
        raise

async def process_asset_content_deeply(asset: dict) -> Optional[dict]:
    """Process individual asset with deep analysis"""
    try:
        asset_type = asset.get("type", "").lower()
        asset_id = asset.get("id")
        
        if asset_type == "text":
            return {
                "asset_type": "text",
                "asset_id": asset_id,
                "ad_copy": asset.get("ad_copy", ""),
                "voice_script": asset.get("voice_script", "")
            }
        
        elif asset_type == "image":
            file_url = asset.get("file_url")
            if not file_url:
                return None
            
            image_base64 = await download_and_encode_image(file_url)
            if image_base64:
                deep_analysis = await analyze_image_deeply(image_base64, asset_id)
                
                return {
                    "asset_type": "image",
                    "asset_id": asset_id,
                    "content": image_base64,
                    "url": file_url,
                    "deep_analysis": deep_analysis
                }
        
        elif asset_type == "audio":
            file_url = asset.get("file_url")
            if not file_url:
                return None
            
            transcript = await transcribe_audio(file_url)
            deep_analysis = await analyze_audio_deeply(transcript, asset_id)
            
            return {
                "asset_type": "audio",
                "asset_id": asset_id,
                "transcript": transcript,
                "url": file_url,
                "deep_analysis": deep_analysis
            }
        
        elif asset_type == "video":
            file_url = asset.get("file_url")
            if not file_url:
                return None
            
            deep_analysis = await analyze_video_deeply(file_url, asset_id)
            
            return {
                "asset_type": "video",
                "asset_id": asset_id,
                "url": file_url,
                "deep_analysis": deep_analysis,
                "frame_content": deep_analysis.get('frame_base64')  # Include frame for prompt
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error processing asset {asset.get('id')}: {str(e)}")
        return None

def build_marketing_prompt_with_assets(user_query: str, project_data: dict) -> list:
    """Build comprehensive prompt with all asset analysis AND project details"""
    
    project = project_data["project"]
    processed = project_data["processed_content"]
    
    # Build PROJECT DETAILS section
    project_details = [
        f"**PROJECT INFORMATION:**",
        f"  - Name: {project.get('name', 'Untitled')}",
        f"  - Brand: {project.get('brand', 'N/A')}",
        f"  - Product/Service: {project.get('product', 'N/A')}",
        f"  - Type: {project.get('product_service_type', 'N/A')}",
        f"  - Category: {project.get('category', 'N/A')}",
        f"  - Market Maturity: {project.get('market_maturity', 'N/A')}",
        f"  - Campaign Objective: {project.get('campaign_objective', 'N/A')}",
        f"  - Value Propositions: {project.get('value_propositions', 'N/A')}",
    ]
    
    # Add media channels if available
    media_channels = project.get('media_channels')
    if media_channels and isinstance(media_channels, list):
        project_details.append(f"  - Media Channels: {', '.join(media_channels)}")
    elif media_channels:
        project_details.append(f"  - Media Channels: {media_channels}")
    
    # Add KPIs
    project_details.append(f"  - KPIs: {project.get('kpis', 'N/A')}")
    project_details.append(f"  - KPI Target: {project.get('kpi_target', 'N/A')}")
    
    # Build comprehensive context
    context_parts = [
        "\n".join(project_details),
        f"\n**TOTAL ASSETS:** Text: {len(processed['text_assets'])}, Images: {len(processed['image_assets'])}, Videos: {len(processed['video_assets'])}, Audio: {len(processed['audio_assets'])}"
    ]
    
    # Add TEXT assets analysis
    if processed['text_assets']:
        context_parts.append("\n**TEXT ASSETS:**")
        for idx, text_asset in enumerate(processed['text_assets'][:3], 1):
            ad_copy = text_asset.get('ad_copy', '')
            if ad_copy:
                context_parts.append(f"{idx}. {ad_copy[:300]}")
    
    # Add IMAGE assets analysis
    if processed['image_assets']:
        context_parts.append("\n**IMAGE ASSETS:**")
        for idx, image in enumerate(processed['image_assets'][:3], 1):
            if image.get('deep_analysis'):
                analysis = image['deep_analysis']
                context_parts.append(f"\nImage {idx}:")
                context_parts.append(f"  - Description: {analysis.get('visual_description', 'N/A')[:200]}")
                context_parts.append(f"  - Composition: {analysis.get('composition', 'N/A')[:150]}")
                context_parts.append(f"  - Emotional Appeal: {analysis.get('emotional_appeal', 'N/A')[:150]}")
                
                strengths = analysis.get('strengths', [])
                if strengths:
                    context_parts.append(f"  - Strengths: {'; '.join(strengths[:3])}")
                
                weaknesses = analysis.get('weaknesses', [])
                if weaknesses:
                    context_parts.append(f"  - Areas to Improve: {'; '.join(weaknesses[:3])}")
    
    # Add VIDEO assets analysis
    if processed['video_assets']:
        context_parts.append("\n**VIDEO ASSETS:**")
        for idx, video in enumerate(processed['video_assets'][:3], 1):
            if video.get('deep_analysis'):
                analysis = video['deep_analysis']
                context_parts.append(f"\nVideo {idx}:")
                context_parts.append(f"  - Visual Content: {analysis.get('visual_analysis', 'N/A')[:250]}")
                context_parts.append(f"  - Visual Elements: {analysis.get('visual_elements', 'N/A')[:200]}")
                context_parts.append(f"  - Emotional Impact: {analysis.get('emotional_impact', 'N/A')[:150]}")
                context_parts.append(f"  - Production Quality: {analysis.get('production_quality', 'N/A')[:150]}")
                context_parts.append(f"  - Message Clarity: {analysis.get('message_clarity', 'N/A')[:150]}")
                
                strengths = analysis.get('strengths', [])
                if strengths:
                    context_parts.append(f"  - Strengths: {'; '.join(strengths[:4])}")
                
                weaknesses = analysis.get('weaknesses', [])
                if weaknesses:
                    context_parts.append(f"  - Areas to Improve: {'; '.join(weaknesses[:4])}")
    
    # Add AUDIO assets analysis
    if processed['audio_assets']:
        context_parts.append("\n**AUDIO ASSETS:**")
        for idx, audio in enumerate(processed['audio_assets'][:3], 1):
            if audio.get('transcript'):
                context_parts.append(f"\nAudio {idx} Transcript: {audio['transcript'][:300]}")
            
            if audio.get('deep_analysis'):
                analysis = audio['deep_analysis']
                context_parts.append(f"  - Tone: {analysis.get('tone', 'N/A')}")
                context_parts.append(f"  - Emotion: {analysis.get('emotion', 'N/A')}")
                context_parts.append(f"  - Message Clarity: {analysis.get('message_clarity', 'N/A')}")
                context_parts.append(f"  - Call to Action: {analysis.get('call_to_action', 'N/A')[:150]}")
                
                strengths = analysis.get('strengths', [])
                if strengths:
                    context_parts.append(f"  - Strengths: {'; '.join(strengths[:3])}")
    
    context_text = "\n".join(context_parts)
    
    # Print the full context for debugging
    print("\n" + "="*80)
    print("CONTEXT BEING SENT TO AI:")
    print("="*80)
    print(context_text)
    print("="*80 + "\n")
    
    prompt = f"""You are an expert marketing strategist with deep knowledge of advertising, branding, and campaign optimization.

**USER QUESTION:** "{user_query}"

**CAMPAIGN CONTEXT AND ASSETS:**
{context_text}

Based on the user's question, the project details, and the detailed asset analysis above, provide strategic, actionable advice in EXACT JSON format:
{{
    "advice": "Comprehensive strategic advice that directly answers the user's question, taking into account the project's objectives, target audience, and brand context (3-5 sentences)",
    "dos": ["Specific action 1 aligned with project objectives", "Specific action 2", "Specific action 3"],
    "donts": ["Specific thing to avoid 1", "Specific thing to avoid 2", "Specific thing to avoid 3"],
    "recommendations": ["Detailed recommendation 1 considering project context", "Detailed recommendation 2", "Detailed recommendation 3", "Detailed recommendation 4"],
    "timeline": [
        {{"duration": "Week 1", "description": "Specific action for week 1 aligned with campaign objective"}},
        {{"duration": "Week 2-3", "description": "Specific action for weeks 2-3"}},
        {{"duration": "Week 4+", "description": "Specific action for week 4 and beyond to meet KPI targets"}}
    ],
    "testing_period": "Recommended testing duration (e.g., 2-4 weeks)"
}}

IMPORTANT: 
- Your response must directly address the user's question using the actual asset content and analysis provided
- Consider the project's brand, objectives, KPIs, and value propositions in your recommendations
- Align your advice with the specified media channels and campaign objectives
- Be specific and reference the actual assets and project details when relevant"""
    
    messages = [
        {"role": "system", "content": "You are an expert marketing strategist. Provide detailed, actionable advice based on the actual project details, assets, and their analysis. Always answer the user's specific question while considering the broader campaign context."},
        {"role": "user", "content": prompt}
    ]
    
    # Add visual content (videos and images)
    visual_messages = []
    if processed['video_assets']:
        for idx, video in enumerate(processed['video_assets'][:2], 1):
            if video.get('frame_content'):
                visual_messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Video {idx} - Representative Frame:"},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{video['frame_content']}",
                            "detail": "high"
                        }}
                    ]
                })
    
    # Add images
    if processed['image_assets']:
        for idx, image in enumerate(processed['image_assets'][:2], 1):
            if image.get('content'):
                visual_messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Image {idx}:"},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{image['content']}",
                            "detail": "high"
                        }}
                    ]
                })
    
    messages.extend(visual_messages)
    
    return messages

@router.post("/", response_model=MarketingAdviceResponse)
async def get_marketing_advice(
    request: MarketingAdviceRequest,
    current_user = Depends(get_current_user)
):
    """Get AI marketing advice with comprehensive asset analysis"""
    try:
        validate_required_field(request.text, "User text")
        
        if not request.project_id or request.project_id <= 0:
            raise HTTPException(status_code=400, detail="Valid Project ID is required")
        
        user_id = str(current_user["id"])
        project, project_data = await asyncio.gather(
            verify_project_ownership(request.project_id, user_id),
            analyze_project_assets(
                project_id=request.project_id,
                project={}, 
                analyze_media=request.analyze_media
            )
        )
        
        project_data["project"] = project
        
        messages = build_marketing_prompt_with_assets(request.text, project_data)
        
        async with API_SEMAPHORE:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
        
        ai_response = json.loads(response.choices[0].message.content)
        
        processed = project_data["processed_content"]
        assets_analyzed = {
            "project_name": project_data["project"].get("name"),
            "total_assets": len(project_data["assets"]),
            "breakdown": {
                "text": len(processed["text_assets"]),
                "images": len(processed["image_assets"]),
                "videos": len(processed["video_assets"]),
                "audio": len(processed["audio_assets"])
            },
            "deep_analysis_performed": request.analyze_media
        }
        
        return MarketingAdviceResponse(
            advice=ai_response.get("advice", ""),
            dos=ai_response.get("dos", []),
            donts=ai_response.get("donts", []),
            recommendations=ai_response.get("recommendations", []),
            timeline=[
                TimelineItem(**item) if isinstance(item, dict) else TimelineItem(duration="N/A", description=str(item))
                for item in ai_response.get("timeline", [])
            ],
            testing_period=ai_response.get("testing_period", "2-4 weeks"),
            assets_analyzed=assets_analyzed
        )
        
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to parse AI response")
    except Exception as e:
        logger.error(f"Error in get_marketing_advice: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate marketing advice: {str(e)}")