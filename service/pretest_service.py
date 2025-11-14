# from typing import List, Optional
# import json
# import uuid
# from datetime import datetime
# import logging
# from openai import OpenAI
# import os
# import base64
# import requests
# import cv2
# import ffmpeg
# import yt_dlp
# import tempfile
# import librosa
# import numpy as np
# import asyncio
# import concurrent.futures
# from functools import lru_cache
# from concurrent.futures import ThreadPoolExecutor

# logger = logging.getLogger(__name__)

# class PretestService:
#     def __init__(self):
#         self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
#         self.pretests_storage = {}
#         self.executor = ThreadPoolExecutor(max_workers=4)

#     async def _analyze_multi_asset_campaign(self, persona: dict, creative_assets: dict, request_body: dict) -> dict:
#         """Campaign analysis with support for multiple images and audio files"""
#         try:
#             user_tier = request_body.get("user_tier", "free")
#             include_creative_director = user_tier in ["professional", "agency", "enterprise"]
            
#             # ADD THESE LINES - Extract persona and content type information
#             persona_age = f"{persona.get('age_min', '25')}-{persona.get('age_max', '45')}"
#             persona_gender = persona.get('gender', 'all genders')
#             persona_type = persona.get('audience_type', 'General Audience')
            
#             # Determine content type
#             text_count = len(creative_assets.get("text_assets", []))
#             image_count = len(creative_assets.get("image_assets", []))
#             video_count = len(creative_assets.get("video_assets", []))
#             audio_count = len(creative_assets.get("audio_assets", []))
            
#             if video_count > 0:
#                 content_type = "VIDEO"
#             elif image_count > 0:
#                 content_type = "IMAGE"
#             elif text_count > 0:
#                 content_type = "TEXT"
#             else:
#                 content_type = "MULTI-ASSET"
            
#             # Extract platforms
#             platforms = persona.get('platforms', [])
#             if isinstance(platforms, str):
#                 try:
#                     import json
#                     platforms = json.loads(platforms)
#                 except:
#                     platforms = [platforms]
#             platforms_str = ', '.join(platforms) if isinstance(platforms, list) else str(platforms)
                
#             prompt = self._build_persona_aware_prompt(persona, creative_assets, request_body, include_creative_director)
            
#             messages = [
#                 {
#                     "role": "system",
#                     "content": """You are an expert campaign analyst.

#     CRITICAL JSON FORMAT REQUIREMENTS:
#     - Return ONLY valid JSON (no markdown, no code blocks, no extra text)
#     - Use lowercase keys with underscores: "performance_insights" NOT "PERFORMANCE_INSIGHTS"
#     - Follow snake_case convention: "scene_by_scene_analysis" NOT "SCENE_BY_SCENE_ANALYSIS"
#     - Match the exact structure provided in the user prompt
#     - All keys must be in lowercase"""
#                 },
#                 {"role": "user", "content": prompt}
#             ]
#             # Process text assets
#             text_assets = creative_assets.get("text_assets", [])
#             for text_asset in text_assets:
#                 text_content = f"TEXT ASSET (ID: {text_asset['asset_id']}):\n"
#                 text_content += f"Ad Copy: {text_asset.get('ad_copy', 'NOT PROVIDED')}\n"
#                 if text_asset.get('voice_script'):
#                     text_content += f"Voice Script: {text_asset['voice_script']}\n"
#                 messages.append({"role": "user", "content": text_content})
            
#             # Process multiple image assets
#             image_assets = creative_assets.get("image_assets", [])
#             for idx, img_asset in enumerate(image_assets):
#                 if img_asset.get("content"):
#                     # Validate base64 content
#                     img_content = img_asset['content']
                    
#                     # Check if base64 is valid and not too large
#                     try:
#                         # Remove potential whitespace/newlines
#                         img_content = img_content.strip().replace('\n', '').replace('\r', '')
                        
#                         # Validate it's proper base64
#                         base64.b64decode(img_content[:100])  # Test decode first 100 chars
                        
#                         # Check size (OpenAI has ~20MB limit, but let's be conservative)
#                         img_size_mb = len(img_content) * 3 / 4 / (1024 * 1024)  # Approximate MB
#                         if img_size_mb > 15:
#                             logger.warning(f"Image {idx + 1} is large ({img_size_mb:.2f}MB), may cause issues")
                        
#                         messages.append({
#                             "role": "user",
#                             "content": [
#                                 {"type": "text", "text": f"IMAGE ASSET #{idx + 1} (ID: {img_asset['asset_id']}): Please analyze this advertising creative image."},
#                                 {"type": "image_url", "image_url": {
#                                     "url": f"data:image/jpeg;base64,{img_content}",
#                                     "detail": "low"  # Use low detail to reduce token usage
#                                 }}
#                             ]
#                         })
#                         logger.info(f"Added image asset {idx + 1} with {img_size_mb:.2f}MB size")
                        
#                     except Exception as img_error:
#                         logger.error(f"Invalid image content for asset {idx + 1}: {str(img_error)}")
#                         # Skip this image but continue with others
#                         messages.append({
#                             "role": "user",
#                             "content": f"IMAGE ASSET #{idx + 1} (ID: {img_asset['asset_id']}): [Image could not be processed]"
#                         })
            
#             video_assets = creative_assets.get("video_assets", [])
#             for video_asset in video_assets:
#                 video_content = f"VIDEO ASSET (ID: {video_asset['asset_id']}):\n"
#                 video_content += f"Transcript: {video_asset.get('transcript', 'No transcript available')[:1000]}\n"
#                 video_content += f"URL: {video_asset.get('url')}"
#                 messages.append({"role": "user", "content": video_content})
            
#             audio_assets = creative_assets.get("audio_assets", [])
#             for idx, audio_asset in enumerate(audio_assets):
#                 acoustic = audio_asset.get("acoustic_features", {})
#                 audio_content = f"AUDIO ASSET #{idx + 1} (ID: {audio_asset['asset_id']}):\n"
#                 audio_content += f"Transcript: {audio_asset.get('transcript', 'No transcript')[:1000]}\n"
#                 audio_content += f"Duration: {acoustic.get('duration_seconds', 0):.1f}s\n"
#                 audio_content += f"Tempo: {acoustic.get('tempo_bpm', 0):.1f} BPM\n"
#                 audio_content += f"Energy: {acoustic.get('average_energy', 0):.3f}"
#                 messages.append({"role": "user", "content": audio_content})
            
#             logger.info(f"Sending request to OpenAI with {len(messages)} messages")
        
#             response = self.openai_client.chat.completions.create(
#                 model="gpt-4o",
#                 messages=messages,
#                 max_tokens=7000,
#                 temperature=0.3,
#                 response_format={"type": "json_object"}
#             )
        
#             if not response or not response.choices:
#                 logger.error("Empty response from OpenAI API")
#                 return self._get_default_analysis(include_creative_director)
            
#             message = response.choices[0].message
            
#             if message.refusal:
#                 logger.error(f"OpenAI API refused the request: {message.refusal}")
#                 return self._get_refusal_analysis(include_creative_director, message.refusal)
            
#             message_content = message.content
#             if message_content is None:
#                 logger.error("API returned None content")
#                 return self._get_default_analysis(include_creative_director)
            
#             ai_response = message_content.strip()
#             logger.info(f"AI Response preview: {ai_response}")
            
#             try:
#                 parsed_json = json.loads(ai_response)
                
#                 # ===== FIX: Normalize all keys to lowercase =====
#                 def normalize_keys(obj):
#                     """Recursively convert all dict keys to lowercase with underscores"""
#                     if isinstance(obj, dict):
#                         return {k.lower().replace('-', '_'): normalize_keys(v) for k, v in obj.items()}
#                     elif isinstance(obj, list):
#                         return [normalize_keys(item) for item in obj]
#                     return obj
                
#                 parsed_json = normalize_keys(parsed_json)
#                 logger.info(f"Normalized keys: {list(parsed_json.keys())}")
                
#             except json.JSONDecodeError as je:
#                 logger.error(f"JSON parse error: {str(je)}")
#                 logger.error(f"Raw response: {ai_response[:1000]}")
#                 return self._get_default_analysis(include_creative_director)
            
#             # Validate required keys
#             required_keys = ["performance_insights", "audience_feedback", "general_audience_response"]
#             missing_keys = [key for key in required_keys if key not in parsed_json]
            
#             if missing_keys:
#                 logger.error(f"Missing required keys: {missing_keys}")
#                 logger.error(f"Available keys: {list(parsed_json.keys())}")
#                 return self._get_default_analysis(include_creative_director)
            
#             result = {
#                 "objectives": parsed_json.get("objectives", ["Analysis in progress", "Analysis in progress", "Analysis in progress"]),
#                 "methodology": parsed_json.get("methodology", {
#                     "sample_size": 150,
#                     "audience": f"{persona_type} aged {persona_age}",
#                     "gender_split": persona_gender,
#                     "design": f"{content_type.lower()} creative testing",
#                     "platform": platforms_str,
#                     "confidence_level": "95%",
#                     "metrics_measured": ["engagement", "clarity", "brand_linkage", "relevance", "conversion_potential"]
#                 }),
#                 "performance_insights": parsed_json["performance_insights"],
#                 "audience_feedback": parsed_json["audience_feedback"],
#                 "general_audience_response": parsed_json["general_audience_response"],
#                 "normative_comparison": parsed_json.get("normative_comparison", {
#                     "top_percentile": "Analysis in progress",
#                     "category_standing": "Analysis in progress",
#                     "memorability_rank": "at norm",
#                     "branding_effectiveness": "at norm"
#                 }),
#                 "scene_by_scene_analysis": parsed_json.get("scene_by_scene_analysis", []),
#                 "verbatim_highlights": parsed_json.get("verbatim_highlights", ["Analysis in progress"]),
#                 "optimization_recommendations": parsed_json.get("optimization_recommendations", {
#                     "keep": ["Analysis in progress"],
#                     "improve": ["Analysis in progress"],
#                     "adjust": ["Analysis in progress"],
#                     "next_steps": "Analysis in progress"
#                 }),
#                 "demographic_breakdown": parsed_json.get("demographic_breakdown", {
#                     "age_18_24": 25,
#                     "age_25_34": 35,
#                     "age_35_44": 25,
#                     "age_45_plus": 15,
#                     "male": 50,
#                     "female": 48,
#                     "other_gender": 2
#                 }),
#                 "emotional_journey": parsed_json.get("emotional_journey", []),
#                 "emotional_engagement_summary": parsed_json.get("emotional_engagement_summary", {
#                     "peak_emotion": "Analysis in progress",
#                     "peak_time_seconds": 0.0,
#                     "low_engagement_scenes": ["Analysis in progress"],
#                     "method": "AI simulation",
#                     "summary": "Analysis in progress"
#                 }),
#                 "technical_appendix": parsed_json.get("technical_appendix", {
#                     "metrics_scale": "1-7 Likert scale for survey responses; 0-100 for performance metrics",
#                     "statistical_confidence": "95%",
#                     "data_source": "AI-powered pre-testing simulation",
#                     "export_formats": ["JSON", "PDF", "CSV"]
#                 })
#             }
            
#             if include_creative_director:
#                 if "creative_director_analysis" not in parsed_json:
#                     logger.error(f"creative_director_analysis missing. Available keys: {list(parsed_json.keys())}")
#                     default = self._get_default_analysis(include_creative_director)
#                     result["creative_director_analysis"] = default["creative_director_analysis"]
#                 else:
#                     result["creative_director_analysis"] = parsed_json["creative_director_analysis"]
            
#             logger.info("Campaign analysis completed successfully")
#             logger.info(f"Returned keys: {list(result.keys())}")
#             return result
            
#         except Exception as e:
#             logger.error(f"Error in campaign analysis: {str(e)}", exc_info=True)
#             user_tier = request_body.get("user_tier", "free")
#             include_creative_director = user_tier in ["professional", "agency", "enterprise"]
#             return self._get_default_analysis(include_creative_director)

#     def _get_refusal_analysis(self, include_creative_director: bool, refusal_reason: str) -> dict:
#         """Return analysis when OpenAI refuses to process the request"""
#         result = {
#             "performance_insights": {
#                 "overall_performance_score": 0,
#                 "engagement": 0,
#                 "click_through_likelihood": 0,
#                 "relevance": 0,
#                 "conversion_potential": 0,
#                 "error": "Content could not be analyzed",
#                 "reason": refusal_reason
#             },
#             "audience_feedback": {
#                 "survey_responses": {
#                     "takeaway": "Unable to analyze - content policy issue",
#                     "clarity": 0,
#                     "brand_linkage": 0,
#                     "relevance": 0,
#                     "distinctiveness": 0,
#                     "emotions_felt": [],
#                     "persuasion_intent": 0,
#                     "cta_clarity": 0,
#                     "craft_execution": 0
#                 },
#                 "detailed_critique": [
#                     f"Analysis could not be completed: {refusal_reason}",
#                     "This may indicate the image contains sensitive content or violates content policy",
#                     "Please ensure your creative assets comply with content guidelines"
#                 ],
#                 "strengths_identified": ["Unable to analyze"],
#                 "improvement_areas": [
#                     "Review image content for compliance with content policies",
#                     "Ensure images are appropriate for AI analysis",
#                     "Contact support if you believe this is an error"
#                 ]
#             },
#             "general_audience_response": {
#                 "survey_responses": {
#                     "takeaway": "Unable to analyze",
#                     "clarity": 0,
#                     "brand_linkage": 0,
#                     "relevance": 0,
#                     "distinctiveness": 0,
#                     "emotions_felt": [],
#                     "persuasion_intent": 0,
#                     "cta_clarity": 0,
#                     "craft_execution": 0
#                 },
#                 "overall_assessment": f"Content analysis blocked: {refusal_reason}",
#                 "engagement_potential": "Unable to assess",
#                 "trust_factors": "Unable to assess",
#                 "recommendations": [
#                     "Verify image content complies with content policies",
#                     "Try re-uploading the image",
#                     "Contact support for assistance"
#                 ]
#             }
#         }
        
#         if include_creative_director:
#             result["creative_director_analysis"] = {
#                 "survey_responses": {
#                     "takeaway_accuracy": "Unable to analyze",
#                     "clarity_professional": 0,
#                     "brand_linkage_strength": 0,
#                     "relevance_demographic": 0,
#                     "distinctiveness_category": 0,
#                     "emotions_strategic": [],
#                     "persuasion_effectiveness": 0,
#                     "cta_strategy": 0,
#                     "craft_professional": 0
#                 },
#                 "overall_assessment": f"Analysis blocked by content policy: {refusal_reason}",
#                 "technical_critique": [
#                     "Content could not be analyzed due to policy restrictions",
#                     "Please review your creative assets"
#                 ],
#                 "strategic_insights": [
#                     "Ensure compliance with content guidelines",
#                     "Verify all assets are appropriate for analysis"
#                 ],
#                 "recommendations": [
#                     "Review and update creative content",
#                     "Ensure compliance with platform policies",
#                     "Contact support if needed"
#                 ]
#             }
        
#         return result


#     async def _download_image_content_async(self, image_url: str) -> Optional[str]:
#         """Download and encode image using thread pool to avoid blocking"""
#         try:
#             loop = asyncio.get_event_loop()
#             content = await loop.run_in_executor(
#                 self.executor, self._download_image_sync, image_url
#             )
#             if content:
#                 # Clean the base64 encoding
#                 encoded = base64.b64encode(content).decode('utf-8')
#                 # Remove any whitespace/newlines that might have been added
#                 encoded = encoded.strip().replace('\n', '').replace('\r', '')
                
#                 # Log size for debugging
#                 size_mb = len(content) / (1024 * 1024)
#                 logger.info(f"Downloaded image: {size_mb:.2f}MB")
                
#                 return encoded
#             return None
                
#         except Exception as e:
#             logger.error(f"Error downloading image from {image_url}: {str(e)}")
#             return None


#     def _download_image_sync(self, image_url: str) -> Optional[bytes]:
#         """Synchronous image download for thread pool execution"""
#         try:
#             response = requests.get(image_url, timeout=30)
#             response.raise_for_status()
            
#             content_type = response.headers.get('content-type', '')
#             if not any(img_type in content_type.lower() for img_type in ['image/', 'application/octet-stream']):
#                 logger.warning(f"Unexpected content type: {content_type}")
            
#             return response.content
#         except Exception as e:
#             logger.error(f"Sync download failed for {image_url}: {str(e)}")
#             return None
        
#     # Update the create_pretest method to include new fields in response

#     async def create_pretest(self, user_id: str, request_data: dict, user_tier) -> dict:
#         """Create and run a pretest analysis with parallel processing for multiple assets"""
#         try:
#             start_time = datetime.now()
#             pretest_id = str(uuid.uuid4())
            
#             user_tier = user_tier
#             request_data["user_tier"] = user_tier
#             analysis_result = await self._generate_multi_asset_analysis_parallel(request_data)
            
#             processing_time = (datetime.now() - start_time).total_seconds()
            
#             creative_ids = request_data["request_body"].get("creative_ids", [])

#             response = {
#                 "pretest_id": pretest_id,
#                 "creative_ids": creative_ids,
#                 "creative_type": request_data["request_body"].get("creative_type", "multi-asset"),
#                 "objectives": analysis_result.get("objectives", []),
#                 "methodology": analysis_result.get("methodology", {}),
#                 "performance_insights": analysis_result["performance_insights"],
#                 "audience_feedback": analysis_result["audience_feedback"],
#                 "general_audience_response": analysis_result.get("general_audience_response", {}),
#                 "normative_comparison": analysis_result.get("normative_comparison", {}),
#                 "scene_by_scene_analysis": analysis_result.get("scene_by_scene_analysis", []),
#                 "verbatim_highlights": analysis_result.get("verbatim_highlights", []),
#                 "optimization_recommendations": analysis_result.get("optimization_recommendations", {}),
#                 "demographic_breakdown": analysis_result.get("demographic_breakdown", {}),
#                 "emotional_journey": analysis_result.get("emotional_journey", []),
#                 "emotional_engagement_summary": analysis_result.get("emotional_engagement_summary", {}),
#                 "technical_appendix": analysis_result.get("technical_appendix", {}),
#                 "created_at": start_time.isoformat(),
#                 "processing_time": processing_time
#             }
            
#             if user_tier in ["professional", "agency", "enterprise"]:
#                 if "creative_director_analysis" not in analysis_result:
#                     logger.error("creative_director_analysis missing from analysis_result")
#                     raise KeyError("creative_director_analysis not found in analysis result")
#                 response["creative_director_analysis"] = analysis_result["creative_director_analysis"]
            
#             if user_id not in self.pretests_storage:
#                 self.pretests_storage[user_id] = {}
#             self.pretests_storage[user_id][pretest_id] = {
#                 **request_data,
#                 "analysis_results": response,
#                 "created_at": start_time.isoformat()
#             }
            
#             return response

#         except Exception as e:
#             logger.error(f"Error in create_pretest: {str(e)}")
#             raise e
    
#     async def _generate_multi_asset_analysis_parallel(self, request_data: dict) -> dict:
#         """Generate AI analysis with parallel processing of multiple assets"""
#         try:
#             persona = request_data.get("persona", {})
#             creative_assets = request_data.get("creative_assets", [])
#             request_body = request_data.get("request_body", {})
            
#             request_body["user_tier"] = request_data.get("user_tier", "free")
#             asset_tasks = []
#             for i, asset in enumerate(creative_assets):
#                 task = self._process_single_asset(i, asset)
#                 asset_tasks.append(task)
            
#             processed_results = await asyncio.gather(*asset_tasks, return_exceptions=True)
#             processed_content = {
#                 "text_assets": [],
#                 "video_assets": [],
#                 "audio_assets": [],
#                 "image_assets": []
#             }
            
#             for result in processed_results:
#                 if isinstance(result, Exception):
#                     logger.error(f"Asset processing failed: {result}")
#                     continue
#                 if result:
#                     asset_type = result.get("asset_type")
#                     if asset_type == "text":
#                         processed_content["text_assets"].append(result)
#                     elif asset_type == "video":
#                         processed_content["video_assets"].append(result)
#                     elif asset_type == "audio":
#                         processed_content["audio_assets"].append(result)
#                     elif asset_type == "image":
#                         processed_content["image_assets"].append(result)
            
#             logger.info(f"Processed assets summary: {len(processed_content['text_assets'])} text, "
#                        f"{len(processed_content['image_assets'])} images, "
#                        f"{len(processed_content['video_assets'])} videos, "
#                        f"{len(processed_content['audio_assets'])} audio")
            
#             return await self._analyze_multi_asset_campaign(
#                 persona=persona,
#                 creative_assets=processed_content,
#                 request_body=request_body
#             )
            
#         except Exception as e:
#             logger.error(f"Error generating parallel analysis: {str(e)}")
#             user_tier = request_data.get("user_tier", "free")
#             include_creative_director = user_tier in ["professional", "agency", "enterprise"]
#             return "error"

#     async def _process_single_asset(self, index: int, asset: dict) -> Optional[dict]:
#         """Process a single asset asynchronously based on type"""
#         try:
#             asset_type = asset.get("type", "").lower()
#             asset_id = asset.get("id")
            
#             if asset_type == "text":
#                 ad_copy = asset.get("ad_copy", "")
#                 voice_script = asset.get("voice_script", "")
                
#                 if not ad_copy:
#                     logger.warning(f"Text asset {asset_id} missing ad_copy field")
                
#                 return {
#                     "asset_type": "text",
#                     "asset_id": asset_id,
#                     "index": index,
#                     "ad_copy": ad_copy,
#                     "voice_script": voice_script
#                 }
                    
#             elif asset_type == "image":
#                 file_url = asset.get("file_url", "")
#                 if not file_url:
#                     logger.warning(f"Image asset {asset_id} missing file_url")
#                     return None
                
#                 image_content = await self._download_image_content_async(file_url)
#                 if image_content:
#                     return {
#                         "asset_type": "image",
#                         "asset_id": asset_id,
#                         "index": index,
#                         "content": image_content,
#                         "url": file_url
#                     }
                    
#             elif asset_type == "video":
#                 file_url = asset.get("file_url", "")
#                 if not file_url:
#                     logger.warning(f"Video asset {asset_id} missing file_url")
#                     return None
                
#                 loop = asyncio.get_event_loop()
#                 transcript, frames = await loop.run_in_executor(
#                     self.executor, self._process_video, file_url
#                 )
#                 return {
#                     "asset_type": "video",
#                     "asset_id": asset_id,
#                     "index": index,
#                     "transcript": transcript,
#                     "frames": frames,
#                     "url": file_url
#                 }
                
#             elif asset_type == "audio":
#                 file_url = asset.get("file_url", "")
#                 if not file_url:
#                     logger.warning(f"Audio asset {asset_id} missing file_url")
#                     return None
                
#                 loop = asyncio.get_event_loop()
#                 audio_analysis = await loop.run_in_executor(
#                     self.executor, self._process_audio_sync, file_url
#                 )
#                 return {
#                     "asset_type": "audio",
#                     "asset_id": asset_id,
#                     "index": index,
#                     "transcript": audio_analysis.get("transcript", ""),
#                     "acoustic_features": audio_analysis.get("acoustic_features", {}),
#                     "url": file_url
#                 }
#             else:
#                 logger.warning(f"Unknown asset type: {asset_type}")
#                 return None
                
#         except Exception as e:
#             logger.error(f"Error processing asset {index} (type: {asset.get('type')}): {str(e)}")
#             return None

#     async def _download_image_content_async(self, image_url: str) -> Optional[str]:
#         """Download and encode image using thread pool to avoid blocking"""
#         try:
#             loop = asyncio.get_event_loop()
#             content = await loop.run_in_executor(
#                 self.executor, self._download_image_sync, image_url
#             )
#             if content:
#                 return base64.b64encode(content).decode('utf-8')
#             return None
                
#         except Exception as e:
#             logger.error(f"Error downloading image from {image_url}: {str(e)}")
#             return None

#     def _download_image_sync(self, image_url: str) -> Optional[bytes]:
#         """Synchronous image download for thread pool execution"""
#         try:
#             response = requests.get(image_url, timeout=30)
#             response.raise_for_status()
#             return response.content
#         except Exception as e:
#             logger.error(f"Sync download failed for {image_url}: {str(e)}")
#             return None

#     def _process_audio_sync(self, audio_url: str) -> dict:
#         """Synchronous audio processing for thread pool execution"""
#         try:
#             with tempfile.TemporaryDirectory() as temp_dir:
#                 audio_path = self._download_audio(audio_url, temp_dir)
#                 if not audio_path:
#                     return {"transcript": "", "acoustic_features": {}}
                
#                 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as local_executor:
#                     transcript_future = local_executor.submit(self._transcribe_audio_sync, audio_path)
#                     acoustic_future = local_executor.submit(self._analyze_audio_acoustics_optimized, audio_path)
                    
#                     transcript = transcript_future.result()
#                     acoustic_features = acoustic_future.result()
                
#                 return {
#                     "transcript": transcript,
#                     "acoustic_features": acoustic_features
#                 }
#         except Exception as e:
#             logger.error(f"Error processing audio: {str(e)}")
#             return {"transcript": "", "acoustic_features": {}}

#     def _transcribe_audio_sync(self, audio_path: str) -> str:
#         """Synchronous audio transcription"""
#         try:
#             with open(audio_path, "rb") as f:
#                 transcript = self.openai_client.audio.transcriptions.create(
#                     model="whisper-1",
#                     file=f
#                 )
#             return transcript.text
#         except Exception as e:
#             logger.error(f"Error transcribing audio: {str(e)}")
#             return ""

#     @lru_cache(maxsize=128)
#     def _analyze_audio_acoustics_optimized(self, audio_path: str) -> dict:
#         """Optimized acoustic analysis with caching"""
#         try:
#             y, sr = librosa.load(audio_path, sr=22050, mono=True)
#             duration = len(y) / sr
            
#             features = {
#                 "duration_seconds": float(duration),
#                 "sample_rate": int(sr),
#                 "total_samples": len(y)
#             }
            
#             try:
#                 hop_length = 1024
#                 tempo, _ = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
#                 features["tempo_bpm"] = float(tempo)
                
#                 rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
#                 features["average_energy"] = float(np.mean(rms))
#                 features["energy_variance"] = float(np.var(rms))
                
#                 spectral_centroids = librosa.feature.spectral_centroid(
#                     y=y, sr=sr, hop_length=hop_length
#                 )[0]
#                 features["spectral_centroid_mean"] = float(np.mean(spectral_centroids))
                
#                 zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]
#                 features["zero_crossing_rate"] = float(np.mean(zcr))
                
#                 energy_threshold = np.mean(rms) * 0.1
#                 silent_frames = rms < energy_threshold
#                 features["silence_ratio"] = float(np.mean(silent_frames))
                
#                 silence_changes = np.diff(silent_frames.astype(int))
#                 features["estimated_pause_count"] = int(np.sum(silence_changes == 1))
                
#             except Exception as feat_e:
#                 logger.error(f"Error extracting features: {feat_e}")
#                 default_features = {
#                     "tempo_bpm": 0, "average_energy": 0, "energy_variance": 0,
#                     "spectral_centroid_mean": 0, "zero_crossing_rate": 0,
#                     "silence_ratio": 0, "estimated_pause_count": 0
#                 }
#                 features.update(default_features)
            
#             return features
            
#         except Exception as e:
#             logger.error(f"Error analyzing audio acoustics: {str(e)}")
#             return {
#                 "duration_seconds": 0, "sample_rate": 0, "total_samples": 0,
#                 "tempo_bpm": 0, "average_energy": 0, "energy_variance": 0,
#                 "silence_ratio": 0, "estimated_pause_count": 0
#             }

#     def _process_video(self, video_url: str) -> tuple:
#         """Optimized video processing"""
#         try:
#             with tempfile.TemporaryDirectory() as temp_dir:
#                 video_path = self._download_video(video_url, temp_dir)
#                 if not video_path:
#                     return "", []
                
#                 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
#                     transcript_future = executor.submit(
#                         self._extract_and_transcribe, video_path, temp_dir
#                     )
#                     frames_future = executor.submit(
#                         self._extract_frames_optimized, video_path, temp_dir
#                     )
                    
#                     transcript = transcript_future.result()
#                     frames = frames_future.result()
                
#                 return transcript, frames
#         except Exception as e:
#             logger.error(f"Error processing video: {str(e)}")
#             return "", []

#     def _extract_frames_optimized(self, video_path: str, temp_dir: str, max_frames: int = 3) -> List[str]:
#         """Optimized frame extraction with reduced frame count"""
#         try:
#             frames_dir = os.path.join(temp_dir, "frames")
#             os.makedirs(frames_dir, exist_ok=True)
            
#             cap = cv2.VideoCapture(video_path)
#             if not cap.isOpened():
#                 return []
            
#             total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
#             if total_frames <= 0:
#                 cap.release()
#                 return []
            
#             frame_indices = np.linspace(0, total_frames - 1, max_frames, dtype=int)
            
#             frames = []
#             for i, frame_idx in enumerate(frame_indices):
#                 cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
#                 ret, frame = cap.read()
                
#                 if ret:
#                     frame_filename = os.path.join(frames_dir, f"frame_{i:03d}.jpg")
#                     success = cv2.imwrite(
#                         frame_filename, frame, 
#                         [cv2.IMWRITE_JPEG_QUALITY, 70]
#                     )
                    
#                     if success and os.path.exists(frame_filename):
#                         frames.append(frame_filename)
            
#             cap.release()
#             return frames
            
#         except Exception as e:
#             logger.error(f"Error extracting frames: {str(e)}")
#             return []
    
#     def _build_persona_aware_prompt(self, persona: dict, creative_assets: dict, request_body: dict, include_creative_director: bool = True) -> str:
#         """Build prompt with integrated consumer survey questions for rigorous evaluation"""
#         persona_age = f"{persona.get('age_min', '25')}-{persona.get('age_max', '45')}"
#         age_min = persona.get('age_min', 25)
#         age_max = persona.get('age_max', 45)
        
#         # Handle persona_gender as a list
#         persona_gender_raw = persona.get('gender', ['all genders'])
#         if isinstance(persona_gender_raw, str):
#             persona_gender_list = [persona_gender_raw]
#         else:
#             persona_gender_list = persona_gender_raw if persona_gender_raw else ['all genders']
        
#         # Create a string representation for display
#         persona_gender = ', '.join(persona_gender_list)
        
#         print("persona gender:", persona_gender)
#         print("persona gender list:", persona_gender_list)
#         print("--------------------------")
        
#         persona_type = persona.get('audience_type', 'General Audience')
        
#         text_count = len(creative_assets.get("text_assets", []))
#         image_count = len(creative_assets.get("image_assets", []))
#         video_count = len(creative_assets.get("video_assets", []))
#         audio_count = len(creative_assets.get("audio_assets", []))
        
#         interests = persona.get('interests', [])
#         interests_str = ', '.join(interests) if isinstance(interests, list) else str(interests)
#         platforms = persona.get('platforms', [])
#         if isinstance(platforms, str):
#             try:
#                 import json
#                 platforms = json.loads(platforms)
#             except:
#                 platforms = [platforms]
#         platforms_str = ', '.join(platforms) if isinstance(platforms, list) else str(platforms)

#         # Determine content type and scene analysis requirements
#         if video_count > 0:
#             content_type = "VIDEO"
#             scene_count = "4-6 temporal scenes"
#             emotional_count = "5-7 temporal points"
#         elif image_count > 0:
#             content_type = "IMAGE"
#             scene_count = "4-5 visual zones"
#             emotional_count = "3-4 viewing phases"
#         elif text_count > 0:
#             content_type = "TEXT"
#             scene_count = "4-5 copy sections"
#             emotional_count = "3-4 reading phases"
#         else:
#             content_type = "MULTI-ASSET"
#             scene_count = "4-5 key moments"
#             emotional_count = "3-5 campaign moments"

#         # Determine sample size based on content type
#         if video_count > 0 or image_count > 0:
#             sample_size = 150
#         else:
#             sample_size = 100

#         # Build the JSON structure with new fields
#         json_structure = """{
#         "objectives": ["<string: objective 1>", "<string: objective 2>", "<string: objective 3>"],
#         "methodology": {
#             "sample_size": <integer: """ + str(sample_size) + """>,
#             "audience": "<string: """ + persona_type + """ aged """ + persona_age + """>",
#             "gender_split": "<string: """ + persona_gender + """>",
#             "design": "<string: """ + content_type.lower() + """ creative testing>",
#             "platform": "<string: """ + platforms_str + """>",
#             "confidence_level": "95%",
#             "metrics_measured": ["<metric_1>", "<metric_2>", "<metric_3>", "<metric_4>", "<metric_5>"]
#         },
#         "performance_insights": {
#             "overall_performance_score": <integer 0-100>,
#             "engagement": <integer 0-100>,
#             "click_through_likelihood": <integer 0-100>,
#             "relevance": <integer 0-100>,
#             "conversion_potential": <integer 0-100>
#         },
#         "audience_feedback": {
#             "survey_responses": {
#                 "takeaway": "<string: primary message from persona perspective>",
#                 "clarity": <integer 1-7>,
#                 "brand_linkage": <integer 1-7>,
#                 "relevance": <integer 1-7>,
#                 "distinctiveness": <integer 1-7>,
#                 "emotions_felt": ["<emotion 1>", "<emotion 2>"],
#                 "persuasion_intent": <integer 1-7>,
#                 "cta_clarity": <integer 1-7>,
#                 "craft_execution": <integer 1-7>
#             },
#             "detailed_critique": ["<specific observation 1>", "<observation 2>", "<observation 3>"],
#             "strengths_identified": ["<strength 1>", "<strength 2>"],
#             "improvement_areas": ["<improvement 1>", "<improvement 2>", "<improvement 3>"]
#         },
#         "general_audience_response": {
#             "survey_responses": {
#                 "takeaway": "<string: general audience primary message>",
#                 "clarity": <integer 1-7>,
#                 "brand_linkage": <integer 1-7>,
#                 "relevance": <integer 1-7>,
#                 "distinctiveness": <integer 1-7>,
#                 "emotions_felt": ["<emotion 1>", "<emotion 2>"],
#                 "persuasion_intent": <integer 1-7>,
#                 "cta_clarity": <integer 1-7>,
#                 "craft_execution": <integer 1-7>
#             },
#             "overall_assessment": "<string: authentic emotional summary>",
#             "engagement_potential": "<string: shareability assessment>",
#             "trust_factors": "<string: credibility assessment>",
#             "recommendations": ["<improvement 1>", "<improvement 2>", "<improvement 3>"]
#         },"""
        
#         if include_creative_director:
#             json_structure += """
#         "creative_director_analysis": {
#             "survey_responses": {
#                 "takeaway_accuracy": "<string: assessment>",
#                 "clarity_professional": <integer 1-7>,
#                 "brand_linkage_strength": <integer 1-7>,
#                 "relevance_demographic": <integer 1-7>,
#                 "distinctiveness_category": <integer 1-7>,
#                 "emotions_strategic": ["<emotion 1>", "<emotion 2>"],
#                 "persuasion_effectiveness": <integer 1-7>,
#                 "cta_strategy": <integer 1-7>,
#                 "craft_professional": <integer 1-7>
#             },
#             "overall_assessment": "<string: professional summary>",
#             "technical_critique": ["<observation 1>", "<observation 2>", "<observation 3>"],
#             "strategic_insights": ["<insight 1>", "<insight 2>", "<insight 3>"],
#             "recommendations": ["<recommendation 1>", "<recommendation 2>", "<recommendation 3>"]
#         },"""

#         json_structure += """
#         "normative_comparison": {
#             "top_percentile": "<string: e.g., 'top 25%', 'bottom 30%', 'top 50%'>",
#             "category_standing": "<string: description>",
#             "memorability_rank": "<string: 'above norm', 'at norm', or 'below norm'>",
#             "branding_effectiveness": "<string: 'above norm', 'at norm', or 'below norm'>"
#         },
#         "scene_by_scene_analysis": [
#             {
#                 "scene_name": "<string: scene name>",
#                 "timestamp_range": "<string: time or location>",
#                 "attention_score": <integer 1-10>,
#                 "positive_emotion": <integer 1-10>,
#                 "confusion_level": <integer 0-100>,
#                 "branding_visibility": <integer 0-100>
#             }
#         ],
#         "verbatim_highlights": [
#             "<quote 1>",
#             "<quote 2>",
#             "<quote 3>",
#             "<quote 4>",
#             "<quote 5>",
#             "<quote 6>",
#             "<quote 7>"
#         ],
#         "optimization_recommendations": {
#             "keep": ["<strength 1>", "<strength 2>"],
#             "improve": ["<fix 1>", "<fix 2>"],
#             "adjust": ["<change 1>", "<change 2>"],
#             "next_steps": "<string: recommended action>"
#         },
#         "demographic_breakdown": {
#             "age_18_24": <integer percentage>,
#             "age_25_34": <integer percentage>,
#             "age_35_44": <integer percentage>,
#             "age_45_plus": <integer percentage>,
#             "male": <integer percentage>,
#             "female": <integer percentage>,
#             "other_gender": <integer percentage>
#         },
#         "emotional_journey": [
#             {
#                 "timestamp": "<string: phase or time>",
#                 "primary_emotion": "<string: emotion name>",
#                 "intensity": <float 1.0-10.0>
#             }
#         ],
#         "emotional_engagement_summary": {
#             "peak_emotion": "<string: highest emotion observed>",
#             "peak_time_seconds": <float: timestamp of peak emotion>,
#             "low_engagement_scenes": ["<scene 1>", "<scene 2>"],
#             "method": "<string: facial coding, survey response, or implicit measurement>",
#             "summary": "<string: overall emotional engagement description>"
#         },
#         "technical_appendix": {
#             "metrics_scale": "1-7 Likert scale for survey responses; 0-100 for performance metrics",
#             "statistical_confidence": "95%",
#             "data_source": "AI-powered pre-testing simulation based on """ + content_type + """ analysis",
#             "export_formats": ["JSON", "PDF", "CSV"]
#         }
#     }"""

#         prompt = f"""CAMPAIGN ANALYSIS - RETURN COMPLETE JSON STRUCTURE

#     ⚠️ CRITICAL: You MUST return ALL sections below in a single valid JSON object. Do not skip any section.

#     === REQUIRED JSON OUTPUT ===
#     Return this EXACT structure with ALL fields filled:

#     {json_structure}

#     ⚠️ DEMOGRAPHIC_BREAKDOWN RULES (MANDATORY):
#     TARGET PERSONA: {persona_age}, {persona_gender}

#     AGE RULES (STRICTLY ENFORCE):
#     - Target age is {age_min}-{age_max}
#     - Put 60-70% of respondents in the age bucket that contains this range
#     - Distribute remaining 30-40% across other age buckets
#     - All percentages must sum to 100

#     === CAMPAIGN DETAILS ===
#     Title: {request_body.get('title', 'Not provided')}
#     Description: {request_body.get('description', 'Not provided')}
#     Content Type: {content_type}
#     Assets: {text_count} text, {image_count} images, {video_count} videos, {audio_count} audio

#     === TARGET PERSONA ===
#     - Type: {persona_type} | Age: {persona_age}
#     - Gender: {persona_gender} | Income: {persona.get('income_min', 'N/A')}-{persona.get('income_max', 'N/A')}
#     - Life Stage: {persona.get('life_stage', 'N/A')} | Interests: {interests_str}
#     - Platforms: {platforms_str}

#     === EVALUATION GROUPS ===

#     GROUP 1 - GENERAL PUBLIC (performance_insights):
#     Provide NUMERIC scores only (0-100):
#     - overall_performance_score, engagement, click_through_likelihood, relevance, conversion_potential

#     GROUP 2 - TARGET PERSONA (audience_feedback):
#     Answer as {persona_age} year old with gender identity: {persona_gender}, interested in {interests_str}:
#     - Complete survey_responses (9 metrics)
#     - Provide 3-5 detailed_critique points
#     - List 2-3 strengths_identified
#     - List 3-5 improvement_areas

#     GROUP 3 - GENERAL AUDIENCE (general_audience_response):
#     Broad audience reaction:
#     - Complete survey_responses (9 metrics)
#     - Provide overall_assessment, engagement_potential, trust_factors
#     - List 3-5 recommendations"""

#         if include_creative_director:
#             prompt += f"""

#     GROUP 4 - CREATIVE DIRECTORS (creative_director_analysis):
#     Professional evaluation FOR the {persona_age} demographic with {persona_gender} representation:
#     - Complete survey_responses (9 metrics)
#     - Provide overall_assessment (honest professional judgment)
#     - List 3-4 technical_critique points
#     - List 3-4 strategic_insights
#     - List 3-5 recommendations"""

        
#         prompt += f"""

#     === RESEARCH OUTPUTS ===

#     NORMATIVE_COMPARISON: Benchmark against category standards
#     SCENE_BY_SCENE_ANALYSIS: Create {scene_count} with attention/emotion scores
#     VERBATIM_HIGHLIGHTS: Generate 5-7 authentic consumer quotes for {persona_age}, {persona_gender} demographic
#     OPTIMIZATION_RECOMMENDATIONS: Specific keep/improve/adjust/next_steps

#     DEMOGRAPHIC_BREAKDOWN: Generate based on target persona ({persona_age}, {persona_gender}):
#     AGE DISTRIBUTION: with in {persona_age}
#     GENDER DISTRIBUTION: within {persona_gender}
#     (All percentages must sum to 100%)

#     EMOTIONAL_JOURNEY: Create {emotional_count} tracking emotional response

#     === SURVEY METRICS REFERENCE ===
#     1. TAKEAWAY: Primary message comprehension (open-ended)
#     2. CLARITY: Message understanding (1-7 scale)
#     3. BRAND_LINKAGE: Brand connection strength (1-7)
#     4. RELEVANCE: Personal/demographic relevance (1-7)
#     5. DISTINCTIVENESS: Category differentiation (1-7)
#     6. EMOTIONS: Felt emotions (multi-select array)
#     7. PERSUASION_INTENT: Purchase likelihood (1-7)
#     8. CTA_CLARITY: Next step clarity (1-7)
#     9. CRAFT_EXECUTION: Quality of execution (1-7)

#     === FINAL REMINDERS ===
#     ✓ Return COMPLETE JSON with ALL sections
#     ✓ Use lowercase snake_case keys
#     ✓ Be HONEST with scores (2-4 for weak, 5-6 average, 7+ only if genuinely strong)
#     ✓ Rate LOW if demographics/interests don't align
#     ✓ Include SPECIFIC observations referencing actual content
#     ✓ Make verbatim quotes sound authentic for the {persona_age}, {persona_gender} demographic"""

#         return prompt
#     def _get_default_analysis(self, include_creative_director: bool = True) -> dict:
#         """Return default analysis if AI parsing fails"""
#         result = {
#             "performance_insights": {
#                 "overall_performance_score": 78,
#                 "engagement": 82,
#                 "click_through_likelihood": 75,
#                 "relevance": 79,
#                 "conversion_potential": 76
#             },
#             "audience_feedback": {
#                 "survey_responses": {
#                     "takeaway": "Analysis in progress",
#                     "clarity": 7,
#                     "brand_linkage": 7,
#                     "relevance": 7,
#                     "distinctiveness": 7,
#                     "emotions_felt": ["neutral"],
#                     "persuasion_intent": 7,
#                     "cta_clarity": 7,
#                     "craft_execution": 7
#                 },
#                 "detailed_critique": ["Analysis in progress"],
#                 "strengths_identified": ["Analysis in progress"],
#                 "improvement_areas": ["Analysis in progress"]
#             },
#             "normative_comparison": {
#                 "top_percentile": "Analysis in progress",
#                 "category_standing": "Analysis in progress",
#                 "memorability_rank": "at norm",
#                 "branding_effectiveness": "at norm"
#             },
#             "scene_by_scene_analysis": [],
#             "verbatim_highlights": ["Analysis in progress"],
#             "optimization_recommendations": {
#                 "keep": ["Analysis in progress"],
#                 "improve": ["Analysis in progress"],
#                 "adjust": ["Analysis in progress"],
#                 "next_steps": "Analysis in progress"
#             },
#             "demographic_breakdown": {
#                 "age_18_24": 25,
#                 "age_25_34": 35,
#                 "age_35_44": 25,
#                 "age_45_plus": 15,
#                 "male": 50,
#                 "female": 48,
#                 "other_gender": 2
#             },
#             "emotional_journey": [],
#             "general_audience_response": {
#                 "survey_responses": {
#                     "takeaway": "Analysis in progress",
#                     "clarity": 7,
#                     "brand_linkage": 7,
#                     "relevance": 7,
#                     "distinctiveness": 7,
#                     "emotions_felt": ["neutral"],
#                     "persuasion_intent": 7,
#                     "cta_clarity": 7,
#                     "craft_execution": 7
#                 },
#                 "overall_assessment": "Analysis in progress",
#                 "engagement_potential": "Analysis in progress",
#                 "trust_factors": "Analysis in progress",
#                 "recommendations": ["Analysis in progress"]
#             }
#         }
        
#         if include_creative_director:
#             result["creative_director_analysis"] = {
#                 "survey_responses": {
#                     "takeaway_accuracy": "Analysis in progress",
#                     "clarity_professional": 7,
#                     "brand_linkage_strength": 7,
#                     "relevance_demographic": 7,
#                     "distinctiveness_category": 7,
#                     "emotions_strategic": ["neutral"],
#                     "persuasion_effectiveness": 7,
#                     "cta_strategy": 7,
#                     "craft_professional": 7
#                 },
#                 "overall_assessment": "Analysis in progress",
#                 "technical_critique": ["Analysis in progress"],
#                 "strategic_insights": ["Analysis in progress"],
#                 "recommendations": ["Analysis in progress"]
#             }
        
#         return result

#     def _download_audio(self, url: str, output_dir: str) -> Optional[str]:
#         """Download audio file from URL"""
#         try:
#             response = requests.get(url, timeout=30)
#             response.raise_for_status()
            
#             content_type = response.headers.get('content-type', '')
#             if 'audio/mpeg' in content_type or 'audio/mp3' in content_type:
#                 ext = 'mp3'
#             elif 'audio/wav' in content_type:
#                 ext = 'wav'
#             elif 'audio/mp4' in content_type or 'audio/m4a' in content_type:
#                 ext = 'm4a'
#             else:
#                 ext = 'mp3'
            
#             audio_path = os.path.join(output_dir, f"audio.{ext}")
#             with open(audio_path, 'wb') as f:
#                 f.write(response.content)
            
#             return audio_path if os.path.exists(audio_path) else None
            
#         except Exception as e:
#             logger.error(f"Error downloading audio: {str(e)}")
#             try:
#                 output_template = os.path.join(output_dir, "audio.%(ext)s")
#                 ydl_opts = {
#                     'format': 'bestaudio/best',
#                     'outtmpl': output_template,
#                     'extract_flat': False,
#                 }
                
#                 with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#                     info = ydl.extract_info(url, download=True)
#                     filename = ydl.prepare_filename(info)
#                     actual_filename = filename.replace('.%(ext)s', f".{info['ext']}")
                    
#                     if os.path.exists(actual_filename):
#                         return actual_filename
                        
#                 return None
#             except Exception as fallback_e:
#                 logger.error(f"Fallback audio download failed: {fallback_e}")
#                 return None

#     def _download_video(self, url: str, output_dir: str) -> Optional[str]:
#         """Download video using yt-dlp"""
#         try:
#             output_template = os.path.join(output_dir, "video.%(ext)s")
#             ydl_opts = {
#                 'format': 'best[ext=mp4]/best',
#                 'outtmpl': output_template,
#             }
            
#             with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#                 info = ydl.extract_info(url, download=True)
#                 filename = ydl.prepare_filename(info)
#                 actual_filename = filename.replace('.%(ext)s', f".{info['ext']}")
                
#                 if os.path.exists(actual_filename):
#                     return actual_filename
                    
#                 for ext in ['mp4', 'webm', 'mkv']:
#                     test_file = filename.replace('.%(ext)s', f'.{ext}')
#                     if os.path.exists(test_file):
#                         return test_file
                        
#             return None
#         except Exception as e:
#             logger.error(f"Error downloading video: {str(e)}")
#             return None
    
#     def _extract_and_transcribe(self, video_path: str, temp_dir: str) -> str:
#         """Extract audio and transcribe"""
#         try:
#             audio_path = os.path.join(temp_dir, "audio.wav")
            
#             (
#                 ffmpeg
#                 .input(video_path)
#                 .output(audio_path, ac=1, ar=16000)
#                 .run(overwrite_output=True, quiet=True)
#             )
            
#             if os.path.exists(audio_path):
#                 with open(audio_path, "rb") as f:
#                     transcript = self.openai_client.audio.transcriptions.create(
#                         model="whisper-1",
#                         file=f
#                     )
#                 return transcript.text
#             return ""
            
#         except Exception as e:
#             logger.error(f"Error extracting/transcribing audio: {str(e)}")
#             return ""
    
#     async def close(self):
#         """Clean up resources"""
#         self.executor.shutdown(wait=True)

from typing import List, Optional, Tuple
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
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class PretestService:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.pretests_storage = {}
        # Increase max_workers for better parallelization
        self.executor = ThreadPoolExecutor(max_workers=8)
        # Add connection pooling for faster HTTP requests
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    async def _analyze_multi_asset_campaign(self, persona: dict, creative_assets: dict, request_body: dict, project: dict) -> dict:
        """Campaign analysis with support for multiple images and audio files"""
        try:
            user_tier = request_body.get("user_tier", "free")
            include_creative_director = user_tier in ["professional", "agency", "enterprise"]
            persona_age = f"{persona.get('age_min', '25')}-{persona.get('age_max', '45')}"
            persona_gender = persona.get('gender', 'all genders')
            persona_type = persona.get('audience_type', 'General Audience')
    
            text_count = len(creative_assets.get("text_assets", []))
            image_count = len(creative_assets.get("image_assets", []))
            video_count = len(creative_assets.get("video_assets", []))
            audio_count = len(creative_assets.get("audio_assets", []))
            
            if video_count > 0:
                content_type = "VIDEO"
            elif image_count > 0:
                content_type = "IMAGE"
            elif text_count > 0:
                content_type = "TEXT"
            else:
                content_type = "MULTI-ASSET"
            platforms = persona.get('platforms', [])
            if isinstance(platforms, str):
                try:
                    platforms = json.loads(platforms)
                except:
                    platforms = [platforms]
            platforms_str = ', '.join(platforms) if isinstance(platforms, list) else str(platforms)
            
            prompt = self._build_persona_aware_prompt(persona, creative_assets, request_body, include_creative_director, project)
            
            messages = [
                {
                    "role": "system",
                    "content": """You are an expert campaign analyst with visual analysis capabilities.

    CRITICAL JSON FORMAT REQUIREMENTS:
    - Return ONLY valid JSON (no markdown, no code blocks, no extra text)
    - Use lowercase keys with underscores: "performance_insights" NOT "PERFORMANCE_INSIGHTS"
    - Follow snake_case convention: "scene_by_scene_analysis" NOT "SCENE_BY_SCENE_ANALYSIS"
    - Match the exact structure provided in the user prompt
    - All keys must be in lowercase

    VISUAL ANALYSIS PRIORITY:
    - ALWAYS analyze the actual visual content shown in images/video frames
    - Identify the ACTUAL brand, product, and content visible
    - If visuals don't match the stated project brief, FLAG this immediately and rate scores low (1-2)
    - Base all analysis on what you SEE, not what the brief claims"""
                },
                {"role": "user", "content": prompt}
            ]
            
            # Add text assets
            for text_asset in creative_assets.get("text_assets", []):
                text_content = f"TEXT ASSET (ID: {text_asset['asset_id']}):\n"
                text_content += f"Ad Copy: {text_asset.get('ad_copy', 'NOT PROVIDED')}\n"
                if text_asset.get('voice_script'):
                    text_content += f"Voice Script: {text_asset['voice_script']}\n"
                messages.append({"role": "user", "content": text_content})
            
            # Add image assets
            for idx, img_asset in enumerate(creative_assets.get("image_assets", [])):
                if img_asset.get("content"):
                    img_content = img_asset['content'].strip().replace('\n', '').replace('\r', '')
                    
                    try:
                        base64.b64decode(img_content[:100])
                        
                        img_size_mb = len(img_content) * 3 / 4 / (1024 * 1024)
                        if img_size_mb > 15:
                            logger.warning(f"Image {idx + 1} is large ({img_size_mb:.2f}MB), may cause issues")
                        
                        messages.append({
                            "role": "user",
                            "content": [
                                {"type": "text", "text": f"IMAGE ASSET #{idx + 1} (ID: {img_asset['asset_id']}): Analyze this advertising creative. Identify the ACTUAL product/brand shown."},
                                {"type": "image_url", "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_content}",
                                    "detail": "high"
                                }}
                            ]
                        })
                        
                    except Exception as img_error:
                        logger.error(f"Invalid image content for asset {idx + 1}: {str(img_error)}")
                        messages.append({
                            "role": "user",
                            "content": f"IMAGE ASSET #{idx + 1} (ID: {img_asset['asset_id']}): [Image could not be processed]"
                        })
            
            for video_idx, video_asset in enumerate(creative_assets.get("video_assets", [])):
                duration = video_asset.get('duration_seconds', 0)
                frames_base64 = video_asset.get('frames_base64', [])
                
                # Add transcript and metadata first
                video_content = f"VIDEO ASSET #{video_idx + 1} (ID: {video_asset['asset_id']}):\n"
                
                if duration > 0:
                    video_content += f"DURATION: {duration} seconds ({int(duration // 60)}:{int(duration % 60):02d})\n"
                    video_content += f"⚠️ CRITICAL: This is a {duration}-second video. Your analysis MUST:\n"
                    video_content += f"  - Create scene_by_scene_analysis covering 0s to {int(duration)}s\n"
                    video_content += f"  - Create emotional_journey with timestamps spanning 0s to {int(duration)}s\n"
                    video_content += f"  - Distribute {len(frames_base64)} frames across the {duration}s timeline\n\n"
                else:
                    video_content += "DURATION: Unknown\n\n"
                
                video_content += f"Audio Transcript: {video_asset.get('transcript', 'No transcript available')[:2000]}\n"
                video_content += f"Source URL: {video_asset.get('url')}\n"
                video_content += f"Number of frames extracted: {len(frames_base64)}\n\n"
                video_content += "⚠️ IMPORTANT: Analyze the VISUAL CONTENT in the frames below. Identify the ACTUAL product/brand shown in the video."
                
                messages.append({"role": "user", "content": video_content})
                
                # Add video frames from base64 strings
                if frames_base64:
                    logger.info(f"Adding {len(frames_base64)} video frames to analysis (duration: {duration}s)")
                    
                    for frame_idx, frame_base64 in enumerate(frames_base64):
                        try:
                            # Calculate approximate timestamp
                            if duration > 0 and len(frames_base64) > 1:
                                frame_timestamp = (frame_idx / (len(frames_base64) - 1)) * duration
                            else:
                                frame_timestamp = 0
                            
                            messages.append({
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text", 
                                        "text": f"VIDEO FRAME {frame_idx + 1}/{len(frames_base64)} at ~{frame_timestamp:.1f}s: What product/brand/content do you see? Describe everything visible in detail."
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{frame_base64}",
                                            "detail": "high"
                                        }
                                    }
                                ]
                            })
                            
                        except Exception as frame_error:
                            logger.error(f"Error adding frame {frame_idx + 1} to messages: {str(frame_error)}")
                else:
                    logger.error(f"Video asset {video_idx + 1} has NO FRAMES - analysis will fail")
                    messages.append({
                        "role": "user",
                        "content": "⚠️ ERROR: No video frames available for analysis. This will severely impact results."
                    })
            
            logger.info(f"Sending request to OpenAI with {len(messages)} messages") 
            for idx, audio_asset in enumerate(creative_assets.get("audio_assets", [])):
                acoustic = audio_asset.get("acoustic_features", {})
                audio_content = f"AUDIO ASSET #{idx + 1} (ID: {audio_asset['asset_id']}):\n"
                audio_content += f"Transcript: {audio_asset.get('transcript', 'No transcript')[:1000]}\n"
                audio_content += f"Duration: {acoustic.get('duration_seconds', 0):.1f}s\n"
                audio_content += f"Tempo: {acoustic.get('tempo_bpm', 0):.1f} BPM\n"
                audio_content += f"Energy: {acoustic.get('average_energy', 0):.3f}"
                messages.append({"role": "user", "content": audio_content})
            
            logger.info(f"Sending request to OpenAI with {len(messages)} messages (including video frames)")
            
            # Call OpenAI API
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.openai_client.chat.completions.create(
                    model="gpt-4o",  # gpt-4o supports vision
                    messages=messages,
                    max_tokens=7000,
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
            )
        
            if not response or not response.choices:
                logger.error("Empty response from OpenAI API")
                return self._get_error_response(user_tier, include_creative_director)
            
            message = response.choices[0].message
            
            if message.refusal:
                logger.error(f"OpenAI API refused the request: {message.refusal}")
                return self._get_error_response(user_tier, include_creative_director)
            
            message_content = message.content
            if message_content is None:
                logger.error("API returned None content")
                return self._get_error_response(user_tier, include_creative_director)
            
            ai_response = message_content.strip()
            
            try:
                parsed_json = json.loads(ai_response)
                def normalize_keys(obj):
                    if isinstance(obj, dict):
                        return {k.lower().replace('-', '_'): normalize_keys(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [normalize_keys(item) for item in obj]
                    return obj
                
                parsed_json = normalize_keys(parsed_json)
                
            except json.JSONDecodeError as je:
                logger.error(f"JSON parse error: {str(je)}")
                return self._get_error_response(user_tier, include_creative_director)
            
            # Validate required keys
            required_keys = ["performance_insights", "audience_feedback", "general_audience_response"]
            missing_keys = [key for key in required_keys if key not in parsed_json]
            
            if missing_keys:
                logger.error(f"Missing required keys: {missing_keys}")
                return self._get_error_response(user_tier, include_creative_director)
            
            # Build result with proper defaults
            result = {
                "objectives": parsed_json.get("objectives", ["Analysis in progress", "Analysis in progress", "Analysis in progress"]),
                "methodology": parsed_json.get("methodology", {
                    "sample_size": 150,
                    "audience": f"{persona_type} aged {persona_age}",
                    "gender_split": persona_gender,
                    "design": f"{content_type.lower()} creative testing",
                    "platform": platforms_str,
                    "confidence_level": "95%",
                    "metrics_measured": ["engagement", "clarity", "brand_linkage", "relevance", "conversion_potential"]
                }),
                "performance_insights": parsed_json["performance_insights"],
                "audience_feedback": parsed_json["audience_feedback"],
                "general_audience_response": parsed_json["general_audience_response"],
                "normative_comparison": parsed_json.get("normative_comparison", {
                    "top_percentile": "Analysis in progress",
                    "category_standing": "Analysis in progress",
                    "memorability_rank": "at norm",
                    "branding_effectiveness": "at norm"
                }),
                "scene_by_scene_analysis": parsed_json.get("scene_by_scene_analysis", []),
                "verbatim_highlights": parsed_json.get("verbatim_highlights", ["Analysis in progress"]),
                "optimization_recommendations": parsed_json.get("optimization_recommendations", {
                    "keep": ["Analysis in progress"],
                    "improve": ["Analysis in progress"],
                    "adjust": ["Analysis in progress"],
                    "next_steps": "Analysis in progress"
                }),
                "demographic_breakdown": parsed_json.get("demographic_breakdown", {
                    "age_18_24": 25,
                    "age_25_34": 35,
                    "age_35_44": 25,
                    "age_45_plus": 15,
                    "male": 50,
                    "female": 48,
                    "other_gender": 2
                }),
                "respondent_data": parsed_json.get("respondent_data", []),
                "emotional_journey": parsed_json.get("emotional_journey", []),
                "emotional_engagement_summary": parsed_json.get("emotional_engagement_summary", {
                    "peak_emotion": "Analysis in progress",
                    "peak_time_seconds": 0.0,
                    "low_engagement_scenes": ["Analysis in progress"],
                    "method": "AI simulation",
                    "summary": "Analysis in progress"
                }),
                "technical_appendix": parsed_json.get("technical_appendix", {
                    "metrics_scale": "1-7 Likert scale for survey responses; 0-100 for performance metrics",
                    "statistical_confidence": "95%",
                    "data_source": "AI-powered pre-testing simulation",
                    "export_formats": ["JSON", "PDF", "CSV"]
                })
            }
            
            if include_creative_director:
                if "creative_director_analysis" not in parsed_json:
                    logger.error("creative_director_analysis missing from parsed_json")
                    result["creative_director_analysis"] = self._get_default_creative_director_analysis()
                else:
                    result["creative_director_analysis"] = parsed_json["creative_director_analysis"]
            
            return result
            
        except Exception as e:
            logger.error(f"Error in campaign analysis: {str(e)}", exc_info=True)
            return self._get_error_response(user_tier, include_creative_director)


    def _get_error_response(self, user_tier: str, include_creative_director: bool) -> dict:
        """Return a structured error response"""
        base_response = {
            "objectives": ["Analysis failed", "Please retry", "Contact support if issue persists"],
            "methodology": {"sample_size": 0, "error": "Analysis failed"},
            "performance_insights": {
                "overall_performance_score": 0,
                "engagement": 0,
                "click_through_likelihood": 0,
                "relevance": 0,
                "conversion_potential": 0
            },
            "audience_feedback": {
                "survey_responses": {
                    "takeaway": "Analysis failed",
                    "clarity": 1,
                    "brand_linkage": 1,
                    "relevance": 1,
                    "distinctiveness": 1,
                    "emotions_felt": ["error"],
                    "persuasion_intent": 1,
                    "cta_clarity": 1,
                    "craft_execution": 1
                },
                "detailed_critique": ["Analysis failed"],
                "strengths_identified": ["Analysis failed"],
                "improvement_areas": ["Analysis failed"]
            },
            "general_audience_response": {
                "survey_responses": {
                    "takeaway": "Analysis failed",
                    "clarity": 1,
                    "brand_linkage": 1,
                    "relevance": 1,
                    "distinctiveness": 1,
                    "emotions_felt": ["error"],
                    "persuasion_intent": 1,
                    "cta_clarity": 1,
                    "craft_execution": 1
                },
                "overall_assessment": "Analysis failed",
                "engagement_potential": "Analysis failed",
                "trust_factors": "Analysis failed",
                "recommendations": ["Analysis failed"]
            }
        }
        
        if include_creative_director:
            base_response["creative_director_analysis"] = self._get_default_creative_director_analysis()
        
        return base_response

    def _get_default_creative_director_analysis(self) -> dict:
        """Return default creative director analysis structure"""
        return {
            "survey_responses": {
                "takeaway_accuracy": "Analysis failed",
                "clarity_professional": 1,
                "brand_linkage_strength": 1,
                "relevance_demographic": 1,
                "distinctiveness_category": 1,
                "emotions_strategic": ["error"],
                "persuasion_effectiveness": 1,
                "cta_strategy": 1,
                "craft_professional": 1
            },
            "overall_assessment": "Analysis failed",
            "technical_critique": ["Analysis failed"],
            "strategic_insights": ["Analysis failed"],
            "recommendations": ["Analysis failed"]
        }

    def _extract_video_metadata(self, video_path: str) -> dict:
        """Extract video metadata including duration"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return {"duration_seconds": 0, "fps": 0, "total_frames": 0}
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            cap.release()
            
            logger.info(f"Video metadata: {duration}s, {fps} fps, {total_frames} frames")
            
            return {
                "duration_seconds": round(duration, 2),
                "fps": round(fps, 2),
                "total_frames": total_frames
            }
        except Exception as e:
            logger.error(f"Error extracting video metadata: {str(e)}")
            return {"duration_seconds": 0, "fps": 0, "total_frames": 0}

    def _extract_frames_with_base64(self, video_path: str, max_frames: int = 8) -> Tuple[List[str], dict]:
        """
        Extract frames and return as base64 strings immediately
        This avoids the tempfile cleanup issue
        """
        try:
            # Extract metadata
            metadata = self._extract_video_metadata(video_path)
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error("Could not open video for frame extraction")
                return [], metadata
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames <= 0:
                cap.release()
                logger.error("Video has no frames")
                return [], metadata
            
            # Calculate frame indices
            frame_indices = np.linspace(0, total_frames - 1, max_frames, dtype=int)
            
            frames_base64 = []
            for i, frame_idx in enumerate(frame_indices):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    # Encode frame to JPEG in memory
                    success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    
                    if success:
                        # Convert to base64 immediately
                        frame_base64 = base64.b64encode(buffer).decode('utf-8')
                        frames_base64.append(frame_base64)
                        logger.debug(f"Encoded frame {i+1}/{max_frames} ({len(frame_base64)} chars)")
                    else:
                        logger.warning(f"Failed to encode frame {i+1}")
                else:
                    logger.warning(f"Failed to read frame at index {frame_idx}")
            
            cap.release()
            
            logger.info(f"Successfully extracted and encoded {len(frames_base64)} frames")
            return frames_base64, metadata
            
        except Exception as e:
            logger.error(f"Error extracting frames: {str(e)}", exc_info=True)
            return [], {"duration_seconds": 0, "fps": 0, "total_frames": 0}

    def _process_video(self, video_url: str) -> Tuple[str, List[str], dict]:
        """
        Process video: download, extract transcript, extract frames as base64
        Returns: (transcript, frames_base64_list, metadata)
        """
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download video
                video_path = self._download_video(video_url, temp_dir)
                if not video_path:
                    logger.error("Video download failed")
                    return "", [], {"duration_seconds": 0, "fps": 0, "total_frames": 0}
                
                logger.info(f"Video downloaded to {video_path}")
                
                # Process in parallel
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    transcript_future = executor.submit(
                        self._extract_and_transcribe, video_path, temp_dir
                    )
                    frames_future = executor.submit(
                        self._extract_frames_with_base64, video_path, max_frames=8
                    )
                    
                    transcript = transcript_future.result()
                    frames_base64, metadata = frames_future.result()
                
                logger.info(f"Video processed: transcript={len(transcript)} chars, "
                          f"frames={len(frames_base64)}, duration={metadata.get('duration_seconds')}s")
                
                return transcript, frames_base64, metadata
                
        except Exception as e:
            logger.error(f"Error processing video: {str(e)}", exc_info=True)
            return "", [], {"duration_seconds": 0, "fps": 0, "total_frames": 0}

    async def _process_single_asset(self, index: int, asset: dict) -> Optional[dict]:
        """Process a single asset asynchronously"""
        try:
            asset_type = asset.get("type", "").lower()
            asset_id = asset.get("id")
            
            if asset_type == "text":
                return {
                    "asset_type": "text",
                    "asset_id": asset_id,
                    "index": index,
                    "ad_copy": asset.get("ad_copy", ""),
                    "voice_script": asset.get("voice_script", "")
                }
                    
            elif asset_type == "image":
                file_url = asset.get("file_url", "")
                if not file_url:
                    return None
                
                image_content = await self._download_image_content_async(file_url)
                if image_content:
                    return {
                        "asset_type": "image",
                        "asset_id": asset_id,
                        "index": index,
                        "content": image_content,
                        "url": file_url
                    }
                    
            elif asset_type == "video":
                file_url = asset.get("file_url", "")
                if not file_url:
                    logger.warning(f"Video asset {asset_id} has no file_url")
                    return None
                
                logger.info(f"Processing video asset {asset_id} from {file_url}")
                
                loop = asyncio.get_event_loop()
                transcript, frames_base64, metadata = await loop.run_in_executor(
                    self.executor, self._process_video, file_url
                )
                
                duration = metadata.get("duration_seconds", 0)
                logger.info(f"Video asset {asset_id} processed: {len(frames_base64)} frames, {duration}s duration")
                
                if not frames_base64:
                    logger.error(f"No frames extracted for video {asset_id}")
                
                return {
                    "asset_type": "video",
                    "asset_id": asset_id,
                    "index": index,
                    "transcript": transcript,
                    "frames_base64": frames_base64,  # Now base64 strings, not file paths
                    "duration_seconds": duration,
                    "fps": metadata.get("fps", 0),
                    "total_frames": metadata.get("total_frames", 0),
                    "url": file_url
                }
                
            elif asset_type == "audio":
                file_url = asset.get("file_url", "")
                if not file_url:
                    return None
                
                loop = asyncio.get_event_loop()
                audio_analysis = await loop.run_in_executor(
                    self.executor, self._process_audio_sync, file_url
                )
                return {
                    "asset_type": "audio",
                    "asset_id": asset_id,
                    "index": index,
                    "transcript": audio_analysis.get("transcript", ""),
                    "acoustic_features": audio_analysis.get("acoustic_features", {}),
                    "url": file_url
                }
            
            return None
                
        except Exception as e:
            logger.error(f"Error processing asset {index} (type: {asset.get('type')}): {str(e)}", exc_info=True)
            return None
          
    async def create_pretest(self, user_id: str, request_data: dict, user_tier) -> dict:
        """Create and run a pretest analysis with parallel processing for multiple assets"""
        try:
            start_time = datetime.now()
            pretest_id = str(uuid.uuid4())
            
            request_data["user_tier"] = user_tier
            print("request body", request_data["project"])
            project = request_data["project"]
            analysis_result = await self._generate_multi_asset_analysis_parallel(request_data, project)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            creative_ids = request_data["request_body"].get("creative_ids", [])

            response = {
                "pretest_id": pretest_id,
                "creative_ids": creative_ids,
                "creative_type": request_data["request_body"].get("creative_type", "multi-asset"),
                "objectives": analysis_result.get("objectives", []),
                "methodology": analysis_result.get("methodology", {}),
                "performance_insights": analysis_result["performance_insights"],
                "audience_feedback": analysis_result["audience_feedback"],
                "general_audience_response": analysis_result.get("general_audience_response", {}),
                "normative_comparison": analysis_result.get("normative_comparison", {}),
                "scene_by_scene_analysis": analysis_result.get("scene_by_scene_analysis", []),
                "verbatim_highlights": analysis_result.get("verbatim_highlights", []),
                "optimization_recommendations": analysis_result.get("optimization_recommendations", {}),
                "demographic_breakdown": analysis_result.get("demographic_breakdown", {}),
                "respondent_data": analysis_result.get("respondent_data", []),
                "emotional_journey": analysis_result.get("emotional_journey", []),
                "emotional_engagement_summary": analysis_result.get("emotional_engagement_summary", {}),
                "technical_appendix": analysis_result.get("technical_appendix", {}),
                "created_at": start_time.isoformat(),
                "processing_time": processing_time
            }
            
            if user_tier in ["professional", "agency", "enterprise"]:
                if "creative_director_analysis" not in analysis_result:
                    logger.error("creative_director_analysis missing from analysis_result")
                    raise KeyError("creative_director_analysis not found in analysis result")
                response["creative_director_analysis"] = analysis_result["creative_director_analysis"]
            
            if user_id not in self.pretests_storage:
                self.pretests_storage[user_id] = {}
            self.pretests_storage[user_id][pretest_id] = {
                **request_data,
                "analysis_results": response,
                "created_at": start_time.isoformat()
            }
            
            return response

        except Exception as e:
            logger.error(f"Error in create_pretest: {str(e)}")
            raise e
    
    async def _generate_multi_asset_analysis_parallel(self, request_data: dict, project : dict) -> dict:
        """Generate AI analysis with parallel processing - OPTIMIZED"""
        try:
            persona = request_data.get("persona", {})
            creative_assets = request_data.get("creative_assets", [])
            request_body = request_data.get("request_body", {})
            
            request_body["user_tier"] = request_data.get("user_tier", "free")
            asset_tasks = [self._process_single_asset(i, asset) for i, asset in enumerate(creative_assets)]
            processed_results = await asyncio.gather(*asset_tasks, return_exceptions=True)
            processed_content = {
                "text_assets": [],
                "video_assets": [],
                "audio_assets": [],
                "image_assets": []
            }
            
            for result in processed_results:
                if isinstance(result, Exception):
                    logger.error(f"Asset processing failed: {result}")
                    continue
                if result:
                    asset_type = result.get("asset_type")
                    if asset_type:
                        processed_content[f"{asset_type}_assets"].append(result)
            
            logger.info(f"Processed assets: {len(processed_content['text_assets'])} text, "
                       f"{len(processed_content['image_assets'])} images, "
                       f"{len(processed_content['video_assets'])} videos, "
                       f"{len(processed_content['audio_assets'])} audio")
            print("type of project", type(project))
            return await self._analyze_multi_asset_campaign(
                persona=persona,
                creative_assets=processed_content,
                request_body=request_body,
                project=project
            )
            
        except Exception as e:
            logger.error(f"Error generating parallel analysis: {str(e)}")
            user_tier = request_data.get("user_tier", "free")
            include_creative_director = user_tier in ["professional", "agency", "enterprise"]
            return "parsing error"

    def _build_persona_aware_prompt(self, persona: dict, creative_assets: dict, request_body: dict, include_creative_director: bool = True, project: dict = None) -> str:
        """Build prompt aligned with PDF output structure for professional creative pretesting"""
        persona_age = f"{persona.get('age_min', '25')}-{persona.get('age_max', '45')}"
        age_min = persona.get('age_min', 25)
        age_max = persona.get('age_max', 45)
        project_name = project.get("name", "Campaign") if project else "Campaign"
        project_brand = project.get("brand", "Brand") if project else "Brand"
        project_product = project.get("product", "Product") if project else "Product"
        product_service_type = project.get("product_service_type", "product/service") if project else "product/service"
        category = project.get("category", "general") if project else "general"
        market_maturity = project.get("market_maturity", "established") if project else "established"
        campaign_objective = project.get("campaign_objective", "awareness") if project else "awareness"
        value_propositions = project.get("value_propositions", []) if project else []
        media_channels = project.get("media_channels", []) if project else []
        kpis = project.get("kpis", []) if project else []
        kpi_target = project.get("kpi_target", "") if project else ""
        value_props_str = ', '.join(value_propositions) if isinstance(value_propositions, list) else str(value_propositions)
        media_channels_str = ', '.join(media_channels) if isinstance(media_channels, list) else str(media_channels)
        kpis_str = ', '.join(kpis) if isinstance(kpis, list) else str(kpis)
        
        persona_gender_raw = persona.get('gender', ['all genders'])
        if isinstance(persona_gender_raw, str):
            persona_gender_list = [persona_gender_raw]
        else:
            persona_gender_list = persona_gender_raw if persona_gender_raw else ['all genders']
        
        persona_gender = ', '.join(persona_gender_list)
        persona_type = persona.get('audience_type', 'General Audience')
        interests = persona.get('interests', [])
        interests_str = ', '.join(interests) if isinstance(interests, list) else str(interests)
        platforms = persona.get('platforms', [])
        if isinstance(platforms, str):
            try:
                platforms = json.loads(platforms)
            except:
                platforms = [platforms]
        platforms_str = ', '.join(platforms) if isinstance(platforms, list) else str(platforms)
        
        text_count = len(creative_assets.get("text_assets", []))
        image_count = len(creative_assets.get("image_assets", []))
        video_count = len(creative_assets.get("video_assets", []))
        audio_count = len(creative_assets.get("audio_assets", []))
        
        video_duration = 0
        if video_count > 0:
            first_video = creative_assets.get("video_assets", [])[0]
            video_duration = first_video.get("duration_seconds", 0)
        
        if video_count > 0:
            content_type = "VIDEO"
            
            if video_duration > 0:
                scene_count_num = max(4, min(12, int(video_duration / 10) + 1))
                scene_count = f"{scene_count_num} scenes"
                
                emotion_count_num = max(5, min(15, int(video_duration / 8) + 1))
                emotional_count = f"{emotion_count_num} temporal points"
                emotion_interval = video_duration / emotion_count_num
            else:
                scene_count = "4-6 temporal scenes"
                emotional_count = "5-7 temporal points"
                
            sample_size = 150
        elif image_count > 0:
            content_type = "IMAGE"
            scene_count = "4-5 visual zones"
            emotional_count = "3-4 viewing phases"
            sample_size = 150
        elif text_count > 0:
            content_type = "TEXT"
            scene_count = "4-5 copy sections"
            emotional_count = "3-4 reading phases"
            sample_size = 100
        else:
            content_type = "MULTI-ASSET"
            scene_count = "4-5 key moments"
            emotional_count = "3-5 campaign moments"
            sample_size = 100

        json_structure = """{
        "objectives": ["<string: objective 1>", "<string: objective 2>", "<string: objective 3>"],
        "methodology": {
            "sample_size": <integer: """ + str(sample_size) + """>,
            "audience": "<string: """ + persona_type + """ aged """ + persona_age + """>",
            "gender_split": "<string: """ + persona_gender + """>",
            "design": "<string: """ + content_type.lower() + """ creative testing>",
            "platform": "<string: """ + platforms_str + """>",
            "confidence_level": "95%",
            "metrics_measured": ["<metric_1>", "<metric_2>", "<metric_3>", "<metric_4>", "<metric_5>"]
        },
        "performance_insights": {
            "overall_performance_score": <integer 0-100>,
            "engagement": <integer 0-100>,
            "click_through_likelihood": <integer 0-100>,
            "relevance": <integer 0-100>,
            "conversion_potential": <integer 0-100>
        },
        "audience_feedback": {
            "survey_responses": {
                "takeaway": "<string: primary message from persona perspective>",
                "clarity": <integer 1-7>,
                "brand_linkage": <integer 1-7>,
                "relevance": <integer 1-7>,
                "distinctiveness": <integer 1-7>,
                "emotions_felt": ["<emotion 1>", "<emotion 2>"],
                "persuasion_intent": <integer 1-7>,
                "cta_clarity": <integer 1-7>,
                "craft_execution": <integer 1-7>
            },
            "detailed_critique": ["<specific observation 1>", "<observation 2>", "<observation 3>"],
            "strengths_identified": ["<strength 1>", "<strength 2>"],
            "improvement_areas": ["<improvement 1>", "<improvement 2>", "<improvement 3>"]
        },
        "general_audience_response": {
            "survey_responses": {
                "takeaway": "<string: general audience primary message>",
                "clarity": <integer 1-7>,
                "brand_linkage": <integer 1-7>,
                "relevance": <integer 1-7>,
                "distinctiveness": <integer 1-7>,
                "emotions_felt": ["<emotion 1>", "<emotion 2>"],
                "persuasion_intent": <integer 1-7>,
                "cta_clarity": <integer 1-7>,
                "craft_execution": <integer 1-7>
            },
            "overall_assessment": "<string: authentic emotional summary>",
            "engagement_potential": "<string: shareability assessment>",
            "trust_factors": "<string: credibility assessment>",
            "recommendations": ["<improvement 1>", "<improvement 2>", "<improvement 3>"]
        },"""
        
        if include_creative_director:
            json_structure += """
        "creative_director_analysis": {
            "survey_responses": {
                "takeaway_accuracy": "<string: assessment>",
                "clarity_professional": <integer 1-7>,
                "brand_linkage_strength": <integer 1-7>,
                "relevance_demographic": <integer 1-7>,
                "distinctiveness_category": <integer 1-7>,
                "emotions_strategic": ["<emotion 1>", "<emotion 2>"],
                "persuasion_effectiveness": <integer 1-7>,
                "cta_strategy": <integer 1-7>,
                "craft_professional": <integer 1-7>
            },
            "overall_assessment": "<string: professional summary>",
            "technical_critique": ["<observation 1>", "<observation 2>", "<observation 3>"],
            "strategic_insights": ["<insight 1>", "<insight 2>", "<insight 3>"],
            "recommendations": ["<recommendation 1>", "<recommendation 2>", "<recommendation 3>"]
        },"""

        json_structure += """
        "normative_comparison": {
            "top_percentile": "<string: e.g., 'top 25%', 'bottom 30%', 'top 50%'>",
            "category_standing": "<string: description vs """ + category + """ category norms>",
            "memorability_rank": "<string: 'above norm', 'at norm', or 'below norm'>",
            "branding_effectiveness": "<string: 'above norm', 'at norm', or 'below norm'>"
        },"""
        
        if video_duration > 0:
            json_structure += f"""
            "scene_by_scene_analysis": [
                {{
                    "scene_name": "<string: scene description>",
                    "timestamp_range": "<string: e.g., '0-{int(video_duration/scene_count_num)}s'>",
                    "attention_score": <integer 1-10>,
                    "positive_emotion": <integer 1-10>,
                    "confusion_level": <integer 0-100>,
                    "branding_visibility": <integer 0-100>
                }}
                // GENERATE {scene_count_num} SCENES SPANNING 0 to {int(video_duration)}s
                // Divide {int(video_duration)}s duration into {scene_count_num} roughly equal scenes
            ],
            """
        else:
            if video_duration == 0:
                json_structure += """
                "scene_by_scene_analysis": [
                    {
                        "scene_name": "<string: scene description>",
                        "timestamp_range": "<string: e.g., '0-5s'>",
                        "attention_score": <integer 1-10>,
                        "positive_emotion": <integer 1-10>,
                        "confusion_level": <integer 0-100>,
                        "branding_visibility": <integer 0-100>
                    }
                ],
                """
            else:
                json_structure += """
                "scene_by_scene_analysis": [],
                """

            
        json_structure += """
        "verbatim_highlights": [
            "<quote 1: authentic consumer response>",
            "<quote 2: authentic consumer response>",
            "<quote 3: authentic consumer response>",
            "<quote 4: authentic consumer response>",
            "<quote 5: authentic consumer response>",
            "<quote 6: authentic consumer response>",
            "<quote 7: authentic consumer response>"
        ],
        "optimization_recommendations": {
            "keep": ["<strength 1>", "<strength 2>"],
            "improve": ["<fix 1>", "<fix 2>"],
            "adjust": ["<change 1>", "<change 2>"],
            "next_steps": "<string: recommended action>"
        },
        "demographic_breakdown": {
            "age_18_24": <integer percentage>,
            "age_25_34": <integer percentage>,
            "age_35_44": <integer percentage>,
            "age_45_plus": <integer percentage>,
            "male": <integer percentage>,
            "female": <integer percentage>,
            "other_gender": <integer percentage>
        },
        "respondent_data": [
            {
                "respondent_id": 1001,
                "gender": "<string: M/F/Other>",
                "age": <integer: """ + str(age_min) + """-""" + str(age_max) + """>",
                "appeal_score": <integer 1-10>,
                "brand_recall_aided": <integer 0 or 1>,
                "message_clarity": <integer 1-10>,
                "purchase_intent": <float 0.0-1.0>
            },
            {
                "respondent_id": 1002,
                "gender": "<string: M/F/Other>",
                "age": <integer: """ + str(age_min) + """-""" + str(age_max) + """>",
                "appeal_score": <integer 1-10>,
                "brand_recall_aided": <integer 0 or 1>,
                "message_clarity": <integer 1-10>,
                "purchase_intent": <float 0.0-1.0>
            }
            // CONTINUE FOR ALL 20 RESPONDENTS (IDs 1001-1020)
            // THIS SECTION IS MANDATORY - GENERATE ALL 20 RECORDS
        ],"""
        
        if video_count > 0:
            json_structure += """
        "emotional_journey": [
            {
                "timestamp": "<string: time in seconds>",
                "primary_emotion": "<string: emotion name>",
                "intensity": <float 1.0-10.0>
            }
        ],
        "emotional_engagement_summary": {
            "peak_emotion": "<string: highest emotion observed>",
            "peak_time_seconds": <float: timestamp of peak>,
            "low_engagement_scenes": ["<scene 1>", "<scene 2>"],
            "method": "facial coding simulation",
            "summary": "<string: overall emotional engagement>"
        },"""

        json_structure += """
        "technical_appendix": {
            "metrics_scale": "1-7 Likert scale for survey; 0-100 for performance",
            "statistical_confidence": "95%",
            "data_source": "AI-powered pre-testing simulation",
            "export_formats": ["JSON", "PDF", "CSV"]
        }
    }"""

        prompt = f"""🚨 CRITICAL: YOU MUST RETURN COMPLETE JSON WITH ALL SECTIONS INCLUDING FULL 20-RECORD RESPONDENT_DATA ARRAY 🚨

    === PROJECT CONTEXT ===
    Campaign: {project_name}
    Brand: {project_brand} | Product: {project_product}
    Type: {product_service_type} | Category: {category}
    Market: {market_maturity} market
    Objective: {campaign_objective}
    Value Props: {value_props_str}
    Media Channels: {media_channels_str}
    KPIs: {kpis_str}
    Target: {kpi_target}

    === CAMPAIGN INFO ===
    Title: {request_body.get('title', 'Not provided')}
    Type: {content_type} | Assets: {text_count} text, {image_count} img, {video_count} vid, {audio_count} audio

    === TARGET PERSONA ===
    {persona_type} | Age: {persona_age} | Gender: {persona_gender}
    Interests: {interests_str} | Platforms: {platforms_str}

    === REQUIRED OUTPUT ===
    {json_structure}

    === ANALYSIS INSTRUCTIONS ===

    ⚠️ CRITICAL: FIRST verify that the creative assets actually match the project details.
    - If assets show a DIFFERENT product/brand than stated in project: FLAG THIS IMMEDIATELY
    - Rate all scores as 1-2 (very poor) if there's a mismatch
    - In feedback, explicitly state: "Creative assets do not match stated product/brand"

    YOU ARE EVALUATING: {project_brand}'s "{project_product}" campaign in the {category} category.
    CAMPAIGN GOAL: {campaign_objective}
    KEY MESSAGE: {value_props_str}

    ⚠️ VERIFY: Do the assets actually show {project_product} from {project_brand}? If NO, rate everything LOW and flag mismatch.

    1. OBJECTIVES: 3 specific research goals aligned with {campaign_objective} for this {product_service_type}

    2. METHODOLOGY: Match persona (sample_size: {sample_size}, audience: {persona_type} aged {persona_age})

    3. PERFORMANCE_INSIGHTS: Numeric scores (0-100) evaluating how well creative achieves {campaign_objective}
    - Consider {market_maturity} market dynamics
    - Assess against KPI target: {kpi_target}

    4. AUDIENCE_FEEDBACK: Target persona ({persona_age}, {persona_gender}) survey response
    ⚠️ FIRST CHECK: Does the creative actually show {project_product}? If showing different product, rate 1-2 across all metrics.
    - Evaluate as someone interested in {interests_str}
    - Assess if ACTUAL content shown matches {product_service_type} expectations
    - If creative shows WRONG product/brand, state in takeaway: "This appears to be [actual product], not {project_product}"
    - Consider if {value_props_str} resonates with persona
    - Rate brand ({project_brand}) recognition - rate 1 if wrong brand shown
    - Judge if creative fits {platforms_str} platform expectations
    - Rate VERY LOW if content misaligns with persona profile OR shows wrong product

    5. GENERAL_AUDIENCE_RESPONSE: Broad audience reaction
    ⚠️ CHECK: Does creative match {project_brand} and {project_product}? If not, flag in takeaway.
    - Assess what brand/product is ACTUALLY shown in the creative
    - If mismatch detected, state: "Creative shows [actual product], not aligned with stated {project_product}"
    - Evaluate {product_service_type} appeal beyond target demographic
    - Consider {category} category expectations vs actual content shown

    6. NORMATIVE_COMPARISON: Benchmark vs {category} category norms in {market_maturity} market
    - Compare to typical {category} advertising
    - Assess competitive positioning for {project_product}"""

        if include_creative_director:
            prompt += f"""

    7. CREATIVE_DIRECTOR_ANALYSIS: Professional evaluation
    ⚠️ CRITICAL CHECK: Verify creative assets match project brief
    - If wrong product/brand shown: Rate all metrics 1-2 and state "Critical misalignment between brief and execution"
    - Assess strategic alignment with {campaign_objective}
    - Evaluate if ACTUAL content communicates value proposition ({value_props_str})
    - Judge execution quality for {media_channels_str} channels
    - Consider {category} category best practices
    - Assess KPI achievement potential ({kpis_str})
    - Flag any disconnect between stated project and actual creative content"""
        
        if video_count > 0 and video_duration > 0:
            prompt += f"""
        VIDEO DURATION: {video_duration} seconds ({int(video_duration // 60)}:{int(video_duration % 60):02d})
        REQUIRED SCENES: {scene_count_num} (spanning full {int(video_duration)}s duration)
        EMOTIONAL POINTS: {emotion_count_num} (distributed across {int(video_duration)}s)
        """
        
        if video_count > 0 and video_duration > 0:
                prompt += f"""

        ⚠️ VIDEO ANALYSIS REQUIREMENTS (CRITICAL):

        8. SCENE_BY_SCENE_ANALYSIS:
        - Generate EXACTLY {scene_count_num} scene objects
        - Cover FULL video from 0s to {int(video_duration)}s
        - Each scene ~{video_duration/scene_count_num:.1f}s long
        - Timestamp format: "X-Ys" (e.g., "0-{int(video_duration/scene_count_num)}s")
        - Example scenes:
            * "0-{int(video_duration/scene_count_num)}s"
            * "{int(video_duration/scene_count_num)}-{int(2*video_duration/scene_count_num)}s"
            * ...continuing to...
            * "{int(video_duration - video_duration/scene_count_num)}-{int(video_duration)}s"

        9. EMOTIONAL_JOURNEY:
        - Generate EXACTLY {emotion_count_num} emotion point objects
        - Span from "0s" to "{int(video_duration)}s"
        - Distribute evenly (every ~{emotion_interval:.1f}s)
        - Timestamp format: "Xs" (just the number with 's')
        - Example timestamps: "0s", "{int(emotion_interval)}s", "{int(2*emotion_interval)}s", ..., "{int(video_duration)}s"

        10. EMOTIONAL_ENGAGEMENT_SUMMARY:
            - peak_time_seconds must be between 0.0 and {video_duration}
            - Reference actual scenes from scene_by_scene_analysis

        THESE ARE MANDATORY. DO NOT GENERATE PLACEHOLDER VALUES LIKE "0-0s" OR SINGLE TIMESTAMPS.
        """

        else:
            prompt += f"""

    8. SCENE_BY_SCENE_ANALYSIS: Create {scene_count} with metrics
    9. EMOTIONAL_JOURNEY: Map {emotional_count} tracking emotional arc"""

        prompt += f"""

    10. VERBATIM_HIGHLIGHTS: 7 authentic quotes from {persona_age}, {persona_gender} respondents
        - Reference {project_brand} and {project_product} naturally
        - Reflect {interests_str} perspective
        - Address value propositions authentically

    11. OPTIMIZATION_RECOMMENDATIONS: Specific keep/improve/adjust/next_steps
        - Align with {campaign_objective}
        - Optimize for {media_channels_str}
        - Enhance KPI achievement ({kpis_str})
        - Strengthen {value_props_str} communication

    12. DEMOGRAPHIC_BREAKDOWN: Distribution based on persona ({persona_age}, {persona_gender})
        AGE: Put 60-70% in {age_min}-{age_max} bucket, distribute rest
        GENDER: Align with {persona_gender} split
        ALL PERCENTAGES MUST SUM TO 100%

    🚨 13. RESPONDENT_DATA [MANDATORY - CANNOT BE SKIPPED] 🚨
        YOU MUST GENERATE EXACTLY 20 COMPLETE RESPONDENT RECORDS
        THIS IS NON-NEGOTIABLE AND REQUIRED FOR CSV EXPORT
        
        REQUIREMENTS:
        ✓ EXACTLY 20 respondent objects (no more, no less)
        ✓ Respondent IDs: MUST be sequential integers 1001, 1002, 1003, ..., 1020
        ✓ Gender distribution: 
            * Match {persona_gender} split from demographic_breakdown
            * If "Male": 60-70% "M", rest "F" and "Other"
            * If "Female": 60-70% "F", rest "M" and "Other"
            * If "all genders": balanced mix ~40% M, 40% F, 20% Other
        ✓ Age distribution:
            * PRIMARY TARGET: 60-70% of respondents aged {age_min}-{age_max}
            * REALISTIC VARIATION: Don't use same age repeatedly
            * Examples for {age_min}-{age_max}: {age_min}, {age_min+2}, {age_min+5}, {age_max-3}, {age_max}, etc.
            * SPILLOVER: 30-40% in adjacent ranges (18-24, 25-34, 35-44, 45+)
        ✓ appeal_score: Integer 1-10
            * REFLECT CREATIVE QUALITY: High scores (7-10) only if creative is strong
            * PRODUCT MISMATCH: Scores 1-3 if wrong product shown
            * NATURAL VARIATION: Mix of scores, not all identical
            * CORRELATION: Should align with overall_performance_score
        ✓ brand_recall_aided: Integer 0 or 1 (BINARY ONLY)
            * HIGH RECALL (mostly 1): If {project_brand} branding is clear/prominent
            * LOW RECALL (mostly 0): If branding is subtle or wrong brand shown
            * DISTRIBUTION: Should match brand_linkage scores from audience_feedback
            * EXAMPLE PATTERNS: Strong brand = 85% with 1, weak = 40% with 1
        ✓ message_clarity: Integer 1-10
            * ALIGN WITH: clarity scores from audience_feedback section
            * REALISTIC: High (7-10) if {value_props_str} are clear
            * REALISTIC: Low (1-4) if message is confusing or mismatched
            * VARIATION: Not all same score
        ✓ purchase_intent: Float 0.0-1.0 (TWO DECIMAL PLACES)
            * CORRELATION: Should align with conversion_potential/100 from performance_insights
            * LOGIC: Higher for respondents with high appeal_score AND brand_recall=1
            * REALISTIC EXAMPLES: 0.23, 0.47, 0.65, 0.78, 0.89
            * AVERAGE: Should be approximately conversion_potential/100
            * VARIATION: Natural spread, not all clustered

        EXAMPLE RESPONDENT RECORDS:
        {{
            "respondent_id": 1001,
            "gender": "F",
            "age": {age_min + 3},
            "appeal_score": 8,
            "brand_recall_aided": 1,
            "message_clarity": 7,
            "purchase_intent": 0.72
        }},
        {{
            "respondent_id": 1002,
            "gender": "M",
            "age": {age_min + 7},
            "appeal_score": 6,
            "brand_recall_aided": 1,
            "message_clarity": 6,
            "purchase_intent": 0.54
        }},
        {{
            "respondent_id": 1003,
            "gender": "F",
            "age": {age_max - 2},
            "appeal_score": 9,
            "brand_recall_aided": 1,
            "message_clarity": 8,
            "purchase_intent": 0.81
        }}
        ... CONTINUE THROUGH respondent_id: 1020

        ⚠️ CRITICAL VALIDATION BEFORE SUBMITTING:
        □ Count respondent_data array length = EXACTLY 20?
        □ All respondent_ids are 1001-1020 sequential integers?
        □ Gender distribution matches demographic_breakdown percentages?
        □ 60-70% of ages fall within {age_min}-{age_max}?
        □ appeal_score reflects creative quality (low if wrong product)?
        □ brand_recall_aided is only 0 or 1 (not decimals)?
        □ message_clarity aligns with audience_feedback clarity?
        □ purchase_intent values are 0.0-1.0 floats with 2 decimals?
        □ purchase_intent average ≈ conversion_potential/100?

        IF ANY CHECK FAILS, REGENERATE RESPONDENT_DATA UNTIL ALL PASS

    === CRITICAL REQUIREMENTS ===
    ✓ FIRST: Verify assets match project - if iPhone shown but Nike shoes expected, FLAG IT
    ✓ Return COMPLETE JSON with ALL sections
    ✓ Use lowercase snake_case keys only
    ✓ Ground analysis in PROJECT CONTEXT but VALIDATE against ACTUAL assets
    ✓ If mismatch detected: All scores 1-2, explicitly state mismatch in takeaways/critiques
    ✓ Evaluate against stated VALUE PROPOSITIONS: {value_props_str}
    ✓ Consider MARKET MATURITY: {market_maturity}
    ✓ Assess KPI achievement: {kpis_str} targeting {kpi_target}
    ✓ Be HONEST: Low scores (1-2) if wrong product, (2-4) if weak execution, 5-6 average, 7+ only if strong
    ✓ Reference ACTUAL content shown in assets, not assumed content from project brief
    ✓ Verbatim quotes must reflect what consumers ACTUALLY see in the creative
    ✓ Demographic breakdown MUST match persona profile
    ✓ 🚨 RESPONDENT_DATA IS MANDATORY - MUST HAVE 20 RECORDS WITH REALISTIC VARIATION 🚨
    ✓ All feedback should reflect REAL CONSUMER perspective on what they actually see

    🚨 FINAL REMINDER: THE JSON RESPONSE WILL FAIL VALIDATION AND BE REJECTED IF:
    - respondent_data array is missing
    - respondent_data has fewer than 20 records
    - Any respondent record is missing required fields
    - brand_recall_aided contains non-binary values (must be 0 or 1 only)
    - purchase_intent is not a float between 0.0-1.0

    GENERATE THE COMPLETE JSON NOW WITH ALL 20 RESPONDENT RECORDS."""

        return prompt

    async def _download_image_content_async(self, image_url: str) -> Optional[dict]:
        """Returns dict with 'content' and 'mime_type'"""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor, self._download_image_sync, image_url
            )
            if response:
                content, mime_type = response
                encoded = base64.b64encode(content).decode('utf-8')
                return {"content": encoded, "mime_type": mime_type}
            return None
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return None

    def _download_image_sync(self, image_url: str) -> Optional[Tuple[bytes, str]]:
        """Returns (content, mime_type)"""
        response = self.session.get(image_url, timeout=15)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', 'image/jpeg')
        
        # Resize if too large
        content = response.content
        if len(content) > 15 * 1024 * 1024:  # 15MB
            from PIL import Image
            from io import BytesIO
            
            img = Image.open(BytesIO(content))
            img.thumbnail((2048, 2048))  # Max dimension
            
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            content = buffer.getvalue()
            content_type = 'image/jpeg'
        
        return content, content_type
    def _process_audio_sync(self, audio_url: str) -> dict:
        """Synchronous audio processing - OPTIMIZED"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                audio_path = self._download_audio(audio_url, temp_dir)
                if not audio_path:
                    return {"transcript": "", "acoustic_features": {}}
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as local_executor:
                    transcript_future = local_executor.submit(self._transcribe_audio_sync, audio_path)
                    acoustic_future = local_executor.submit(self._analyze_audio_acoustics_optimized, audio_path)
                    
                    transcript = transcript_future.result()
                    acoustic_features = acoustic_future.result()
                
                return {
                    "transcript": transcript,
                    "acoustic_features": acoustic_features
                }
        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")
            return {"transcript": "", "acoustic_features": {}}

    def _transcribe_audio_sync(self, audio_path: str) -> str:
        """Synchronous audio transcription"""
        try:
            with open(audio_path, "rb") as f:
                transcript = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f
                )
            return transcript.text
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            return ""

    @lru_cache(maxsize=128)
    def _analyze_audio_acoustics_optimized(self, audio_path: str) -> dict:
        """Optimized acoustic analysis with caching"""
        try:
            y, sr = librosa.load(audio_path, sr=16000, mono=True)
            duration = len(y) / sr
            
            features = {
                "duration_seconds": float(duration),
                "sample_rate": int(sr),
                "total_samples": len(y)
            }
            
            try:
                hop_length = 2048
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
                features["tempo_bpm"] = float(tempo)
                
                rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
                features["average_energy"] = float(np.mean(rms))
                features["energy_variance"] = float(np.var(rms))
                
                spectral_centroids = librosa.feature.spectral_centroid(
                    y=y, sr=sr, hop_length=hop_length
                )[0]
                features["spectral_centroid_mean"] = float(np.mean(spectral_centroids))
                
                zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]
                features["zero_crossing_rate"] = float(np.mean(zcr))
                
                energy_threshold = np.mean(rms) * 0.1
                silent_frames = rms < energy_threshold
                features["silence_ratio"] = float(np.mean(silent_frames))
                
                silence_changes = np.diff(silent_frames.astype(int))
                features["estimated_pause_count"] = int(np.sum(silence_changes == 1))
                
            except Exception as feat_e:
                logger.error(f"Error extracting features: {feat_e}")
                default_features = {
                    "tempo_bpm": 0, "average_energy": 0, "energy_variance": 0,
                    "spectral_centroid_mean": 0, "zero_crossing_rate": 0,
                    "silence_ratio": 0, "estimated_pause_count": 0
                }
                features.update(default_features)
            
            return features
            
        except Exception as e:
            logger.error(f"Error analyzing audio acoustics: {str(e)}")
            return {
                "duration_seconds": 0, "sample_rate": 0, "total_samples": 0,
                "tempo_bpm": 0, "average_energy": 0, "energy_variance": 0,
                "silence_ratio": 0, "estimated_pause_count": 0
            }

    def _extract_frames_optimized(self, video_path: str, temp_dir: str, max_frames: int = 10) -> List[str]:
        """Optimized frame extraction - REDUCED frame count"""
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
            frame_indices = np.linspace(0, total_frames - 1, max_frames, dtype=int)
            
            frames = []
            for i, frame_idx in enumerate(frame_indices):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    frame_filename = os.path.join(frames_dir, f"frame_{i:03d}.jpg")
                    success = cv2.imwrite(
                        frame_filename, frame, 
                        [cv2.IMWRITE_JPEG_QUALITY, 60]
                    )
                    
                    if success and os.path.exists(frame_filename):
                        frames.append(frame_filename)
            
            cap.release()
            return frames
            
        except Exception as e:
            logger.error(f"Error extracting frames: {str(e)}")
            return []
    
    def _download_audio(self, url: str, output_dir: str) -> Optional[str]:
        """Download audio file from URL - OPTIMIZED with session"""
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            if 'audio/mpeg' in content_type or 'audio/mp3' in content_type:
                ext = 'mp3'
            elif 'audio/wav' in content_type:
                ext = 'wav'
            elif 'audio/mp4' in content_type or 'audio/m4a' in content_type:
                ext = 'm4a'
            else:
                ext = 'mp3'
            
            audio_path = os.path.join(output_dir, f"audio.{ext}")
            with open(audio_path, 'wb') as f:
                f.write(response.content)
            
            return audio_path if os.path.exists(audio_path) else None
            
        except Exception as e:
            logger.error(f"Error downloading audio: {str(e)}")
            try:
                output_template = os.path.join(output_dir, "audio.%(ext)s")
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': output_template,
                    'extract_flat': False,
                    'quiet': True,
                    'no_warnings': True
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    actual_filename = filename.replace('.%(ext)s', f".{info['ext']}")
                    
                    if os.path.exists(actual_filename):
                        return actual_filename
                        
                return None
            except Exception as fallback_e:
                logger.error(f"Fallback audio download failed: {fallback_e}")
                return None

    def _download_video(self, url: str, output_dir: str) -> Optional[str]:
        """Download video using yt-dlp - OPTIMIZED"""
        try:
            output_template = os.path.join(output_dir, "video.%(ext)s")
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': output_template,
                'quiet': True,
                'no_warnings': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                actual_filename = filename.replace('.%(ext)s', f".{info['ext']}")
                
                if os.path.exists(actual_filename):
                    return actual_filename
                    
                for ext in ['mp4', 'webm', 'mkv']:
                    test_file = filename.replace('.%(ext)s', f'.{ext}')
                    if os.path.exists(test_file):
                        return test_file
                        
            return None
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            return None
    
    def _extract_and_transcribe(self, video_path: str, temp_dir: str) -> str:
        """Extract audio and transcribe - OPTIMIZED"""
        try:
            audio_path = os.path.join(temp_dir, "audio.wav")
            (
                ffmpeg
                .input(video_path)
                .output(audio_path, ac=1, ar=16000, **{'loglevel': 'error'})
                .run(overwrite_output=True, quiet=True)
            )
            
            if os.path.exists(audio_path):
                with open(audio_path, "rb") as f:
                    transcript = self.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f
                    )
                return transcript.text
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting/transcribing audio: {str(e)}")
            return ""
    
    async def close(self):
        """Clean up resources"""
        self.executor.shutdown(wait=True)
        self.session.close()