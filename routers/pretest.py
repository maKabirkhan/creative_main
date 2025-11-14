import logging
import csv
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from app.helpers.security import get_current_user
from app.helpers.db import supabase
from app.schemas.pretest import PretestRequest
from app.service.pretest_service import PretestService
from openai import OpenAI
from dotenv import load_dotenv
import os
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import tempfile
from typing import Dict, Any

logger = logging.getLogger(__name__)



load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
pretest_service = PretestService()

PRETEST_LIMITS = {
    "free": 5,
    "starter": 15,
    "professional": 50,
    "agency": 200,
    "enterprise": None 
}


async def generate_csv_report_with_respondents(result: Dict[str, Any], persona: Dict[str, Any]) -> str:
    """
    Generate a CSV report with respondent-level data matching the required format.
    Columns: respondent_id, gender, age, appeal_score, brand_recall_aided, message_clarity, purchase_intent
    """
    try:
        # Create a temporary file
        temp_dir = tempfile.gettempdir()
        csv_filename = f"pretest_{result.get('pretest_id', 'unknown')}.csv"
        csv_path = os.path.join(temp_dir, csv_filename)
        
        # Get respondent data from result
        respondent_data = result.get('respondent_data', [])
        
        if not respondent_data:
            raise ValueError("No respondent data available in the pretest result")
        
        # Define CSV headers matching the screenshot
        headers = [
            'respondent_id',
            'gender',
            'age',
            'appeal_score',
            'brand_recall_aided',
            'message_clarity',
            'purchase_intent'
        ]
        
        # Write CSV file
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for respondent in respondent_data:
                # Map the data to match the required format
                row = {
                    'respondent_id': respondent.get('respondent_id', ''),
                    'gender': respondent.get('gender', ''),
                    'age': respondent.get('age', ''),
                    'appeal_score': respondent.get('appeal_score', ''),
                    'brand_recall_aided': respondent.get('brand_recall_aided', ''),
                    'message_clarity': respondent.get('message_clarity', ''),
                    'purchase_intent': respondent.get('purchase_intent', '')
                }
                writer.writerow(row)
        
        logger.info(f"CSV report generated at: {csv_path} with {len(respondent_data)} respondents")
        return csv_path
        
    except Exception as e:
        logger.error(f"Error generating CSV report: {str(e)}")
        raise Exception(f"Failed to generate CSV report: {str(e)}")

def generate_pdf_report(pretest_data: dict, user_id: str, user_tier: str = "free") -> str:
    """Generate professional PDF report with optimized spacing and improved cover page"""
    try:
        pdf_filename = f"/tmp/pretest_{pretest_data['pretest_id']}.pdf"
        doc = SimpleDocTemplate(pdf_filename, pagesize=A4,
                               rightMargin=0.75*inch, leftMargin=0.75*inch,
                               topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        styles = getSampleStyleSheet()
        elements = []
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            keepWithNext=True
        )
        
        subtitle_style = ParagraphStyle(
            'SubTitle',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#555555'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=8,
            spaceBefore=16,
            fontName='Helvetica-Bold',
            keepWithNext=True
        )
        
        body_style = ParagraphStyle(
            'BodyText',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            spaceAfter=6,
            alignment=TA_LEFT,
            fontName='Helvetica',
            leading=14
        )
        
        bullet_style = ParagraphStyle(
            'BulletPoint',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            leftIndent=15,
            spaceAfter=4,
            fontName='Helvetica',
            leading=14
        )
        
        # Cover page label style (left column)
        cover_label_style = ParagraphStyle(
            'CoverLabel',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#1a1a1a'),
            fontName='Helvetica-Bold',
            leading=16
        )
        
        # Cover page value style (right column)
        cover_value_style = ParagraphStyle(
            'CoverValue',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            fontName='Helvetica',
            leading=16
        )
        
        # Check if emotional/scene data exists (regardless of video)
        has_emotional_data = bool(pretest_data.get('emotional_engagement_summary') and 
                                 pretest_data.get('emotional_engagement_summary', {}).get('peak_emotion'))
        has_scene_data = bool(pretest_data.get('scene_by_scene_analysis'))
        has_emotional_journey = bool(pretest_data.get('emotional_journey'))
        
        # 1. Cover Page with new heading
        elements.append(Spacer(1, 2.2*inch))
        
        # Main heading
        elements.append(Paragraph("Creative Pretesting Research", title_style))
        elements.append(Spacer(1, 0.3*inch))
        
        creative_type = pretest_data.get('creative_type', 'Multi-Asset').replace('-', ' ').title()
        test_date = datetime.now().strftime('%B %Y')
        
        # Cover table with improved styling
        cover_data = [
            [Paragraph("Campaign:", cover_label_style), Paragraph(f"{creative_type} Creative Test", cover_value_style)],
            [Paragraph("Test Date:", cover_label_style), Paragraph(test_date, cover_value_style)],
            [Paragraph("Plan Tier:", cover_label_style), Paragraph(user_tier.title(), cover_value_style)],
            [Paragraph("Conducted by:", cover_label_style), Paragraph("BuzzInsider Research Labs", cover_value_style)]
        ]
        
        cover_table = Table(cover_data, colWidths=[2.2*inch, 4.3*inch])
        cover_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(cover_table)
        elements.append(PageBreak())
        
        # 2. Objectives
        elements.append(Paragraph("1. Objectives", heading_style))
        
        objectives = pretest_data.get('objectives', [])
        if not objectives:
            objectives = [
                "Evaluate creative effectiveness across key performance metrics",
                "Identify emotional engagement and brand recall opportunities",
                "Provide diagnostic feedback for creative optimization before launch"
            ]
        
        for obj in objectives:
            elements.append(Paragraph(f"• {obj}", bullet_style))
        
        elements.append(Spacer(1, 12))
        
        # 3. Methodology
        elements.append(Paragraph("2. Methodology", heading_style))
        
        methodology = pretest_data.get('methodology', {})
        sample_size = methodology.get('sample_size', 'N/A')
        audience = methodology.get('audience', 'N/A')
        gender_split = ', '.join(methodology.get('gender_split', ['N/A']))
        design = methodology.get('design', 'N/A')
        
        elements.append(Paragraph(f"<b>Sample:</b> {sample_size} respondents ({audience}, {gender_split})", body_style))
        elements.append(Paragraph(f"<b>Design:</b> {design}", body_style))
        elements.append(Paragraph(f"<b>Stimuli:</b> Creative assets hosted in test platform", body_style))
        elements.append(Spacer(1, 6))
        
        elements.append(Paragraph("<b>Measures:</b>", body_style))
        metrics = methodology.get('metrics_measured', [])
        if not metrics:
            metrics = ["Ad Appeal", "Brand Recall", "Message Clarity", "Purchase Intent", "Emotional Engagement"]
        
        for metric in metrics:
            elements.append(Paragraph(f"  • {metric.replace('_', ' ').title()}", bullet_style))
        
        elements.append(Paragraph(f"  • Normative Comparison vs Category", bullet_style))
        elements.append(Spacer(1, 12))
        
        # 4. Key Takeaways
        elements.append(Paragraph("3. Key Takeaways", heading_style))

        perf = pretest_data.get('performance_insights', {})
        audience_survey = pretest_data.get('audience_feedback', {}).get('survey_responses', {})
        
        # Build performance metrics table
        table_data = [["Metric", "Score", "Category Norm"]]
        
        overall_score = perf.get('overall_performance_score', 'N/A')
        table_data.append(["Ad Appeal", str(overall_score), "7.0"])
        
        engagement_score = perf.get('engagement', 'N/A')
        table_data.append(["Brand Recall (Aided)", f"{engagement_score}%", "80%"])
        
        clarity = audience_survey.get('clarity', 'N/A')
        table_data.append(["Message Clarity", f"{clarity}/7", "5.5/7"])
        
        conversion = perf.get('conversion_potential', 'N/A')
        table_data.append(["Purchase Intent", f"{conversion}%", "65%"])
        
        # Add emotional engagement if data exists
        if has_emotional_data:
            craft = audience_survey.get('craft_execution', 'N/A')
            table_data.append(["Emotional Engagement (Peak)", str(craft), "6.4"])

        col_widths = [2.5*inch, 1.5*inch, 1.5*inch]
        metrics_table = Table(table_data, colWidths=col_widths)

        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
            ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ]))

        elements.append(metrics_table)
        elements.append(Spacer(1, 10))
        
        norm_comp = pretest_data.get('normative_comparison', {})
        percentile = norm_comp.get('top_percentile', 'above average')
        standing = norm_comp.get('category_standing', 'Strong performance across key metrics.')

        summary_text = f"<b>Summary:</b> This creative performs in the <b>{percentile}</b> for the category. {standing}"
        elements.append(Paragraph(summary_text, body_style))
        elements.append(Spacer(1, 12))
        
        section_number = 4
        
        # Emotional Engagement Section (if data exists)
        if has_emotional_data:
            elements.append(Paragraph(f"{section_number}. Emotional Engagement – Facial Coding Summary", heading_style))
            
            emotion_data = pretest_data.get('emotional_engagement_summary', {})
            peak_emotion = emotion_data.get('peak_emotion', 'Interest').title()
            peak_time = emotion_data.get('peak_time_seconds', 'N/A')
            summary = emotion_data.get('summary', 'The creative maintains engagement throughout.')
            low_engagement = emotion_data.get('low_engagement_scenes', [])
            
            elements.append(Paragraph(f"<b>Peak Emotion:</b> {peak_emotion} at {peak_time} seconds", body_style))
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(summary, body_style))
            
            if low_engagement:
                elements.append(Spacer(1, 6))
                elements.append(Paragraph(f"<b>Low Engagement Scenes:</b> {', '.join(low_engagement)}", body_style))
            
            elements.append(Spacer(1, 12))
            section_number += 1
        
        # Scene-by-Scene Analysis (if data exists)
        if has_scene_data:
            elements.append(Paragraph(f"{section_number}. Diagnostic Heatmap (Scene-by-Scene Ratings)", heading_style))
            
            scene_analysis = pretest_data.get('scene_by_scene_analysis', [])
            scene_data = [["Scene", "Avg. Attention", "Positive Emotion", "Confusion", "Branding"]]
            
            for scene in scene_analysis:
                scene_name = scene.get('scene_name', 'N/A')
                timestamp = scene.get('timestamp_range', '')
                scene_label = f"{scene_name} ({timestamp})" if timestamp else scene_name
                
                scene_data.append([
                    scene_label,
                    str(scene.get('attention_score', 'N/A')),
                    str(scene.get('positive_emotion', 'N/A')),
                    f"{scene.get('confusion_level', 'N/A')}%",
                    f"{scene.get('branding_visibility', 'N/A')}%"
                ])
            
            scene_table = Table(scene_data, colWidths=[2*inch, 1.2*inch, 1.2*inch, 1*inch, 1*inch])
            scene_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7f7f7f')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8f9fa'), colors.white]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ]))
            elements.append(scene_table)
            
            elements.append(Spacer(1, 12))
            section_number += 1
        
        # Verbatim Highlights
        elements.append(Paragraph(f"{section_number}. Verbatim Highlights", heading_style))
        
        verbatims = pretest_data.get('verbatim_highlights', [])
        if verbatims:
            for verbatim in verbatims[:8]:
                elements.append(Paragraph(f'• "{verbatim}"', bullet_style))
        else:
            elements.append(Paragraph('• "The creative captures attention effectively."', bullet_style))
            elements.append(Paragraph('• "Brand message could be clearer."', bullet_style))
            elements.append(Paragraph('• "Visual appeal is strong."', bullet_style))
        
        elements.append(Spacer(1, 12))
        section_number += 1
        
        # Recommendations
        elements.append(Paragraph(f"{section_number}. Recommendations", heading_style))
        
        opt_rec = pretest_data.get('optimization_recommendations', {})
        
        keep_items = opt_rec.get('keep', [])
        if keep_items:
            elements.append(Paragraph("<b>Keep:</b>", body_style))
            for item in keep_items:
                elements.append(Paragraph(f"  • {item}", bullet_style))
            elements.append(Spacer(1, 6))
        
        improve_items = opt_rec.get('improve', [])
        if improve_items:
            elements.append(Paragraph("<b>Improve:</b>", body_style))
            for item in improve_items:
                elements.append(Paragraph(f"  • {item}", bullet_style))
            elements.append(Spacer(1, 6))
        
        adjust_items = opt_rec.get('adjust', [])
        if adjust_items:
            elements.append(Paragraph("<b>Adjust:</b>", body_style))
            for item in adjust_items:
                elements.append(Paragraph(f"  • {item}", bullet_style))
            elements.append(Spacer(1, 6))
        
        next_steps = opt_rec.get('next_steps', '')
        if next_steps:
            elements.append(Paragraph(f"<b>Next Step:</b> {next_steps}", body_style))
        
        elements.append(Spacer(1, 12))
        section_number += 1
        
        # Normative Comparison
        elements.append(Paragraph(f"{section_number}. Normative Comparison (vs Category)", heading_style))
        
        norm = pretest_data.get('normative_comparison', {})
        
        elements.append(Paragraph(f"• Performance in <b>{norm.get('top_percentile', 'top 50%')}</b> for the category", bullet_style))
        elements.append(Paragraph(f"• {norm.get('category_standing', 'Strong competitive positioning')}", bullet_style))
        elements.append(Paragraph(f"• Memorability: {norm.get('memorability_rank', 'at norm')}", bullet_style))
        elements.append(Paragraph(f"• Branding effectiveness: {norm.get('branding_effectiveness', 'above norm')}", bullet_style))
        
        elements.append(Spacer(1, 12))
        section_number += 1
        
        # Appendices
        elements.append(Paragraph(f"{section_number}. Appendices", heading_style))
        elements.append(Paragraph("<b>A. Demographics</b>", body_style))
        elements.append(Spacer(1, 6))
        
        demo = pretest_data.get('demographic_breakdown', {})
        demo_data = [
            ["Segment", "% of Sample"],
            ["18–24", f"{demo.get('age_18_24', 0)}%"],
            ["25–34", f"{demo.get('age_25_34', 0)}%"],
            ["35–44", f"{demo.get('age_35_44', 0)}%"],
            ["45+", f"{demo.get('age_45_plus', 0)}%"],
            ["Male", f"{demo.get('male', 0)}%"],
            ["Female", f"{demo.get('female', 0)}%"],
        ]
        
        demo_table = Table(demo_data, colWidths=[3*inch, 2*inch])
        demo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ]))
        elements.append(demo_table)
        
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("<b>B. Method Detail</b>", body_style))
        elements.append(Spacer(1, 6))
        
        tech = pretest_data.get('technical_appendix', {})
        
        elements.append(Paragraph(f"<b>Platform:</b> BuzzInsider Creative Lab v1.3", body_style))
        elements.append(Paragraph(f"<b>Metrics Scales:</b> {tech.get('metrics_scale', '1–7 Likert scale')}", body_style))
        elements.append(Paragraph(f"<b>Statistical Confidence:</b> {tech.get('statistical_confidence', '95%')}", body_style))
        
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("<b>Deliverable Package Summary</b>", body_style))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("<b>File Provided:</b>", body_style))
        elements.append(Paragraph("  1. PDF Report", bullet_style))
    
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("End of Report", 
                                 ParagraphStyle('End', parent=styles['Normal'], 
                                              fontSize=10, alignment=TA_CENTER,
                                              textColor=colors.HexColor('#999999'),
                                              fontName='Helvetica-Bold')))
        
        doc.build(elements)
        logger.info(f"PDF report generated: {pdf_filename}")
        return pdf_filename
        
    except Exception as e:
        logger.error(f"Failed to generate PDF report: {str(e)}")
        raise

def upload_pdf_to_supabase(pdf_path: str, user_id: str, filename: str) -> str:
    """Upload PDF to Supabase storage"""
    try:
        storage_path = f"reports/{user_id}/{filename}"
        
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
        
        supabase.storage.from_('creative-asset').upload(
            path=storage_path,
            file=pdf_data,
            file_options={
                "content-type": "application/pdf",
                "upsert": "true"
            }
        )
        
        public_url = supabase.storage.from_('creative-asset').get_public_url(storage_path)
        logger.info(f"PDF uploaded to Supabase: {storage_path}")
        return public_url
        
    except Exception as e:
        logger.error(f"Failed to upload PDF: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload PDF: {str(e)}"
        )

def check_pretest_usage_limit(user_id: str, tier: str) -> tuple[bool, int, int]:
    """Check pretest usage limit"""
    limit = PRETEST_LIMITS.get(tier.lower())
    
    if limit is None:
        return True, 0, -1
    
    try:
        user_response = (
            supabase.table("users")
            .select("pretests_count")
            .eq("id", user_id)
            .execute()
        )
        
        if not user_response.data:
            logger.error(f"User {user_id} not found")
            return True, 0, limit
        
        current_count = user_response.data[0].get("pretests_count", 0)
        can_proceed = current_count < limit
        
        return can_proceed, current_count, limit
        
    except Exception as e:
        logger.error(f"Error checking pretest usage: {str(e)}")
        return True, 0, limit

@router.post("/create")
async def create_pretest(
    request: PretestRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create and run a pretest analysis for creative content.
    Supports multiple creative IDs including multiple images and audio files.
    
    Report generation by tier:
    - Free: No reports
    - Starter: PDF report only
    - Professional: PDF and CSV reports
    - Agency: PDF and CSV reports
    - Enterprise: PDF and CSV reports (unlimited)
    
    Usage limits by tier:
    - Free: 5 pretests
    - Starter: 15 pretests
    - Professional: 50 pretests
    - Agency: 200 pretests
    - Enterprise: Unlimited
    """
    try:
        user_id = current_user["id"]
        
        subscription_resp = (
            supabase.table("subscriptions")
            .select("tier, status")
            .eq("user_id", user_id)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        
        user_tier = subscription_resp.data[0]["tier"].lower() if subscription_resp.data else "free"
        
        
        can_proceed, current_count, limit = check_pretest_usage_limit(str(user_id), user_tier)
        
        if not can_proceed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Pretest limit reached. You have used {current_count} of {limit} pretests available on the {user_tier.title()} plan. Please upgrade to continue."
            )
        
        logger.info(f"User {user_id} on {user_tier} plan: {current_count}/{limit if limit else 'unlimited'} pretests used")
        
        persona_id = int(request.persona_id)
        creative_ids = request.creative_ids

        if not isinstance(creative_ids, list) or len(creative_ids) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="creative_ids must be a non-empty list"
            )

        persona_response = (
            supabase.table("personas")
            .select("*")
            .eq("id", persona_id)
            .execute()
        )
        
        if not persona_response.data:
            raise HTTPException(status_code=404, detail="Persona not found")
        
        persona = persona_response.data[0]

        if persona["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="You do not own this persona")

        creative_assets_response = (
            supabase.table("creative_assets")
            .select("*")
            .in_("id", creative_ids)
            .execute()
        )
        
        creative_assets = creative_assets_response.data if creative_assets_response.data else []

        if not creative_assets or len(creative_assets) != len(creative_ids):
            raise HTTPException(
                status_code=404, 
                detail="One or more creative assets not found"
            )

        project_ids = list(set([asset["project_id"] for asset in creative_assets]))
        projects_response = (
            supabase.table("projects")
            .select("id, user_id")
            .in_("id", project_ids)
            .execute()
        )
        
        projects_map = {p["id"]: p["user_id"] for p in projects_response.data}
        
        for asset in creative_assets:
            project_user_id = projects_map.get(asset["project_id"])
            if not project_user_id or project_user_id != user_id:
                raise HTTPException(
                    status_code=403,
                    detail=f"Creative asset {asset['id']} does not belong to your project"
                )
        project_id = creative_assets[0]["project_id"]
        project = (
            supabase.table("projects")
            .select("*")
            .eq("id", project_id)
            .single()
            .execute()
        )
        project_data = project.data
        filtered_project = {
            "name": project_data.get("name"),
            "brand": project_data.get("brand"),
            "product": project_data.get("product"),
            "product_service_type": project_data.get("product_service_type"),
            "category": project_data.get("category"),
            "market_maturity": project_data.get("market_maturity"),
            "campaign_objective": project_data.get("campaign_objective"),
            "value_propositions": project_data.get("value_propositions"),
            "media_channels": project_data.get("media_channels"),
            "kpis": project_data.get("kpis"),
            "kpi_target": project_data.get("kpi_target")
        }

        filtered_assets = []
        
        for asset in creative_assets:
            asset_type = asset["type"].lower()

            if asset_type in ["audio", "image", "video"]:
                if not asset.get("file_url"):
                    logger.warning(f"Asset {asset['id']} of type {asset_type} missing file_url")
                    continue
                    
                filtered_assets.append({
                    "id": asset["id"],
                    "type": asset["type"],
                    "file_url": asset["file_url"]
                })
                
            elif asset_type == "text":
                text_asset = {
                    "id": asset["id"],
                    "type": asset["type"],
                    "ad_copy": asset.get("ad_copy", "")
                }
                
                if asset.get("voice_script"):
                    text_asset["voice_script"] = asset["voice_script"]
                    
                filtered_assets.append(text_asset)

        if not filtered_assets:
            raise HTTPException(
                status_code=400,
                detail="No valid assets found to analyze"
            )

        asset_summary = {}
        for asset in filtered_assets:
            asset_type = asset["type"].lower()
            asset_summary[asset_type] = asset_summary.get(asset_type, 0) + 1
        
        logger.info(f"Processing pretest with assets: {asset_summary}")

        filtered_persona = {
            "audience_type": persona.get("audience_type"),
            "geography": persona.get("geography"),
            "age_min": persona.get("age_min"),
            "age_max": persona.get("age_max"),
            "income_min": persona.get("income_min"),
            "income_max": persona.get("income_max"),
            "gender": persona.get("gender"),
            "purchase_frequency": persona.get("purchase_frequency"),
            "interests": persona.get("interests"),
            "life_stage": persona.get("life_stage"),
            "category_involvement": persona.get("category_involvement"),
            "decision_making_style": persona.get("decision_making_style"),
            "min_reach": persona.get("min_reach"),
            "max_reach": persona.get("max_reach"),
            "efficiency": persona.get("efficiency"),
            "platforms": persona.get("platforms"),
            "peak_activity": persona.get("peak_activity"),
            "engagement": persona.get("engagement"),
            "clarity": persona.get("clarity"),
            "relevance": persona.get("relevance"),
            "distinctiveness": persona.get("distinctiveness"),
            "brand_fit": persona.get("brand_fit"),
            "emotion": persona.get("emotion"),
            "cta": persona.get("cta"),
            "inclusivity": persona.get("inclusivity"),
        }

        request_body_data = request.dict()
        request_body_data.pop("persona_id", None)

        request_data = {
            "persona": filtered_persona,
            "creative_assets": filtered_assets,
            "request_body": request_body_data,
            "project": filtered_project,
        }

        logger.info(f"Prepared request_data with {len(filtered_assets)} assets")

        result = await pretest_service.create_pretest(
            user_id=str(user_id),
            request_data=request_data,
            user_tier=user_tier
        )
        
        report_urls = {}
        
        if user_tier in ["starter", "professional", "agency", "enterprise"]:
            try:
                pdf_filename = f"pretest_{result.get('pretest_id')}.pdf"
                pdf_path = generate_pdf_report(result, str(user_id), user_tier)
                pdf_url = upload_pdf_to_supabase(pdf_path, str(user_id), pdf_filename)
                report_urls["pdf"] = pdf_url
                logger.info(f"PDF report generated and uploaded for pretest {result.get('pretest_id')}")
            except Exception as e:
                logger.error(f"Failed to generate/upload PDF report: {str(e)}")
        if user_tier in ["professional", "agency", "enterprise"]:
            try:
                csv_filename = f"pretest_{result.get('pretest_id')}.csv"
                # Pass both pretest result and persona data to generate respondent-level CSV
                csv_path = await generate_csv_report_with_respondents(result, filtered_persona)
                csv_url = upload_csv_to_supabase(csv_path, str(user_id), csv_filename)
                report_urls["csv"] = csv_url
                logger.info(f"CSV report generated and uploaded for pretest {result.get('pretest_id')}")
            except Exception as e:
                logger.error(f"Failed to generate/upload CSV report: {str(e)}")
        
        result["report_urls"] = report_urls
        
        try:
            supabase.table("users").update({
                "pretests_count": current_count + 1
            }).eq("id", user_id).execute()
            
            logger.info(f"Updated pretest count for user {user_id}: {current_count + 1}")
        except Exception as e:
            logger.error(f"Failed to update pretest count: {str(e)}")
        
        logger.info(f"Pretest created successfully: {result.get('pretest_id')}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating pretest: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to create pretest"
        )

def upload_csv_to_supabase(csv_path: str, user_id: str, filename: str) -> str:
    """Upload CSV to Supabase storage"""
    try:
        storage_path = f"reports/{user_id}/{filename}"
        
        with open(csv_path, 'rb') as f:
            csv_data = f.read()
        
        supabase.storage.from_("creative-asset").upload(
            path=storage_path,
            file=csv_data,
            file_options={"content-type": "text/csv", "upsert": "true"}
        )
        
        csv_url = supabase.storage.from_("creative-asset").get_public_url(storage_path)
        logger.info(f"CSV uploaded to Supabase: {csv_url}")
        return csv_url
        
    except Exception as e:
        logger.error(f"Failed to upload CSV: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload CSV: {str(e)}"
        )

@router.get("/usage")
async def get_pretest_usage(current_user: dict = Depends(get_current_user)):
    """
    Get the current user's pretest usage and remaining limit.
    Returns how many pretests are used, remaining, and total limit based on subscription tier.
    """
    try:
        user_id = current_user["id"]

        subscription_resp = (
            supabase.table("subscriptions")
            .select("tier, status")
            .eq("user_id", user_id)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        user_tier = (
            subscription_resp.data[0]["tier"].lower()
            if subscription_resp.data
            else "free"
        )

        can_proceed, current_count, limit = check_pretest_usage_limit(str(user_id), user_tier)

        if limit is None:
            return {
                "tier": user_tier.title(),
                "used": current_count,
                "remaining": "Unlimited",
                "limit": "Unlimited"
            }

        remaining = max(limit - current_count, 0)

        return {
            "tier": user_tier.title(),
            "used": current_count,
            "remaining": remaining,
            "limit": limit,
            
        }

    except Exception as e:
        logger.error(f"Error fetching pretest usage: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch pretest usage information"
        )
