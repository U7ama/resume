import sys
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable, Image
)

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path('/usr/share/fonts/truetype/dejavu')

pdfmetrics.registerFont(TTFont('EU', str(FONT_DIR / 'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('EUBold', str(FONT_DIR / 'DejaVuSans-Bold.ttf')))
pdfmetrics.registerFont(TTFont('EUOblique', str(FONT_DIR / 'DejaVuSans-Oblique.ttf')))
pdfmetrics.registerFontFamily('EU', normal='EU', bold='EUBold', italic='EUOblique')

# Official Europass Color Palette
EU_BLUE = colors.HexColor('#0e4194')
EU_DARK = colors.HexColor('#1f2937')
EU_MUTED = colors.HexColor('#4b5563')
EU_BORDER = colors.HexColor('#cbd5e1')
EU_BG_LIGHT = colors.HexColor('#f8fafc')

body = ParagraphStyle('body', fontName='EU', fontSize=9.2, leading=12.8, textColor=EU_DARK, spaceAfter=2)
body_bold = ParagraphStyle('body_bold', parent=body, fontName='EUBold')
small = ParagraphStyle('small', parent=body, fontSize=8.2, leading=11.5, textColor=EU_MUTED)
name_style = ParagraphStyle('name', fontName='EUBold', fontSize=19, leading=23, textColor=EU_BLUE, spaceAfter=2)
role_title = ParagraphStyle('role_title', fontName='EU', fontSize=10.5, leading=14, textColor=EU_MUTED, spaceAfter=4)
section_title = ParagraphStyle('section_title', fontName='EUBold', fontSize=10.5, leading=14, textColor=EU_BLUE, spaceAfter=2)
item_title = ParagraphStyle('item_title', fontName='EUBold', fontSize=9.2, leading=12.8, textColor=EU_DARK)
item_meta = ParagraphStyle('item_meta', fontName='EU', fontSize=8.2, leading=11.5, textColor=EU_MUTED)
bullet_style = ParagraphStyle('bullet', parent=body, leftIndent=11, firstLineIndent=-7, spaceAfter=2)

def build_pdf(out_path: Path, show_photo: bool = True):
    story = []

    def p(text, style=body):
        return Paragraph(text, style)

    def section(title_text):
        story.append(Spacer(1, 5))
        story.append(p(title_text.upper(), section_title))
        story.append(HRFlowable(width='100%', thickness=0.8, color=EU_BLUE, spaceAfter=4))

    def bullet(text):
        return p('&#8226;  ' + text, bullet_style)

    # 1. Header (Personal Information)
    contact_info = [
        p('<b>USAMA ASLAM</b>', name_style),
        p('Full-Stack Engineer &amp; Applied AI Specialist', role_title),
        p('<b>Nationality:</b> Pakistani &nbsp;|&nbsp; <b>Gender:</b> Male &nbsp;|&nbsp; <b>Location:</b> Lahore, Pakistan', item_meta),
        p('<b>Email:</b> <link href="mailto:u7amaaslam@gmail.com" color="#0e4194">u7amaaslam@gmail.com</link> &nbsp;|&nbsp; '
          '<b>Phone:</b> <link href="tel:+923016441046" color="#0e4194">+92 301 6441046</link>', item_meta),
        p('<b>Website:</b> <link href="https://portfolio.usamaaslam.site/" color="#0e4194">portfolio.usamaaslam.site</link> &nbsp;|&nbsp; '
          '<b>LinkedIn:</b> <link href="https://www.linkedin.com/in/usama-aslam-638584194/" color="#0e4194">in/usama-aslam-638584194</link> &nbsp;|&nbsp; '
          '<b>GitHub:</b> <link href="https://github.com/U7ama" color="#0e4194">github.com/U7ama</link>', item_meta),
    ]

    photo_path = ROOT / 'Usama DP headshot.jpeg'
    if show_photo and photo_path.exists():
        photo_w = 26 * mm
        photo_h = photo_w * (842 / 891)
        img = Image(str(photo_path), width=photo_w, height=photo_h)
        header_table = Table([[contact_info, img]], colWidths=[146 * mm, 28 * mm], hAlign='LEFT')
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(header_table)
    else:
        story.extend(contact_info)

    story.append(Spacer(1, 4))
    story.append(p('Full-stack engineer with 4+ years of professional experience building production SaaS platforms, scalable APIs, and real-time AV/IoT monitoring services. Proven expertise in React, Next.js, Node.js, Python, and cloud infrastructure (AWS/GCP/Azure), with applied AI focus in tenant-scoped assistants, pgvector RAG, and multimodal integrations.'))

    # 2. Work Experience
    section('Work Experience')

    def job_entry(role, company, dates, location, bullets):
        row = Table([[
            p(f'<b>{escape(role)}</b> &nbsp;|&nbsp; <font color="#4b5563">{escape(company)}</font>', item_title),
            Paragraph(f'<font color="#0e4194"><b>{escape(dates)}</b></font><br/><font color="#64748b">{escape(location)}</font>', ParagraphStyle('d', parent=item_meta, alignment=2))
        ]], colWidths=[124 * mm, 50 * mm], hAlign='LEFT')
        row.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        items = [row, Spacer(1, 2)]
        for b in bullets:
            items.append(bullet(b))
        items.append(Spacer(1, 4))
        story.append(KeepTogether(items))

    job_entry('Full Stack Engineer', 'AlignAV', '08/2024 – 09/2026', 'Remote', [
        'Architected real-time asset-management dashboards and AV/IoT monitoring services supporting 5,000+ connected devices.',
        'Engineered Azure IoT edge services and a lightweight C# Windows monitoring client for device telemetry.',
        'Implemented tenant-scoped AI assistant with citations from verified device knowledge and validation warning workflows.',
        'Automated CI/CD deployment pipelines using Azure DevOps and Docker containers.'
    ])

    job_entry('Full Stack Developer', 'Olumi Tech', '11/2023 – 02/2025', 'Remote', [
        'Delivered full-stack web applications, REST APIs, and microservices across healthcare, travel, and e-commerce products.',
        'Integrated multimodal Gemini computer vision for real-time ingredient analysis in Cool Potato and OpenAI-powered journaling in Diary Synergy.',
        'Collaborated with international engineering teams using Agile workflows, maintaining clean code standards.'
    ])

    job_entry('Full Stack Developer', 'Xecutors', '08/2022 – 10/2023', 'Islamabad, Pakistan', [
        'Developed Node.js microservices behind Kong API Gateway using OpenAPI 3 specifications and OAuth 2.0 authentication.',
        'Automated multi-cloud infrastructure with Terraform and deployed Kong Ingress controller on GKE/Anthos.',
        'Engineered independently deployable Next.js/TypeScript microfrontends and integrated PostgreSQL/GraphQL services for billing, messaging, and digital document workflows.'
    ])

    job_entry('MERN Stack Developer', 'Stash Technologies', '03/2022 – 08/2022', 'Remote', [
        'Engineered hotel discovery and booking flows for Roomph.pk with React, Node.js, and MongoDB.',
        'Optimised client-side state management, cutting redundant API requests and page re-render cycles.'
    ])

    # 3. Education and Training (Starts Page 2 cleanly)
    from reportlab.platypus import PageBreak
    story.append(PageBreak())
    section('Education and Training')
    edu_row = Table([[
        p('<b>Bachelor of Science in Computer Science (BSCS)</b><br/>'
          '<font color="#4b5563">PMAS Arid Agriculture University, Rawalpindi, Pakistan</font><br/>'
          '<font color="#64748b"><b>EQF Level:</b> EQF Level 6 &nbsp;|&nbsp; <b>Academic Standing:</b> CGPA 3.30 / 4.00 (Aggregate: 70.42%)<br/>'
          '<b>Language of Instruction:</b> English (Certified English-medium curriculum)</font>', item_title),
        Paragraph('<font color="#0e4194"><b>2018 – 2022</b></font><br/><font color="#64748b">Rawalpindi, Pakistan</font>', ParagraphStyle('ed', parent=item_meta, alignment=2))
    ]], colWidths=[124 * mm, 50 * mm], hAlign='LEFT')
    edu_row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    edu_hssc = Table([[
        p('<b>Higher Secondary School Certificate (HSSC) – Pre-Engineering</b><br/>'
          '<font color="#4b5563">Board of Intermediate and Secondary Education (BISE), Gujranwala, Pakistan</font><br/>'
          '<font color="#64748b"><b>EQF Level:</b> EQF Level 4 &nbsp;|&nbsp; <b>Curriculum:</b> Mathematics, Physics, Chemistry, English</font>', item_title),
        Paragraph('<font color="#0e4194"><b>2015 – 2017</b></font><br/><font color="#64748b">Gujranwala, Pakistan</font>', ParagraphStyle('ed2', parent=item_meta, alignment=2))
    ]], colWidths=[124 * mm, 50 * mm], hAlign='LEFT')
    edu_hssc.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    edu_ssc = Table([[
        p('<b>Secondary School Certificate (SSC) – Science</b><br/>'
          '<font color="#4b5563">Board of Intermediate and Secondary Education (BISE), Gujranwala, Pakistan</font><br/>'
          '<font color="#64748b"><b>EQF Level:</b> EQF Level 3/4 &nbsp;|&nbsp; <b>Curriculum:</b> Science, Mathematics, Physics, Chemistry</font>', item_title),
        Paragraph('<font color="#0e4194"><b>2013 – 2015</b></font><br/><font color="#64748b">Gujranwala, Pakistan</font>', ParagraphStyle('ed3', parent=item_meta, alignment=2))
    ]], colWidths=[124 * mm, 50 * mm], hAlign='LEFT')
    edu_ssc.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    story.append(KeepTogether([edu_row, Spacer(1, 4), edu_hssc, Spacer(1, 4), edu_ssc, Spacer(1, 4)]))

    # 4. Language Skills (Official Europass CEFR Grid)
    section('Language Skills')
    story.append(p('<b>Mother tongue(s):</b> Urdu, Punjabi', body))
    story.append(Spacer(1, 2))
    story.append(p('<b>Other language(s): English</b>', body_bold))

    cefr_data = [
        [
            p('<b>UNDERSTANDING</b>', ParagraphStyle('ch', parent=small, fontName='EUBold', alignment=1, textColor=EU_BLUE)), '',
            p('<b>SPEAKING</b>', ParagraphStyle('ch', parent=small, fontName='EUBold', alignment=1, textColor=EU_BLUE)), '',
            p('<b>WRITING</b>', ParagraphStyle('ch', parent=small, fontName='EUBold', alignment=1, textColor=EU_BLUE))
        ],
        [
            p('Listening', small), p('Reading', small),
            p('Spoken interaction', small), p('Spoken production', small),
            p('Writing', small)
        ],
        [
            p('<b>C1</b> Proficient', small), p('<b>C1</b> Proficient', small),
            p('<b>C1</b> Proficient', small), p('<b>C1</b> Proficient', small),
            p('<b>C1</b> Proficient', small)
        ]
    ]
    cefr_table = Table(cefr_data, colWidths=[34.8 * mm] * 5, hAlign='LEFT')
    cefr_table.setStyle(TableStyle([
        ('SPAN', (0,0), (1,0)),
        ('SPAN', (2,0), (3,0)),
        ('BACKGROUND', (0,0), (-1,0), EU_BG_LIGHT),
        ('GRID', (0,0), (-1,-1), 0.5, EU_BORDER),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(cefr_table)
    story.append(Spacer(1, 2))
    story.append(p('<font size="7.5" color="#64748b">Levels: A1 and A2: Basic user; B1 and B2: Independent user; C1 and C2: Proficient user (Common European Framework of Reference for Languages)</font>', small))

    # 5. Digital Competences
    section('Digital Competences')
    skills = [
        ('Programming & Scripting', 'TypeScript, JavaScript, Python, C#, SQL, HTML5, CSS3'),
        ('Frontend Frameworks', 'React, Next.js, Tailwind CSS, Three.js, WebGL, Playwright (E2E)'),
        ('Backend & Cloud', 'Node.js, FastAPI, RESTful APIs, GraphQL, AWS, GCP, Azure, Docker, Kubernetes, Terraform'),
        ('Databases & Storage', 'PostgreSQL, MongoDB, MySQL, Redis, DynamoDB, Cosmos DB, pgvector'),
        ('Applied AI & Workflows', 'Retrieval-Augmented Generation (RAG), LLM Integrations (OpenAI, Gemini), n8n, AI Agents, SSE Streaming')
    ]
    for category, items in skills:
        story.append(p(f'&#8226; <b>{category}:</b> {items}', bullet_style))

    # 6. Selected Projects
    section('Selected Projects')
    projects = [
        ('Blindspot Edu', 'https://blindspot-edu.online', 'Next.js/FastAPI lecture-learning platform with Whisper transcription, Qwen prerequisite diagnostics, worked examples, reassessment, and timestamped evidence; AWS hosting with S3, Polly, and SES.'),
        ('DeviceOps AI Copilot', 'https://github.com/U7ama/deviceops-ai-copilot', 'Multi-tenant AI copilot with pgvector RAG, approval-gated workflows, signed n8n automation, Expo mobile companion, and 40-case evaluation suite.'),
        ('Copilot Travel', 'https://copilottravel.com/', 'Enterprise flight search and booking UI component built with Next.js and TypeScript.'),
        ('Sunridge Medical', 'https://sunridgemedical.com/', 'Clinic management dashboard for patient records, appointments, and laboratory-result workflows.'),
        ('Interactive 3D & OS Portfolio', 'https://portfolio.usamaaslam.site/', 'Modular personal portfolio ecosystem featuring Three.js 3D graphics and desktop OS-style browser interface.')
    ]
    for name, link, desc in projects:
        story.append(p(f'&#8226; <b><link href="{link}" color="#0e4194">{name}</link>:</b> {desc}', bullet_style))

    # 7. Academic References
    section('Academic References')
    refs = [
        '<b>Dr. Tariq Ali:</b> Associate Professor, University Institute of Information Technology (UIIT), PMAS Arid Agriculture University, Rawalpindi, Pakistan.',
        '<b>Dr. Saif ur Rehman:</b> Associate Professor, University Institute of Information Technology (UIIT), PMAS Arid Agriculture University, Rawalpindi, Pakistan.',
        '<i>Official letters of recommendation and English-medium instruction certificate available on request.</i>'
    ]
    for r in refs:
        story.append(p(f'&#8226; {r}', bullet_style))

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title='Europass Curriculum Vitae - Usama Aslam',
        author='Usama Aslam'
    )
    doc.build(story)
    print(f'Generated: {out_path}')

if __name__ == '__main__':
    out_dir = ROOT / 'output/pdf'
    out_dir.mkdir(parents=True, exist_ok=True)
    build_pdf(out_dir / 'Usama_Aslam_Europass_CV.pdf', show_photo=True)
    build_pdf(out_dir / 'Usama_Aslam_Europass_CV_No_Photo.pdf', show_photo=False)
    # Mirror directly to output/
    (ROOT / 'output').mkdir(parents=True, exist_ok=True)
    build_pdf(ROOT / 'output/Usama_Aslam_Europass_CV.pdf', show_photo=True)
    build_pdf(ROOT / 'output/Usama_Aslam_Europass_CV_No_Photo.pdf', show_photo=False)
