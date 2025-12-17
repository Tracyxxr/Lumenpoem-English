import streamlit as st
import time
import random
import io
import os
import platform
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ================= Configuration =================
MOCK_AI = False  

# Cloud Secrets Logic
try:
    QINIU_API_KEY = st.secrets["QINIU_API_KEY"]
except:
    # Fallback key for local testing
    QINIU_API_KEY = "sk-80b39617f109c2380eef6058a697fa146f96b059f34423c2149e655be7d424cd" 

QINIU_BASE_URL = "https://api.qnaigc.com/v1"

# ================= Visual Style =================
THEME_INK_COLOR = "#9B4D73"  
THEME_PAPER_COLOR = "#F0EFE9" 

# ================= Helper: Font Loading =================
def get_font(size=24):
    # 1. Look for custom font file first (optional for English)
    if os.path.exists("font.ttf"):
        return ImageFont.truetype("font.ttf", size)
    
    # 2. Fallback to system Serif fonts for proper English aesthetics
    system = platform.system()
    try:
        if system == "Windows":
            return ImageFont.truetype("C:\\Windows\\Fonts\\georgia.ttf", size)
        elif system == "Darwin": # macOS
            return ImageFont.truetype("/System/Library/Fonts/Times.ttc", size)
        else:
            return ImageFont.load_default()
    except:
        return ImageFont.load_default()

# ================= AI Logic =================
def get_client():
    from openai import OpenAI
    return OpenAI(base_url=QINIU_BASE_URL, api_key=QINIU_API_KEY)

def get_ai_guidance(history_lines, retry=False):
    """Generate poetic guidance in English"""
    if MOCK_AI:
        time.sleep(0.5)
        return "Listen to the rhythm of the rain against the window..."
    
    try:
        client = get_client()
        context_str = "\n".join(history_lines) if history_lines else "(User has not started yet)"
        
        # English System Prompt
        system_prompt = (
            "You are a gentle, poetic therapist. Based on the user's poem lines, "
            "provide a short (under 30 words) metaphorical writing prompt in English. "
            "Guide the user to notice their body sensations (breath, heartbeat, touch) "
            "or subtle environmental changes (light, sound). "
            "Tone: extremely gentle, soothing, and lyrical. Do not use quotation marks."
        )
        if retry:
            system_prompt += " The user wants a different perspective or metaphor."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User's current poem:\n{context_str}\n\nPlease provide the next guidance prompt:"}
        ]
        response = client.chat.completions.create(
            model="deepseek-v3", messages=messages, temperature=0.8, max_tokens=100, stream=False 
        )
        return response.choices[0].message.content.strip().replace('"', '').replace("“", "").replace("”", "")
    except Exception as e:
        print(f"❌ API Error: {e}")
        return "Breathe deeply, and feel the stillness of this moment..."

def analyze_poem_visuals(lines):
    """Analyze poem for color and imagery"""
    if MOCK_AI:
        return "#9B4D73", ["star", "abstract"]

    try:
        client = get_client()
        full_poem = "\n".join(lines)
        prompt = f"""
        Read this poem:
        "{full_poem}"
        
        Extract two visual elements:
        1. Emotional Color (Hex Code): Warm colors for passion/joy, Cool colors for sadness/calm. Default to Purple (#9B4D73).
        2. Decorative Elements (Keywords, choose 2): snow, sun, moon, star, flower, leaf, cloud, water, bird. If none fit, use 'abstract'.
        
        Return strictly in this format: COLOR:#HexCode|ELEMENTS:element1,element2
        """
        response = client.chat.completions.create(
            model="deepseek-v3",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=50
        )
        content = response.choices[0].message.content.strip()
        
        color = "#9B4D73"
        elements = ["abstract"]
        
        if "|" in content:
            parts = content.split("|")
            for part in parts:
                if "COLOR:" in part:
                    color = part.replace("COLOR:", "").strip()
                if "ELEMENTS:" in part:
                    elements = part.replace("ELEMENTS:", "").strip().split(",")
        return color, elements
    except:
        return "#9B4D73", ["abstract"]

# ================= Drawing Helpers =================
def draw_gradient_background(img, main_color_hex):
    """Draw dreamy gradient background"""
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    draw.rectangle([(0,0), (width, height)], fill="#FDFDFD")
    
    main_color_hex = main_color_hex.replace("#", "")
    if len(main_color_hex) == 6:
        r, g, b = tuple(int(main_color_hex[i:i+2], 16) for i in (0, 2, 4))
    else:
        r, g, b = (155, 77, 115) 
        
    layers = Image.new('RGBA', (width, height), (0,0,0,0))
    layer_draw = ImageDraw.Draw(layers)
    
    for _ in range(4):
        x = random.randint(0, width)
        y = random.randint(0, height)
        radius = random.randint(200, 500)
        opacity = random.randint(20, 60)
        layer_draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(r, g, b, opacity))
        
    layers = layers.filter(ImageFilter.GaussianBlur(radius=100))
    img.paste(layers, (0,0), layers)
    
    noise = Image.new('RGBA', (width, height), (0,0,0,0))
    noise_draw = ImageDraw.Draw(noise)
    for _ in range(15000):
        x = random.randint(0, width)
        y = random.randint(0, height)
        noise_draw.point((x, y), fill=(100, 100, 100, 40))
    img.paste(noise, (0,0), noise)

def draw_element(draw, type, x, y, size, color):
    """Draw decorative elements"""
    type = type.strip().lower()
    if type == "snow":
        draw.line([(x-size, y), (x+size, y)], fill=color, width=2)
        draw.line([(x, y-size), (x, y+size)], fill=color, width=2)
    elif type == "star":
        draw.text((x, y), "✦", font=get_font(size+10), fill=color)
    elif type == "moon":
        draw.chord((x, y, x+size, y+size), 30, 330, fill=color)
    elif type == "flower":
        draw.text((x, y), "❀", font=get_font(size+10), fill=color)
    else: # abstract
        draw.ellipse((x, y, x+size/2, y+size/2), fill=color)

# ================= Image Generation Logic =================
def create_poem_image(lines, reflection="", include_reflection=False):
    width = 700
    
    title_height = 100
    line_height = 55
    poem_content_height = max(150, len(lines) * line_height)
    
    reflection_part_height = 0
    if include_reflection and reflection:
        # Wrap reflection text (approx 45 chars per line for English)
        ref_lines = math.ceil(len(reflection) / 45) 
        reflection_part_height = 80 + ref_lines * 40
        
    total_height = title_height + poem_content_height + reflection_part_height + 80
    
    img = Image.new('RGB', (width, total_height), color="#FFFFFF")
    
    main_color_hex, elements = analyze_poem_visuals(lines)
    
    draw_gradient_background(img, main_color_hex)
    draw = ImageDraw.Draw(img)
    
    for _ in range(6):
        el = random.choice(elements)
        ex = random.randint(20, width-20)
        ey = random.randint(20, total_height-20)
        ecolor = main_color_hex if random.random() > 0.5 else "#FFFFFF"
        draw_element(draw, el, ex, ey, random.randint(20, 40), ecolor)

    title_font = get_font(48)
    text_font = get_font(28)
    small_font = get_font(18)
    italic_font = get_font(28) 
    
    draw.text((60, 50), "LumenPoem", fill="#333", font=title_font)
    
    y = 150
    for line in lines:
        draw.text((80, y), line, fill="#111", font=text_font)
        y += line_height
        
    if include_reflection and reflection:
        y += 30
        draw.line([(60, y), (640, y)], fill="#888", width=1)
        y += 30
        draw.text((80, y), "My Reflection:", fill=main_color_hex, font=italic_font)
        y += 40
        
        # English word wrapping logic
        chars_per_line = 45
        for i in range(0, len(reflection), chars_per_line):
            line_chunk = reflection[i:i+chars_per_line]
            draw.text((80, y), line_chunk, fill="#444", font=text_font)
            y += 40

    draw.text((width - 240, total_height - 40), "Created with LumenPoem", fill="#888", font=small_font)
    
    return img

# ================= CSS Styles =================
def local_css():
    st.markdown(f"""
    <style>
    /* Import Serif fonts for English */
    @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:ital,wght@0,300;0,400;0,600;1,400&family=Noto+Serif:ital,wght@0,400;0,700;1,400&display=swap');

    :root {{
        --ink-color: {THEME_INK_COLOR};
        --paper-color: {THEME_PAPER_COLOR};
    }}

    .stApp {{
        background-color: var(--paper-color);
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.08'/%3E%3C/svg%3E");
        font-family: 'Crimson Pro', 'Noto Serif', Georgia, serif;
        color: #333;
    }}

    h1 {{
        color: var(--ink-color) !important;
        font-weight: 300 !important;
        letter-spacing: 0.1rem;
        font-family: 'Crimson Pro', serif;
    }}

    /* Welcome text style */
    .hi-text {{
        font-size: 0.95rem;
        color: #888;
        margin-bottom: 15px;
        line-height: 1.6;
    }}
    .guide-text {{
        font-size: 1.4rem;
        color: var(--ink-color);
        font-family: 'Crimson Pro', serif;
        font-style: italic;
        line-height: 1.5;
    }}

    .stButton > button {{
        background-color: transparent !important;
        border: 1px solid var(--ink-color) !important;
        color: var(--ink-color) !important;
        border-radius: 20px !important;
        padding: 5px 15px !important;
        font-size: 0.9rem !important;
        transition: all 0.3s ease;
        font-family: 'Crimson Pro', serif;
    }}
    .stButton > button:hover {{
        background-color: var(--ink-color) !important;
        color: white !important;
    }}
    
    .back-btn-container button {{
        border: none !important;
        font-size: 1.5rem !important;
        padding: 0 !important;
    }}

    .stTextInput input {{
        background-color: transparent !important;
        border: none !important;
        border-bottom: 1px dashed rgba(155, 77, 115, 0.3) !important;
        border-radius: 0 !important;
        padding: 10px 0 !important;
        font-family: 'Crimson Pro', serif !important;
        font-size: 1.2rem !important;
        color: #222 !important;
        box-shadow: none !important;
    }}
    .stTextInput input:focus {{
        border-bottom: 1px solid var(--ink-color) !important;
    }}
    
    .stTextInput label {{
        display: none;
    }}

    .stTextArea textarea {{
        background-color: rgba(255,255,255,0.5) !important;
        border: 1px solid rgba(155, 77, 115, 0.2) !important;
        border-radius: 10px !important;
        font-family: 'Crimson Pro', serif !important;
        font-size: 1.1rem !important;
    }}

    .block-container {{
        padding-top: 2rem;
    }}
    </style>
    """, unsafe_allow_html=True)

# ================= Main App =================
def main():
    st.set_page_config(page_title="LumenPoem", layout="wide")
    local_css()
    
    st.title("LumenPoem")

    if 'poem_lines' not in st.session_state:
        st.session_state.poem_lines = []
    if 'current_guide' not in st.session_state:
        st.session_state.current_guide = "Let your breath settle lightly, like a feather, upon your awareness right now..."
    if 'app_state' not in st.session_state:
        st.session_state.app_state = "writing" 
    if 'user_reflection' not in st.session_state:
        st.session_state.user_reflection = ""

    # ============ 1. Writing Mode ============
    if st.session_state.app_state == "writing":
        col1, col2 = st.columns([1.2, 0.8], gap="large")
        
        with col1:
            # Translated Welcome Message as requested
            st.markdown('<div class="hi-text">Hi! Welcome here. Please tune into your present feelings and create a poem.<br>Now, I will provide you with a prompt. You can write a line of poetry guided by this prompt.</div>', unsafe_allow_html=True)
            
            p_col1, p_col2 = st.columns([4, 1.2])
            with p_col1:
                st.markdown(f'<div class="guide-text">{st.session_state.current_guide}</div>', unsafe_allow_html=True)
            with p_col2:
                if st.button("New Prompt"):
                    with st.spinner("..."):
                        st.session_state.current_guide = get_ai_guidance(st.session_state.poem_lines, retry=True)
                    st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)

            def submit_line():
                if st.session_state.input_line.strip():
                    st.session_state.poem_lines.append(st.session_state.input_line)
                    st.session_state.input_line = ""
                    st.session_state.current_guide = get_ai_guidance(st.session_state.poem_lines)

            st.text_input("Input", key="input_line", on_change=submit_line, placeholder="Write your line here...", label_visibility="collapsed")
            
            if st.session_state.poem_lines:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Finish Poem"):
                    st.session_state.app_state = "reflecting"
                    st.rerun()

        with col2:
            st.markdown(f'<div style="color:{THEME_INK_COLOR}; font-weight:bold; margin-bottom:10px;">Your Poem</div>', unsafe_allow_html=True)
            if not st.session_state.poem_lines:
                st.info("The page awaits...")
            else:
                for i, line in enumerate(st.session_state.poem_lines):
                    st.session_state.poem_lines[i] = st.text_input(f"s_line_{i}", line, label_visibility="collapsed")

    # ============ 2. Reflection & Generation Mode ============
    elif st.session_state.app_state == "reflecting":
        
        if st.button("← Back"):
            st.session_state.app_state = "writing"
            st.rerun()

        col1, col2 = st.columns([1, 1], gap="large")
        
        with col1:
            st.markdown(f'<h3 style="color:{THEME_INK_COLOR}">Your Poem</h3>', unsafe_allow_html=True)
            st.caption("You can modify your lines here. The image will update accordingly.")
            
            st.markdown('<div style="padding: 10px 0;">', unsafe_allow_html=True)
            for i, line in enumerate(st.session_state.poem_lines):
                st.session_state.poem_lines[i] = st.text_input(
                    f"final_line_{i}", 
                    value=line, 
                    label_visibility="collapsed"
                )
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.subheader("🌿 Self-Reflection")
            st.markdown("""
            <div style="font-size:0.9rem; color:#666; margin-bottom:10px;">
                Please write down your feelings while writing this poem. If you notice difficult thoughts, remember: thoughts are just thoughts, not facts.
            </div>
            """, unsafe_allow_html=True)
            
            st.session_state.user_reflection = st.text_area("Reflection", height=100, placeholder="I feel...", label_visibility="collapsed")
            
            include_ref = st.checkbox("Include reflection in image", value=True)
            
            if st.button("Generate Image"):
                # No warning needed for English usually
                with st.spinner("Sketching..."):
                    img = create_poem_image(st.session_state.poem_lines, st.session_state.user_reflection, include_ref)
                
                st.image(img, caption="LumenPoem Card", use_container_width=False, width=400)
                
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                byte_im = buf.getvalue()
                st.download_button("Download", byte_im, "LumenPoem.png", "image/png")
            
            st.markdown("<br><br>", unsafe_allow_html=True)
            
            if st.button("Write another poem"):
                st.session_state.poem_lines = []
                st.session_state.current_guide = "Let your breath settle lightly, like a feather, upon your awareness right now..."
                st.session_state.app_state = "writing"
                st.session_state.user_reflection = ""
                st.rerun()

if __name__ == "__main__":
    main()
