# from fastapi import APIRouter, HTTPException, Depends, status
# from fastapi.security import HTTPBearer
# import logging
# import os
# from datetime import datetime
# import tempfile
# from reportlab.lib.pagesizes import A4
# from reportlab.lib import colors
# from reportlab.lib.units import inch
# from reportlab.lib.enums import TA_CENTER
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.platypus import (
#     SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
#     PageBreak
# )
# from app.helpers.security import get_current_user
# from app.service.simulation_service import SimulationService
# from app.helpers.db import supabase

# logger = logging.getLogger(__name__)
# router = APIRouter()
# security = HTTPBearer()
# simulation_service = SimulationService()

# def create_enhanced_pdf(result, variant_a, variant_b, user_id, user_tier, pdf_path):
#     """Generate an enhanced, visually appealing PDF report"""
    
#     doc = SimpleDocTemplate(pdf_path, pagesize=A4, 
#                            rightMargin=0.75*inch, leftMargin=0.75*inch,
#                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    
#     styles = getSampleStyleSheet()
#     elements = []
    
#     # Custom styles
#     title_style = ParagraphStyle(
#         'CustomTitle',
#         parent=styles['Heading1'],
#         fontSize=24,
#         textColor=colors.HexColor('#1a1a1a'),
#         spaceAfter=30,
#         alignment=TA_CENTER,
#         fontName='Helvetica-Bold'
#     )
    
#     heading_style = ParagraphStyle(
#         'CustomHeading',
#         parent=styles['Heading2'],
#         fontSize=16,
#         textColor=colors.HexColor('#2c3e50'),
#         spaceAfter=12,
#         spaceBefore=12,
#         fontName='Helvetica-Bold'
#     )
    
#     subheading_style = ParagraphStyle(
#         'CustomSubHeading',
#         parent=styles['Heading3'],
#         fontSize=13,
#         textColor=colors.HexColor('#34495e'),
#         spaceAfter=8,
#         fontName='Helvetica-Bold'
#     )
    
#     elements.append(Paragraph("A/B SIMULATION REPORT", title_style))
#     elements.append(Spacer(1, 20))
    
#     metadata = [
#         ["Report Details", ""],
#         ["Plan Tier:", user_tier.title()],
#         ["Generated On:", datetime.now().strftime('%B %d, %Y at %H:%M:%S')],
#     ]
    
#     meta_table = Table(metadata, colWidths=[2*inch, 4*inch])
#     meta_table.setStyle(TableStyle([
#         ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
#         ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#         ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
#         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#         ('FONTSIZE', (0, 0), (-1, 0), 12),
#         ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
#         ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
#         ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
#         ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
#     ]))
#     elements.append(meta_table)
#     elements.append(Spacer(1, 30))
    
#     comp_insights = result.get('comparative_insights', {})
#     winner = comp_insights.get('winner', 'N/A').replace('_', ' ').title()
#     confidence = comp_insights.get('confidence_score', 0)
    
#     elements.append(Paragraph("🏆 WINNER", heading_style))
#     winner_data = [
#         [f"{winner}", f"Confidence: {confidence}%"]
#     ]
#     winner_table = Table(winner_data, colWidths=[3*inch, 3*inch])
#     winner_table.setStyle(TableStyle([
#         ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#505351")),
#         ('TEXTCOLOR', (0, 0), (-1, -1), colors.whitesmoke),
#         ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#         ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
#         ('FONTSIZE', (0, 0), (-1, -1), 14),
#         ('PADDING', (0, 0), (-1, -1), 12),
#     ]))
#     elements.append(winner_table)
#     elements.append(Spacer(1, 20))
    
#     # Performance Comparison
#     elements.append(Paragraph("📊 PERFORMANCE COMPARISON", heading_style))
    
#     var_a = result.get('variant_a_results', {})
#     var_b = result.get('variant_b_results', {})
#     overall_comp = result.get('overall_effectiveness_comparison', {})
    
#     performance_data = [
#         ["Metric", "Variant A", "Variant B", "Difference"],
#         ["Engagement Score", 
#          f"{var_a.get('engagement_score', 0)}", 
#          f"{var_b.get('engagement_score', 0)}",
#          f"+{var_b.get('engagement_score', 0) - var_a.get('engagement_score', 0)}"],
#         ["Relevance Score", 
#          f"{var_a.get('relevance_score', 0)}", 
#          f"{var_b.get('relevance_score', 0)}",
#          f"+{var_b.get('relevance_score', 0) - var_a.get('relevance_score', 0)}"],
#         ["Click-Through Score", 
#          f"{var_a.get('click_through_score', 0)}", 
#          f"{var_b.get('click_through_score', 0)}",
#          f"+{var_b.get('click_through_score', 0) - var_a.get('click_through_score', 0)}"],
#         ["Conversion Potential", 
#          f"{var_a.get('conversion_potential', 0)}", 
#          f"{var_b.get('conversion_potential', 0)}",
#          f"+{var_b.get('conversion_potential', 0) - var_a.get('conversion_potential', 0)}"],
#         ["Overall Performance", 
#          f"{var_a.get('overall_performance', 0)}", 
#          f"{var_b.get('overall_performance', 0)}",
#          f"+{overall_comp.get('relative_increase', 0):.2f}%"],
#     ]
    
#     perf_table = Table(performance_data, colWidths=[2*inch, 1.3*inch, 1.3*inch, 1.4*inch])
#     perf_table.setStyle(TableStyle([
#         ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
#         ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#         ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#         ('FONTSIZE', (0, 0), (-1, 0), 11),
#         ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
#         ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
#         ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
#         ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
#         ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
#         ('TEXTCOLOR', (3, 1), (3, -1), colors.HexColor("#272B29")),
#         ('FONTNAME', (3, 1), (3, -1), 'Helvetica-Bold'),
#     ]))
#     elements.append(perf_table)
#     elements.append(Spacer(1, 20))
    
#     # Detailed Metrics
#     elements.append(Paragraph("🎯 DETAILED METRICS", heading_style))
    
#     detailed_data = [
#         ["Quality Metric", "Variant A", "Variant B"],
#         ["Clarity Score", f"{var_a.get('clarity_score', 0)}/10", f"{var_b.get('clarity_score', 0)}/10"],
#         ["Brand Linkage", f"{var_a.get('brand_linkage_score', 0)}/10", f"{var_b.get('brand_linkage_score', 0)}/10"],
#         ["Relevance Detail", f"{var_a.get('relevance_detail_score', 0)}/10", f"{var_b.get('relevance_detail_score', 0)}/10"],
#         ["Distinctiveness", f"{var_a.get('distinctiveness_score', 0)}/10", f"{var_b.get('distinctiveness_score', 0)}/10"],
#         ["Persuasion", f"{var_a.get('persuasion_score', 0)}/10", f"{var_b.get('persuasion_score', 0)}/10"],
#         ["CTA Clarity", f"{var_a.get('cta_clarity_score', 0)}/10", f"{var_b.get('cta_clarity_score', 0)}/10"],
#         ["Craft Score", f"{var_a.get('craft_score', 0)}/10", f"{var_b.get('craft_score', 0)}/10"],
#     ]
    
#     detailed_table = Table(detailed_data, colWidths=[2.5*inch, 1.75*inch, 1.75*inch])
#     detailed_table.setStyle(TableStyle([
#         ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#7f7f7f")),
#         ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#         ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#         ('FONTSIZE', (0, 0), (-1, 0), 11),
#         ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
#         ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8f9fa'), colors.white]),
#         ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
#         ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
#     ]))
#     elements.append(detailed_table)
#     elements.append(Spacer(1, 30))
    
#     # Page Break
#     elements.append(PageBreak())
    
#     # Variant A Details
#     elements.append(Paragraph("📋 VARIANT A - DETAILED ANALYSIS", heading_style))
#     elements.append(Spacer(1, 10))
    
#     elements.append(Paragraph("Campaign Content:", subheading_style))
#     elements.append(Paragraph(f"<b>Headline:</b> {variant_a.get('headline', 'N/A')}", styles['Normal']))
#     elements.append(Paragraph(f"<b>Title:</b> {variant_a.get('title', 'N/A')}", styles['Normal']))
#     elements.append(Paragraph(f"<b>Description:</b> {variant_a.get('description', 'N/A')}", styles['Normal']))
#     elements.append(Spacer(1, 15))
    
#     # Variant A Perspectives
#     persona_persp_a = var_a.get('persona_perspective', {})
#     elements.append(Paragraph("Persona Perspective:", subheading_style))
#     elements.append(Paragraph(f"<i>{persona_persp_a.get('description', 'N/A')}</i>", styles['Normal']))
#     elements.append(Paragraph(f'<b>Feedback:</b> "{persona_persp_a.get("feedback", "N/A")}"', styles['Normal']))
#     elements.append(Paragraph(f"<b>Sentiment:</b> {persona_persp_a.get('sentiment', 'N/A').upper()}", styles['Normal']))
#     elements.append(Spacer(1, 10))
    
#     cd_persp_a = var_a.get('creative_director_perspective', {})
#     elements.append(Paragraph("Creative Director Perspective:", subheading_style))
#     elements.append(Paragraph(f"<i>{cd_persp_a.get('description', 'N/A')}</i>", styles['Normal']))
#     elements.append(Paragraph(f'<b>Feedback:</b> "{cd_persp_a.get("feedback", "N/A")}"', styles['Normal']))
#     elements.append(Spacer(1, 10))
    
#     gen_persp_a = var_a.get('general_audience_perspective', {})
#     elements.append(Paragraph("General Audience Perspective:", subheading_style))
#     elements.append(Paragraph(f"<i>{gen_persp_a.get('description', 'N/A')}</i>", styles['Normal']))
#     elements.append(Paragraph(f'<b>Feedback:</b> "{gen_persp_a.get("feedback", "N/A")}"', styles['Normal']))
#     elements.append(Spacer(1, 15))
    
#     # Variant A Emotions & Takeaway
#     emotions_a = ', '.join(var_a.get('emotions_triggered', []))
#     elements.append(Paragraph(f"<b>Emotions Triggered:</b> {emotions_a}", styles['Normal']))
#     elements.append(Paragraph(f"<b>Primary Takeaway:</b> {var_a.get('primary_takeaway', 'N/A')}", styles['Normal']))
#     elements.append(Spacer(1, 10))
    
#     tech_assess_a = var_a.get('technical_assessment', [])
#     elements.append(Paragraph("<b>Technical Assessment:</b>", styles['Normal']))
#     for item in tech_assess_a:
#         elements.append(Paragraph(f"• {item}", styles['Normal']))
    
#     elements.append(Spacer(1, 30))
#     elements.append(PageBreak())
    
#     # Variant B Details
#     elements.append(Paragraph("📋 VARIANT B - DETAILED ANALYSIS", heading_style))
#     elements.append(Spacer(1, 10))
    
#     elements.append(Paragraph("Campaign Content:", subheading_style))
#     elements.append(Paragraph(f"<b>Headline:</b> {variant_b.get('headline', 'N/A')}", styles['Normal']))
#     elements.append(Paragraph(f"<b>Title:</b> {variant_b.get('title', 'N/A')}", styles['Normal']))
#     elements.append(Paragraph(f"<b>Description:</b> {variant_b.get('description', 'N/A')}", styles['Normal']))
#     elements.append(Spacer(1, 15))
    
#     # Variant B Perspectives
#     persona_persp_b = var_b.get('persona_perspective', {})
#     elements.append(Paragraph("Persona Perspective:", subheading_style))
#     elements.append(Paragraph(f"<i>{persona_persp_b.get('description', 'N/A')}</i>", styles['Normal']))
#     elements.append(Paragraph(f'<b>Feedback:</b> "{persona_persp_b.get("feedback", "N/A")}"', styles['Normal']))
#     elements.append(Paragraph(f"<b>Sentiment:</b> {persona_persp_b.get('sentiment', 'N/A').upper()}", styles['Normal']))
#     elements.append(Spacer(1, 10))
    
#     cd_persp_b = var_b.get('creative_director_perspective', {})
#     elements.append(Paragraph("Creative Director Perspective:", subheading_style))
#     elements.append(Paragraph(f"<i>{cd_persp_b.get('description', 'N/A')}</i>", styles['Normal']))
#     elements.append(Paragraph(f'<b>Feedback:</b> "{cd_persp_b.get("feedback", "N/A")}"', styles['Normal']))
#     elements.append(Spacer(1, 10))
    
#     gen_persp_b = var_b.get('general_audience_perspective', {})
#     elements.append(Paragraph("General Audience Perspective:", subheading_style))
#     elements.append(Paragraph(f"<i>{gen_persp_b.get('description', 'N/A')}</i>", styles['Normal']))
#     elements.append(Paragraph(f'<b>Feedback:</b> "{gen_persp_b.get("feedback", "N/A")}"', styles['Normal']))
#     elements.append(Spacer(1, 15))
    
#     # Variant B Emotions & Takeaway
#     emotions_b = ', '.join(var_b.get('emotions_triggered', []))
#     elements.append(Paragraph(f"<b>Emotions Triggered:</b> {emotions_b}", styles['Normal']))
#     elements.append(Paragraph(f"<b>Primary Takeaway:</b> {var_b.get('primary_takeaway', 'N/A')}", styles['Normal']))
#     elements.append(Spacer(1, 10))
    
#     tech_assess_b = var_b.get('technical_assessment', [])
#     elements.append(Paragraph("<b>Technical Assessment:</b>", styles['Normal']))
#     for item in tech_assess_b:
#         elements.append(Paragraph(f"• {item}", styles['Normal']))
    
#     elements.append(Spacer(1, 30))
#     elements.append(PageBreak())
    
#     # Comparative Insights
#     elements.append(Paragraph("💡 COMPARATIVE INSIGHTS", heading_style))
#     elements.append(Spacer(1, 10))
    
#     elements.append(Paragraph(f"<b>Winner:</b> {winner}", styles['Normal']))
#     elements.append(Paragraph(f"<b>Confidence Score:</b> {confidence}%", styles['Normal']))
#     elements.append(Spacer(1, 10))
    
#     elements.append(Paragraph(f"<b>Why the Winner Won:</b>", subheading_style))
#     why_won = comp_insights.get('why_winner_won', [])
#     for reason in why_won:
#         elements.append(Paragraph(f"✓ {reason}", styles['Normal']))
#     elements.append(Spacer(1, 10))
    
#     elements.append(Paragraph(f"<b>Preference Reason:</b>", subheading_style))
#     elements.append(Paragraph(comp_insights.get('preference_reason', 'N/A'), styles['Normal']))
#     elements.append(Spacer(1, 10))
    
#     elements.append(Paragraph(f"<b>Performance Prediction:</b>", subheading_style))
#     elements.append(Paragraph(comp_insights.get('performance_prediction', 'N/A'), styles['Normal']))
#     elements.append(Spacer(1, 15))
    
#     # Key Differences
#     elements.append(Paragraph(f"<b>Key Differences:</b>", subheading_style))
#     key_diffs = comp_insights.get('key_differences', [])
#     for diff in key_diffs:
#         elements.append(Paragraph(f"• {diff}", styles['Normal']))
#     elements.append(Spacer(1, 15))
    
#     # Recommendations
#     elements.append(Paragraph("🎯 RECOMMENDATIONS", heading_style))
#     recommendations = comp_insights.get('recommendations', [])
#     for rec in recommendations:
#         elements.append(Paragraph(f"→ {rec}", styles['Normal']))
#     elements.append(Spacer(1, 15))
    
#     # Flip to Win
#     elements.append(Paragraph("<b>How to Improve Variant A:</b>", subheading_style))
#     elements.append(Paragraph(comp_insights.get('flip_to_win_variant_a', 'N/A'), styles['Normal']))
#     elements.append(Spacer(1, 10))
    
#     elements.append(Paragraph("<b>How to Improve Variant B:</b>", subheading_style))
#     elements.append(Paragraph(comp_insights.get('flip_to_win_variant_b', 'N/A'), styles['Normal']))
    
#     # Build PDF
#     doc.build(elements)
#     return pdf_path


# def upload_pdf_to_supabase(pdf_path: str, user_id: str, filename: str) -> str:
#     """
#     Upload PDF to Supabase storage bucket and return public URL
    
#     Args:
#         pdf_path: Local path to the PDF file
#         user_id: User ID for organizing files
#         filename: Name of the file
        
#     Returns:
#         Public URL of the uploaded file
#     """
#     try:
#         # Create a unique path in storage: reports/{user_id}/{filename}
#         storage_path = f"reports/{user_id}/{filename}"
        
#         # Read the PDF file
#         with open(pdf_path, 'rb') as f:
#             pdf_data = f.read()
        
#         # Upload to Supabase storage
#         response = supabase.storage.from_('creative-asset').upload(
#             path=storage_path,
#             file=pdf_data,
#             file_options={
#                 "content-type": "application/pdf",
#                 "upsert": "true"  # Overwrite if exists
#             }
#         )
        
#         # Get public URL
#         public_url = supabase.storage.from_('creative-asset').get_public_url(storage_path)
        
#         logger.info(f"✅ PDF uploaded to Supabase storage: {storage_path}")
#         return public_url
        
#     except Exception as e:
#         logger.error(f"❌ Failed to upload PDF to Supabase: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to upload PDF to storage: {str(e)}"
#         )

# import csv
# import tempfile
# import os
# from datetime import datetime
# from fastapi import APIRouter, Depends, HTTPException, status

# def create_simulation_csv(result: dict, variant_a: dict, variant_b: dict, csv_path: str):
#     """Generate CSV report from simulation results"""
    
#     with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
#         writer = csv.writer(csvfile)
        
#         writer.writerow(['A/B Simulation Results Report'])
#         writer.writerow([f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
#         writer.writerow([f'Simulation ID: {result.get("simulation_id", "N/A")}'])
#         writer.writerow([])
        
#         writer.writerow(['VARIANT A'])
#         writer.writerow(['Headline', variant_a.get('headline', '')])
#         writer.writerow(['Title', variant_a.get('title', '')])
#         writer.writerow(['Description', variant_a.get('description', '')])
#         writer.writerow([])
        
#         writer.writerow(['Variant A - Performance Metrics'])
#         va_results = result.get('variant_a_results', {})
#         writer.writerow(['Metric', 'Score'])
#         writer.writerow(['Overall Performance', va_results.get('overall_performance', 0)])
#         writer.writerow(['Engagement Score', va_results.get('engagement_score', 0)])
#         writer.writerow(['Relevance Score', va_results.get('relevance_score', 0)])
#         writer.writerow(['Click Through Score', va_results.get('click_through_score', 0)])
#         writer.writerow(['Conversion Potential', va_results.get('conversion_potential', 0)])
#         writer.writerow(['Clarity Score', va_results.get('clarity_score', 0)])
#         writer.writerow(['Brand Linkage Score', va_results.get('brand_linkage_score', 0)])
#         writer.writerow(['Distinctiveness Score', va_results.get('distinctiveness_score', 0)])
#         writer.writerow(['Persuasion Score', va_results.get('persuasion_score', 0)])
#         writer.writerow(['CTA Clarity Score', va_results.get('cta_clarity_score', 0)])
#         writer.writerow([])
        
#         # Variant A Perspectives
#         writer.writerow(['Variant A - Perspectives'])
#         writer.writerow(['Perspective', 'Sentiment', 'Feedback'])
#         persona_persp = va_results.get('persona_perspective', {})
#         writer.writerow(['Persona', persona_persp.get('sentiment', ''), persona_persp.get('feedback', '')])
#         creative_persp = va_results.get('creative_director_perspective', {})
#         writer.writerow(['Creative Director', creative_persp.get('sentiment', ''), creative_persp.get('feedback', '')])
#         general_persp = va_results.get('general_audience_perspective', {})
#         writer.writerow(['General Audience', general_persp.get('sentiment', ''), general_persp.get('feedback', '')])
#         writer.writerow([])
        
#         # Variant B Details
#         writer.writerow(['VARIANT B'])
#         writer.writerow(['Headline', variant_b.get('headline', '')])
#         writer.writerow(['Title', variant_b.get('title', '')])
#         writer.writerow(['Description', variant_b.get('description', '')])
#         writer.writerow([])
        
#         # Variant B Scores
#         writer.writerow(['Variant B - Performance Metrics'])
#         vb_results = result.get('variant_b_results', {})
#         writer.writerow(['Metric', 'Score'])
#         writer.writerow(['Overall Performance', vb_results.get('overall_performance', 0)])
#         writer.writerow(['Engagement Score', vb_results.get('engagement_score', 0)])
#         writer.writerow(['Relevance Score', vb_results.get('relevance_score', 0)])
#         writer.writerow(['Click Through Score', vb_results.get('click_through_score', 0)])
#         writer.writerow(['Conversion Potential', vb_results.get('conversion_potential', 0)])
#         writer.writerow(['Clarity Score', vb_results.get('clarity_score', 0)])
#         writer.writerow(['Brand Linkage Score', vb_results.get('brand_linkage_score', 0)])
#         writer.writerow(['Distinctiveness Score', vb_results.get('distinctiveness_score', 0)])
#         writer.writerow(['Persuasion Score', vb_results.get('persuasion_score', 0)])
#         writer.writerow(['CTA Clarity Score', vb_results.get('cta_clarity_score', 0)])
#         writer.writerow([])
        
#         # Variant B Perspectives
#         writer.writerow(['Variant B - Perspectives'])
#         writer.writerow(['Perspective', 'Sentiment', 'Feedback'])
#         persona_persp = vb_results.get('persona_perspective', {})
#         writer.writerow(['Persona', persona_persp.get('sentiment', ''), persona_persp.get('feedback', '')])
#         creative_persp = vb_results.get('creative_director_perspective', {})
#         writer.writerow(['Creative Director', creative_persp.get('sentiment', ''), creative_persp.get('feedback', '')])
#         general_persp = vb_results.get('general_audience_perspective', {})
#         writer.writerow(['General Audience', general_persp.get('sentiment', ''), general_persp.get('feedback', '')])
#         writer.writerow([])
        
#         # Comparative Insights
#         writer.writerow(['COMPARATIVE INSIGHTS'])
#         insights = result.get('comparative_insights', {})
#         writer.writerow(['Winner', insights.get('winner', '').upper()])
#         writer.writerow(['Confidence Score', f"{insights.get('confidence_score', 0)}%"])
#         writer.writerow(['Preference Reason', insights.get('preference_reason', '')])
#         writer.writerow([])
        
#         # Overall Effectiveness
#         effectiveness = result.get('overall_effectiveness_comparison', {})
#         writer.writerow(['Overall Effectiveness Comparison'])
#         writer.writerow(['Variant A Score', effectiveness.get('variant_a_score', 0)])
#         writer.writerow(['Variant B Score', effectiveness.get('variant_b_score', 0)])
#         writer.writerow(['Relative Increase', f"{effectiveness.get('relative_increase', 0):.2f}%"])
#         writer.writerow([])
        
#         # Key Differences
#         writer.writerow(['Key Differences'])
#         for diff in insights.get('key_differences', []):
#             writer.writerow(['', diff])
#         writer.writerow([])
        
#         # Recommendations
#         writer.writerow(['Recommendations'])
#         for rec in insights.get('recommendations', []):
#             writer.writerow(['', rec])
#         writer.writerow([])
        
#         # Why Winner Won
#         writer.writerow(['Why Winner Won'])
#         for reason in insights.get('why_winner_won', []):
#             writer.writerow(['', reason])


# def upload_csv_to_supabase(csv_path: str, user_id: str, filename: str) -> str:
#     """Upload CSV to Supabase storage"""
#     try:
#         with open(csv_path, 'rb') as f:
#             csv_data = f.read()
        
#         storage_path = f"reports/{user_id}/{filename}"
        
#         supabase.storage.from_("creative-asset").upload(
#             path=storage_path,
#             file=csv_data,
#             file_options={"content-type": "text/csv"}
#         )
        
#         csv_url = supabase.storage.from_("creative-asset").get_public_url(storage_path)
#         logger.info(f"✅ CSV uploaded to Supabase: {csv_url}")
        
#         return csv_url
#     except Exception as e:
#         logger.error(f"Failed to upload CSV to Supabase: {str(e)}")
#         raise


# @router.post("/")
# async def create_simulation(request: dict, current_user: dict = Depends(get_current_user)):
  
#     pdf_temp_path = None
#     csv_temp_path = None
    
#     try:
#         user_id = current_user["id"]

#         subscription_resp = (
#             supabase.table("subscriptions")
#             .select("tier, status")
#             .eq("user_id", user_id)
#             .eq("status", "active")
#             .order("created_at", desc=True)
#             .limit(1)
#             .execute()
#         )

#         user_tier = (
#             subscription_resp.data[0]["tier"].lower()
#             if subscription_resp.data
#             else "free"
#         )

#         variant_a = request.get("variant_a", {})
#         variant_b = request.get("variant_b", {})

#         required_fields = ["persona_id", "creative_ids", "headline", "title", "description"]
#         for name, variant in [("variant_a", variant_a), ("variant_b", variant_b)]:
#             missing = [f for f in required_fields if not variant.get(f)]
#             if missing:
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail=f"{name} missing required fields: {', '.join(missing)}"
#                 )

#         # Persona validation
#         persona_a_id = variant_a["persona_id"]
#         persona_b_id = variant_b["persona_id"]

#         response_a = supabase.table("personas").select("*").eq("id", persona_a_id).execute()
#         response_b = supabase.table("personas").select("*").eq("id", persona_b_id).execute()

#         if not response_a.data or not response_b.data:
#             raise HTTPException(status_code=404, detail="One or more personas not found")

#         persona_a = response_a.data[0]
#         persona_b = response_b.data[0]

#         if persona_a["user_id"] != user_id or persona_b["user_id"] != user_id:
#             raise HTTPException(status_code=403, detail="You do not own one or more personas")

#         # Creative assets validation
#         creative_ids_a = variant_a["creative_ids"]
#         creative_ids_b = variant_b["creative_ids"]
#         all_ids = list(set(creative_ids_a + creative_ids_b))

#         creative_assets_response = supabase.table("creative_assets").select("*").in_("id", all_ids).execute()
#         creative_assets = creative_assets_response.data or []

#         if len(creative_assets) != len(all_ids):
#             raise HTTPException(status_code=404, detail="One or more creative assets not found")

#         # Verify ownership of creative assets
#         for asset in creative_assets:
#             project_resp = supabase.table("projects").select("user_id").eq("id", asset["project_id"]).execute()
#             if not project_resp.data or project_resp.data[0]["user_id"] != user_id:
#                 raise HTTPException(
#                     status_code=403,
#                     detail=f"Creative asset {asset['id']} does not belong to your project"
#                 )

#         # Process and format creative assets
#         filtered_assets_a, filtered_assets_b = [], []

#         for asset in creative_assets:
#             asset_type = asset["type"].lower()
#             formatted_asset = None

#             if asset_type in ["audio", "image", "video"]:
#                 formatted_asset = {
#                     "id": asset["id"],
#                     "type": asset["type"],
#                     "file_url": asset["file_url"]
#                 }
#             elif asset_type == "text":
#                 formatted_asset = {
#                     "id": asset["id"],
#                     "type": asset["type"],
#                     "ad_copy": asset["ad_copy"]
#                 }
#                 if asset.get("voice_script"):
#                     formatted_asset["voice_script"] = asset["voice_script"]

#             if formatted_asset:
#                 if asset["id"] in creative_ids_a:
#                     filtered_assets_a.append(formatted_asset)
#                 if asset["id"] in creative_ids_b:
#                     filtered_assets_b.append(formatted_asset)

#         # Filter persona fields
#         persona_fields = [
#             "min_reach", "max_reach", "efficiency", "platforms",
#             "peak_activity", "engagement", "clarity", "relevance",
#             "distinctiveness", "brand_fit", "emotion", "cta", "inclusivity"
#         ]
#         filtered_persona_a = {k: persona_a.get(k) for k in persona_fields}
#         filtered_persona_b = {k: persona_b.get(k) for k in persona_fields}

#         # Prepare request data
#         request_data = {
#             "variant_a": {
#                 "persona": filtered_persona_a,
#                 "creative_assets": filtered_assets_a,
#                 "headline": variant_a["headline"],
#                 "title": variant_a["title"],
#                 "description": variant_a["description"]
#             },
#             "variant_b": {
#                 "persona": filtered_persona_b,
#                 "creative_assets": filtered_assets_b,
#                 "headline": variant_b["headline"],
#                 "title": variant_b["title"],
#                 "description": variant_b["description"]
#             }
#         }

#         logger.info(f"Prepared request_data with {len(filtered_assets_a)} assets for variant A and {len(filtered_assets_b)} assets for variant B")

#         # Run simulation service
#         result = await simulation_service.create_simulation(
#             user_id=str(user_id),
#             request=request_data
#         )

#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
#         pdf_filename = f"simulation_report_{user_id}_{timestamp}.pdf"
#         with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pdf') as tmp_file:
#             pdf_temp_path = tmp_file.name
        
#         create_enhanced_pdf(result, variant_a, variant_b, user_id, user_tier, pdf_temp_path)
#         logger.info(f"✅ PDF report generated temporarily: {pdf_temp_path}")
        
#         # Generate CSV in temporary directory
#         csv_filename = f"simulation_report_{user_id}_{timestamp}.csv"
#         with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp_file:
#             csv_temp_path = tmp_file.name
        
#         create_simulation_csv(result, variant_a, variant_b, csv_temp_path)
#         logger.info(f"✅ CSV report generated temporarily: {csv_temp_path}")
        
#         # Upload both files to Supabase storage
#         pdf_url = upload_pdf_to_supabase(pdf_temp_path, str(user_id), pdf_filename)
#         csv_url = upload_csv_to_supabase(csv_temp_path, str(user_id), csv_filename)
        
#         return {
#             "message": "Simulation completed successfully",
#             "result": result,
#             "pdf_url": pdf_url,
#             "csv_url": csv_url
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Unexpected error in create_simulation: {str(e)}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Internal server error during simulation: {str(e)}"
#         )
#     finally:
#         # Clean up temporary files
#         if pdf_temp_path and os.path.exists(pdf_temp_path):
#             try:
#                 os.remove(pdf_temp_path)
#                 logger.info(f"🗑️ Cleaned up temporary PDF: {pdf_temp_path}")
#             except Exception as e:
#                 logger.warning(f"Failed to clean up temporary PDF file: {str(e)}")
        
#         if csv_temp_path and os.path.exists(csv_temp_path):
#             try:
#                 os.remove(csv_temp_path)
#                 logger.info(f"🗑️ Cleaned up temporary CSV: {csv_temp_path}")
#             except Exception as e:
#                 logger.warning(f"Failed to clean up temporary CSV file: {str(e)}")

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
import logging
import os
from datetime import datetime
import tempfile
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak
)
from app.helpers.security import get_current_user
from app.service.simulation_service import SimulationService
from app.helpers.db import supabase
import csv

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()
simulation_service = SimulationService()

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from datetime import datetime

def create_enhanced_pdf(result, variant_a, variant_b, user_id, user_tier, pdf_path):
    """Generate an enhanced, visually appealing PDF report matching creative pretesting format"""
    
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, 
                           rightMargin=0.75*inch, leftMargin=0.75*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    styles = getSampleStyleSheet()
    elements = []
    
    # Custom styles matching the research report format
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#555555'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        spaceAfter=6,
        alignment=TA_LEFT,
        fontName='Helvetica'
    )
    
    elements.append(Spacer(1, 1.5*inch))
    elements.append(Paragraph("Creative Pretesting Research Report", title_style))
    elements.append(Paragraph("A/B Simulation Analysis", subtitle_style))
    elements.append(Spacer(1, 0.5*inch))
    
    cover_data = [
        ["Campaign:", f"{variant_a.get('title', 'Campaign Test')}"],
        ["Test Date:", datetime.now().strftime('%B %Y')],
        ["Plan Tier:", user_tier.title()],
        ["Conducted by:", "BuzzInsider Research Labs"]
    ]
    
    cover_table = Table(cover_data, colWidths=[2*inch, 4*inch])
    cover_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
    ]))
    elements.append(cover_table)
    elements.append(PageBreak())
    
    elements.append(Paragraph("1. Objectives", heading_style))
    elements.append(Paragraph("Evaluate effectiveness of two campaign variants:", body_style))
    elements.append(Paragraph(f"• <b>Variant A:</b> {variant_a.get('headline', 'N/A')}", body_style))
    elements.append(Paragraph(f"• <b>Variant B:</b> {variant_b.get('headline', 'N/A')}", body_style))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("Identify the creative with highest emotional engagement and brand recall.", body_style))
    elements.append(Paragraph("Provide diagnostic feedback for creative optimization before media launch.", body_style))
    elements.append(Spacer(1, 20))
    
    research_data = result.get('research_data', {})
    methodology = research_data.get('methodology', {})
    demographics = research_data.get('demographics', {})
    
    elements.append(Paragraph("2. Methodology", heading_style))
    elements.append(Paragraph(f"<b>Sample:</b> {methodology.get('sample_description', 'N/A')}", body_style))
    elements.append(Paragraph(f"<b>Design:</b> {methodology.get('design', 'N/A')}", body_style))
    elements.append(Paragraph("<b>Measures:</b>", body_style))
    
    for metric in methodology.get('metrics_measured', []):
        elements.append(Paragraph(f"  • {metric}", body_style))
    
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("Normative Comparison vs Category Benchmark", body_style))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("3. Key Takeaways", heading_style))
    
    key_takeaways = research_data.get('key_takeaways_table', {}).get('metrics', [])
    if key_takeaways:
        takeaway_data = [["Metric", "Variant A", "Variant B", "Category Norm"]]
        for metric in key_takeaways:
            takeaway_data.append([
                metric.get('metric', 'N/A'),
                str(metric.get('variant_a', 0)),
                str(metric.get('variant_b', 0)),
                str(metric.get('category_norm', 0))
            ])
        
        takeaway_table = Table(takeaway_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        takeaway_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        elements.append(takeaway_table)
    
    elements.append(Spacer(1, 10))
    comp_insights = result.get('comparative_insights', {})
    winner = comp_insights.get('winner', 'N/A').replace('_', ' ').title()
    elements.append(PageBreak())
    
    elements.append(Paragraph("4. Performance Comparison", heading_style))
    
    var_a = result.get('variant_a_results', {})
    var_b = result.get('variant_b_results', {})
    overall_comp = result.get('overall_effectiveness_comparison', {})
    
    performance_data = [
        ["Metric", "Variant A", "Variant B", "Difference"],
        ["Engagement Score", 
         f"{var_a.get('engagement_score', 0)}", 
         f"{var_b.get('engagement_score', 0)}",
         f"{var_b.get('engagement_score', 0) - var_a.get('engagement_score', 0):+d}"],
        ["Relevance Score", 
         f"{var_a.get('relevance_score', 0)}", 
         f"{var_b.get('relevance_score', 0)}",
         f"{var_b.get('relevance_score', 0) - var_a.get('relevance_score', 0):+d}"],
        ["Click-Through Score", 
         f"{var_a.get('click_through_score', 0)}", 
         f"{var_b.get('click_through_score', 0)}",
         f"{var_b.get('click_through_score', 0) - var_a.get('click_through_score', 0):+d}"],
        ["Conversion Potential", 
         f"{var_a.get('conversion_potential', 0)}", 
         f"{var_b.get('conversion_potential', 0)}",
         f"{var_b.get('conversion_potential', 0) - var_a.get('conversion_potential', 0):+d}"],
        ["Overall Performance", 
         f"{var_a.get('overall_performance', 0):.2f}", 
         f"{var_b.get('overall_performance', 0):.2f}",
         f"{overall_comp.get('relative_increase', 0):+.2f}% {'(Increase)' if overall_comp.get('relative_increase', 0) > 0 else '(Decrease)' if overall_comp.get('relative_increase', 0) < 0 else ''}"],
    ]
    
    perf_table = Table(performance_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    perf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    elements.append(perf_table)
    elements.append(Spacer(1, 20))
    
    # ADD EMOTIONAL ENGAGEMENT SECTIONS CONDITIONALLY
    emotional_journey_a = research_data.get('emotional_journey_variant_a')
    emotional_journey_b = research_data.get('emotional_journey_variant_b')
    emotional_summary_a = research_data.get('emotional_engagement_summary_variant_a')
    emotional_summary_b = research_data.get('emotional_engagement_summary_variant_b')
    
    # Only add this section if any emotional data exists
    if emotional_journey_a or emotional_journey_b or emotional_summary_a or emotional_summary_b:
        elements.append(Paragraph("5. Emotional Engagement Analysis", heading_style))
        
        # Variant A Emotional Data
        if emotional_journey_a or emotional_summary_a:
            elements.append(Paragraph("<b>Variant A:</b>", body_style))
            
            if emotional_summary_a:
                elements.append(Paragraph(f"<b>Summary:</b> {emotional_summary_a.get('summary', 'N/A')}", body_style))
                elements.append(Paragraph(f"<b>Peak Emotion:</b> {emotional_summary_a.get('peak_emotion', 'N/A')} at {emotional_summary_a.get('peak_time_seconds', 0)}s", body_style))
                elements.append(Paragraph(f"<b>Method:</b> {emotional_summary_a.get('method', 'N/A')}", body_style))
                
                low_scenes = emotional_summary_a.get('low_engagement_scenes', [])
                if low_scenes:
                    elements.append(Paragraph(f"<b>Low Engagement Scenes:</b> {', '.join(low_scenes)}", body_style))
                
                elements.append(Spacer(1, 10))
            
            if emotional_journey_a:
                journey_data_a = [["Timestamp", "Primary Emotion", "Intensity"]]
                for point in emotional_journey_a:
                    journey_data_a.append([
                        point.get('timestamp', 'N/A'),
                        point.get('primary_emotion', 'N/A').title(),
                        f"{point.get('intensity', 0):.1f}"
                    ])
                
                journey_table_a = Table(journey_data_a, colWidths=[1.5*inch, 2*inch, 1.5*inch])
                journey_table_a.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7f7f7f')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                ]))
                elements.append(journey_table_a)
                elements.append(Spacer(1, 15))
        
        # Variant B Emotional Data
        if emotional_journey_b or emotional_summary_b:
            elements.append(Paragraph("<b>Variant B:</b>", body_style))
            
            if emotional_summary_b:
                elements.append(Paragraph(f"<b>Summary:</b> {emotional_summary_b.get('summary', 'N/A')}", body_style))
                elements.append(Paragraph(f"<b>Peak Emotion:</b> {emotional_summary_b.get('peak_emotion', 'N/A')} at {emotional_summary_b.get('peak_time_seconds', 0)}s", body_style))
                elements.append(Paragraph(f"<b>Method:</b> {emotional_summary_b.get('method', 'N/A')}", body_style))
                
                low_scenes = emotional_summary_b.get('low_engagement_scenes', [])
                if low_scenes:
                    elements.append(Paragraph(f"<b>Low Engagement Scenes:</b> {', '.join(low_scenes)}", body_style))
                
                elements.append(Spacer(1, 10))
            
            if emotional_journey_b:
                journey_data_b = [["Timestamp", "Primary Emotion", "Intensity"]]
                for point in emotional_journey_b:
                    journey_data_b.append([
                        point.get('timestamp', 'N/A'),
                        point.get('primary_emotion', 'N/A').title(),
                        f"{point.get('intensity', 0):.1f}"
                    ])
                
                journey_table_b = Table(journey_data_b, colWidths=[1.5*inch, 2*inch, 1.5*inch])
                journey_table_b.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7f7f7f')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                ]))
                elements.append(journey_table_b)
                elements.append(Spacer(1, 15))
        
        elements.append(PageBreak())
    
    # ADD SCENE-BY-SCENE ANALYSIS CONDITIONALLY
    scene_analysis_a = research_data.get('scene_by_scene_analysis_variant_a')
    scene_analysis_b = research_data.get('scene_by_scene_analysis_variant_b')
    
    section_number = 6 if not (emotional_journey_a or emotional_journey_b or emotional_summary_a or emotional_summary_b) else 6
    
    if scene_analysis_a or scene_analysis_b:
        elements.append(Paragraph(f"{section_number}. Scene-by-Scene Analysis", heading_style))
        
        # Variant A Scene Analysis
        if scene_analysis_a:
            elements.append(Paragraph("<b>Variant A:</b>", body_style))
            elements.append(Spacer(1, 8))
            
            scene_data_a = [["Scene", "Time", "Attention", "Positive", "Confusion", "Branding"]]
            for scene in scene_analysis_a:
                scene_data_a.append([
                    scene.get('scene_name', 'N/A'),
                    scene.get('timestamp_range', 'N/A'),
                    f"{scene.get('attention_score', 0)}",
                    f"{scene.get('positive_emotion', 0)}",
                    f"{scene.get('confusion_level', 0)}%",
                    f"{scene.get('branding_visibility', 0)}%"
                ])
            
            scene_table_a = Table(scene_data_a, colWidths=[1.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
            scene_table_a.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
            ]))
            elements.append(scene_table_a)
            elements.append(Spacer(1, 15))
        
        # Variant B Scene Analysis
        if scene_analysis_b:
            elements.append(Paragraph("<b>Variant B:</b>", body_style))
            elements.append(Spacer(1, 8))
            
            scene_data_b = [["Scene", "Time", "Attention", "Positive", "Confusion", "Branding"]]
            for scene in scene_analysis_b:
                scene_data_b.append([
                    scene.get('scene_name', 'N/A'),
                    scene.get('timestamp_range', 'N/A'),
                    f"{scene.get('attention_score', 0)}",
                    f"{scene.get('positive_emotion', 0)}",
                    f"{scene.get('confusion_level', 0)}%",
                    f"{scene.get('branding_visibility', 0)}%"
                ])
            
            scene_table_b = Table(scene_data_b, colWidths=[1.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
            scene_table_b.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
            ]))
            elements.append(scene_table_b)
            elements.append(Spacer(1, 15))
        
        elements.append(PageBreak())
        section_number += 1
    
    # Continue with the rest of the sections (adjusted numbering)
    elements.append(Paragraph(f"{section_number}. Detailed Quality Metrics", heading_style))
    
    detailed_data = [
        ["Quality Metric", "Variant A", "Variant B"],
        ["Clarity Score", f"{var_a.get('clarity_score', 0)}/7", f"{var_b.get('clarity_score', 0)}/7"],
        ["Brand Linkage", f"{var_a.get('brand_linkage_score', 0)}/7", f"{var_b.get('brand_linkage_score', 0)}/7"],
        ["Relevance Detail", f"{var_a.get('relevance_detail_score', 0)}/7", f"{var_b.get('relevance_detail_score', 0)}/7"],
        ["Distinctiveness", f"{var_a.get('distinctiveness_score', 0)}/7", f"{var_b.get('distinctiveness_score', 0)}/7"],
        ["Persuasion", f"{var_a.get('persuasion_score', 0)}/7", f"{var_b.get('persuasion_score', 0)}/7"],
        ["CTA Clarity", f"{var_a.get('cta_clarity_score', 0)}/7", f"{var_b.get('cta_clarity_score', 0)}/7"],
        ["Craft Score", f"{var_a.get('craft_score', 0)}/7", f"{var_b.get('craft_score', 0)}/7"],
    ]
    
    detailed_table = Table(detailed_data, colWidths=[2.5*inch, 2*inch, 2*inch])
    detailed_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#7f7f7f")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8f9fa'), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    elements.append(detailed_table)
    elements.append(PageBreak())
    
    section_number += 1
    elements.append(Paragraph(f"{section_number}. Verbatim Highlights", heading_style))
    
    elements.append(Paragraph("<b>Variant A:</b>", body_style))
    verbatim_a = research_data.get('verbatim_highlights_variant_a', [])
    for comment in verbatim_a[:6]:
        elements.append(Paragraph(f'  • "{comment}"', body_style))
    
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>Variant B:</b>", body_style))
    verbatim_b = research_data.get('verbatim_highlights_variant_b', [])
    for comment in verbatim_b[:6]:
        elements.append(Paragraph(f'  • "{comment}"', body_style))
    
    elements.append(Spacer(1, 20))
    
    section_number += 1
    elements.append(Paragraph(f"{section_number}. Recommendations", heading_style))
    
    recommendations = research_data.get('recommendations', {})
    
    elements.append(Paragraph("<b>Keep:</b>", body_style))
    for item in recommendations.get('keep', []):
        elements.append(Paragraph(f"  • {item}", body_style))
    
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("<b>Improve:</b>", body_style))
    for item in recommendations.get('improve', []):
        elements.append(Paragraph(f"  • {item}", body_style))
    
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("<b>Adjust:</b>", body_style))
    for item in recommendations.get('adjust', []):
        elements.append(Paragraph(f"  • {item}", body_style))
    
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Next Step:</b> {comp_insights.get('performance_prediction', 'Re-test optimized creative for final validation.')}", body_style))
    elements.append(PageBreak())
    
    section_number += 1
    elements.append(Paragraph(f"{section_number}. Winner Analysis", heading_style))
    
    confidence = comp_insights.get('confidence_score', 0)
    elements.append(Paragraph(f"<b>Winner:</b> {winner}", body_style))
    elements.append(Paragraph(f"<b>Confidence Score:</b> {confidence}%", body_style))
    elements.append(Spacer(1, 10))
    
    elements.append(Paragraph("<b>Why the Winner Won:</b>", body_style))
    why_won = comp_insights.get('why_winner_won', [])
    for reason in why_won:
        elements.append(Paragraph(f"  ✓ {reason}", body_style))
    
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>Key Differences:</b>", body_style))
    key_diffs = comp_insights.get('key_differences', [])
    for diff in key_diffs:
        elements.append(Paragraph(f"  • {diff}", body_style))
    
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>Strategic Recommendations:</b>", body_style))
    strategic_recs = comp_insights.get('recommendations', [])
    for rec in strategic_recs:
        elements.append(Paragraph(f"  → {rec}", body_style))
    
    elements.append(Spacer(1, 20))
    
    section_number += 1
    elements.append(Paragraph(f"{section_number}. Normative Comparison", heading_style))
    
    normative = research_data.get('normative_comparison', {})
    elements.append(Paragraph(f"<b>Category Benchmark:</b> {normative.get('category_benchmark', 'N/A')}", body_style))
    elements.append(Paragraph(f"• Variant A sits in the {normative.get('variant_a_percentile', 0)}th percentile", body_style))
    elements.append(Paragraph(f"• Variant B sits in the {normative.get('variant_b_percentile', 0)}th percentile", body_style))
    elements.append(Spacer(1, 20))
    
    section_number += 1
    elements.append(Paragraph(f"{section_number}. Appendices", heading_style))
    
    elements.append(Paragraph("<b>A. Demographics</b>", body_style))
    age_segments = demographics.get('age_segments', [])
    if age_segments:
        demo_data = [["Age Segment", "% of Sample"]]
        for segment in age_segments:
            demo_data.append([segment.get('segment', 'N/A'), f"{segment.get('percent', 0)}%"])
        
        gender_split = demographics.get('gender_split', {})
        demo_data.append(["Male", f"{gender_split.get('male', 0)}%"])
        demo_data.append(["Female", f"{gender_split.get('female', 0)}%"])
        
        demo_table = Table(demo_data, colWidths=[3*inch, 2*inch])
        demo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ]))
        elements.append(demo_table)
    
    elements.append(PageBreak())
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<b>B. Method Detail</b>", body_style))
    elements.append(Paragraph(f"Platform: AI-Powered Creative Testing Platform", body_style))
    elements.append(Paragraph(f"Simulation ID: {result.get('simulation_id', 'N/A')}", body_style))
    elements.append(Paragraph(f"Processing Time: {result.get('processing_time', 0):.2f} seconds", body_style))
    elements.append(Paragraph(f"Statistical Confidence: 95%", body_style))
    
    doc.build(elements)
    return pdf_path

def upload_pdf_to_supabase(pdf_path: str, user_id: str, filename: str) -> str:
    """Upload PDF to Supabase storage bucket and return public URL"""
    try:
        storage_path = f"reports/{user_id}/{filename}"
        
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
        
        response = supabase.storage.from_('creative-asset').upload(
            path=storage_path,
            file=pdf_data,
            file_options={
                "content-type": "application/pdf",
                "upsert": "true"
            }
        )
        
        public_url = supabase.storage.from_('creative-asset').get_public_url(storage_path)
        
        logger.info(f"PDF uploaded to Supabase storage: {storage_path}")
        return public_url
        
    except Exception as e:
        logger.error(f"Failed to upload PDF to Supabase: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload PDF to storage: {str(e)}"
        )

def create_simulation_csv(result: dict, variant_a: dict, variant_b: dict, csv_path: str, user_tier: str):
    """Generate CSV with respondent-level data for both variants"""
    
    research_data = result.get('research_data', {})
    respondents_a = research_data.get('respondent_data_variant_a', [])
    respondents_b = research_data.get('respondent_data_variant_b', [])
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        writer.writerow([
            'respondent_id',
            'concept',
            'gender',
            'age',
            'appeal_score',
            'brand_recall_aided',
            'message_clarity',
            'purchase_intent'
        ])
        
        respondent_id = 1
        for respondent in respondents_a:
            writer.writerow([
                respondent_id,
                'A',
                respondent.get('gender', ''),
                respondent.get('age', ''),
                respondent.get('appeal_score', ''),
                respondent.get('brand_recall_aided', ''),
                respondent.get('message_clarity', ''),
                respondent.get('purchase_intent', '')
            ])
            respondent_id += 1
        
        # Write Variant B respondent data
        for respondent in respondents_b:
            writer.writerow([
                respondent_id,
                'B',
                respondent.get('gender', ''),
                respondent.get('age', ''),
                respondent.get('appeal_score', ''),
                respondent.get('brand_recall_aided', ''),
                respondent.get('message_clarity', ''),
                respondent.get('purchase_intent', '')
            ])
            respondent_id += 1

def upload_csv_to_supabase(csv_path: str, user_id: str, filename: str) -> str:
    """Upload CSV to Supabase storage"""
    try:
        with open(csv_path, 'rb') as f:
            csv_data = f.read()
        
        storage_path = f"reports/{user_id}/{filename}"
        
        supabase.storage.from_("creative-asset").upload(
            path=storage_path,
            file=csv_data,
            file_options={"content-type": "text/csv", "upsert": "true"}
        )
        
        csv_url = supabase.storage.from_("creative-asset").get_public_url(storage_path)
        logger.info(f"CSV uploaded to Supabase: {csv_url}")
        
        return csv_url
    except Exception as e:
        logger.error(f"Failed to upload CSV to Supabase: {str(e)}")
        raise

@router.post("/")
async def create_simulation(request: dict, current_user: dict = Depends(get_current_user)):
  
    pdf_temp_path = None
    csv_temp_path = None
    
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

        if user_tier == "free":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A/B Simulation API is not available in the Free plan. Please upgrade to Starter or higher."
            )

        variant_a = request.get("variant_a", {})
        variant_b = request.get("variant_b", {})

        required_fields = ["persona_id", "creative_ids", "headline", "title", "description"]
        for name, variant in [("variant_a", variant_a), ("variant_b", variant_b)]:
            missing = [f for f in required_fields if not variant.get(f)]
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{name} missing required fields: {', '.join(missing)}"
                )
        persona_a_id = variant_a["persona_id"]
        persona_b_id = variant_b["persona_id"]

        response_a = supabase.table("personas").select("*").eq("id", persona_a_id).execute()
        response_b = supabase.table("personas").select("*").eq("id", persona_b_id).execute()

        if not response_a.data or not response_b.data:
            raise HTTPException(status_code=404, detail="One or more personas not found")

        persona_a = response_a.data[0]
        persona_b = response_b.data[0]

        if persona_a["user_id"] != user_id or persona_b["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="You do not own one or more personas")

        creative_ids_a = variant_a["creative_ids"]
        creative_ids_b = variant_b["creative_ids"]
        all_ids = list(set(creative_ids_a + creative_ids_b))

        creative_assets_response = supabase.table("creative_assets").select("*").in_("id", all_ids).execute()
        creative_assets = creative_assets_response.data or []

        if len(creative_assets) != len(all_ids):
            raise HTTPException(status_code=404, detail="One or more creative assets not found")

        for asset in creative_assets:
            project_resp = supabase.table("projects").select("user_id").eq("id", asset["project_id"]).execute()
            if not project_resp.data or project_resp.data[0]["user_id"] != user_id:
                raise HTTPException(
                    status_code=403,
                    detail=f"Creative asset {asset['id']} does not belong to your project"
                )
        project_ids = list(set([asset["project_id"] for asset in creative_assets]))
        projects_response = supabase.table("projects").select("*").in_("id", project_ids).execute()
        projects_data = {p["id"]: p for p in projects_response.data} if projects_response.data else {}

        for asset in creative_assets:
            if asset["project_id"] not in projects_data:
                raise HTTPException(status_code=404, detail=f"Project {asset['project_id']} not found")
            
            project = projects_data[asset["project_id"]]
            if project["user_id"] != user_id:
                raise HTTPException(
                    status_code=403,
                    detail=f"Creative asset {asset['id']} does not belong to your project"
                )
            
            asset["project_context"] = {
                "name": project.get("name"),
                "brand": project.get("brand"),
                "product": project.get("product"),
                "product_service_type": project.get("product_service_type"),
                "category": project.get("category"),
                "market_maturity": project.get("market_maturity"),
                "campaign_objective": project.get("campaign_objective"),
                "value_propositions": project.get("value_propositions"),
                "media_channels": project.get("media_channels"),
                "kpis": project.get("kpis"),
                "kpi_target": project.get("kpi_target")
            }
            project_context = asset["project_context"]
           

        filtered_assets_a, filtered_assets_b = [], []

        for asset in creative_assets:
            asset_type = asset["type"].lower()
            formatted_asset = None

            if asset_type in ["audio", "image", "video"]:
                formatted_asset = {
                    "id": asset["id"],
                    "type": asset["type"],
                    "file_url": asset["file_url"],
                    "name": asset.get("name"),
                    "project_name": project_context.get("name"),
                    "brand": project_context.get("brand"),
                    "product": project_context.get("product"),
                    "product_service_type": project_context.get("product_service_type"),
                    "category": project_context.get("category"),
                    "market_maturity": project_context.get("market_maturity"),
                    "campaign_objective": project_context.get("campaign_objective"),
                    "value_propositions": project_context.get("value_propositions"),
                    "media_channels": project_context.get("media_channels"),
                    "kpis": project_context.get("kpis"),
                    "kpi_target": project_context.get("kpi_target")
                }
            elif asset_type == "text":
                formatted_asset = {
                    "id": asset["id"],
                    "type": asset["type"],
                    "file_url": asset["file_url"],
                    "name": asset.get("name"),
                    "project_name": project_context.get("name"),
                    "brand": project_context.get("brand"),
                    "product": project_context.get("product"),
                    "product_service_type": project_context.get("product_service_type"),
                    "category": project_context.get("category"),
                    "market_maturity": project_context.get("market_maturity"),
                    "campaign_objective": project_context.get("campaign_objective"),
                    "value_propositions": project_context.get("value_propositions"),
                    "media_channels": project_context.get("media_channels"),
                    "kpis": project_context.get("kpis"),
                    "kpi_target": project_context.get("kpi_target")
                }
                if asset.get("voice_script"):
                    formatted_asset["voice_script"] = asset["voice_script"]

            if formatted_asset:
                if asset["id"] in creative_ids_a:
                    filtered_assets_a.append(formatted_asset)
                if asset["id"] in creative_ids_b:
                    filtered_assets_b.append(formatted_asset)
    
        persona_fields = [
            "audience_type", "geography", "age_min", "age_max", 
            "income_min", "income_max", "gender", 
            "purchase_frequency", "interests", "life_stage", 
            "category_involvement", "decision_making_style",
            "min_reach", "max_reach", "efficiency", "platforms",
            "peak_activity", "engagement","clarity", "relevance", "distinctiveness", "brand_fit", 
            "emotion", "cta", "inclusivity"
        ]
        
        filtered_persona_a = {k: persona_a.get(k) for k in persona_fields}
        filtered_persona_b = {k: persona_b.get(k) for k in persona_fields}

        request_data = {
            "variant_a": {
                "persona": filtered_persona_a,
                "creative_assets": filtered_assets_a,
                "headline": variant_a["headline"],
                "title": variant_a["title"],
                "description": variant_a["description"]
            },
            "variant_b": {
                "persona": filtered_persona_b,
                "creative_assets": filtered_assets_b,
                "headline": variant_b["headline"],
                "title": variant_b["title"],
                "description": variant_b["description"]
            }
        }

        logger.info(f"Prepared request_data with {len(filtered_assets_a)} assets for variant A and {len(filtered_assets_b)} assets for variant B")

        result = await simulation_service.create_simulation(
            user_id=str(user_id),
            request=request_data,
            user_tier=user_tier
        )
        print("Simulation result:", result)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"simulation_report_{user_id}_{timestamp}.pdf"
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pdf') as tmp_file:
            pdf_temp_path = tmp_file.name
        
        create_enhanced_pdf(result, variant_a, variant_b, user_id, user_tier, pdf_temp_path)
        logger.info(f"PDF report generated temporarily: {pdf_temp_path}")
        
        pdf_url = upload_pdf_to_supabase(pdf_temp_path, str(user_id), pdf_filename)
        
        csv_url = None
        if user_tier.lower() not in ["starter", "free"]:
            csv_filename = f"simulation_report_{user_id}_{timestamp}.csv"
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp_file:
                csv_temp_path = tmp_file.name
            
            create_simulation_csv(result, variant_a, variant_b, csv_temp_path, user_tier)
            logger.info(f"CSV report generated temporarily: {csv_temp_path}")
            
            csv_url = upload_csv_to_supabase(csv_temp_path, str(user_id), csv_filename)
        else:
            logger.info(f"CSV generation skipped for {user_tier} tier user")
        
        response_data = {
            "message": "Simulation completed successfully",
            "result": result,
            "pdf_url": pdf_url,
        }
        if csv_url:
            response_data["csv_url"] = csv_url
        
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in create_simulation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during simulation: {str(e)}"
        )
    finally:
        if pdf_temp_path and os.path.exists(pdf_temp_path):
            try:
                os.remove(pdf_temp_path)
                logger.info(f"Cleaned up temporary PDF: {pdf_temp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary PDF file: {str(e)}")
        
        if csv_temp_path and os.path.exists(csv_temp_path):
            try:
                os.remove(csv_temp_path)
                logger.info(f"Cleaned up temporary CSV: {csv_temp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary CSV file: {str(e)}")