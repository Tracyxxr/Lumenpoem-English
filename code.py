import streamlit as st
import time
import random
import io
import os
import platform
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ================= 配置区域 =================
MOCK_AI = False  

# 适配 Streamlit Cloud 部署：优先读取云端保险箱的 Key
try:
    QINIU_API_KEY = st.secrets["QINIU_API_KEY"]
except:
    # 本地测试用的备用 Key
    QINIU_API_KEY = " " 

QINIU_BASE_URL = "https://api.qnaigc.com/v1"

# ================= 视觉风格定义 =================
THEME_INK_COLOR = "#9B4D73"  # 紫红色油墨
THEME_PAPER_COLOR = "#F0EFE9" # 暖灰纸张

# ================= 辅助功能：字体加载 =================
def get_chinese_font(size=24):
    if os.path.exists("font.ttf"):
        return ImageFont.truetype("font.ttf", size)
    system = platform.system()
    try:
        if system == "Windows":
            return ImageFont.truetype("C:\\Windows\\Fonts\\msyh.ttc", size)
        elif system == "Darwin":
            return ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", size)
        else:
            return ImageFont.load_default()
    except:
        return ImageFont.load_default()

# ================= AI 核心逻辑 =================
def get_client():
    from openai import OpenAI
    return OpenAI(base_url=QINIU_BASE_URL, api_key=QINIU_API_KEY)

def get_ai_guidance(history_lines, retry=False):
    """获取写作引导"""
    if MOCK_AI:
        time.sleep(0.5)
        return "听，雨滴在窗上轻轻写下它的诗行..."
    
    try:
        client = get_client()
        context_str = "\n".join(history_lines) if history_lines else "（用户尚未开始写作）"
        
        system_prompt = "你是一位温柔的心理疗愈师。请根据用户已写的诗句，提供一句简短的（30字以内）隐喻性引导。引导用户觉察当下的身体感受或环境细微变化。语气极度温柔。不要使用引号。"
        if retry:
            system_prompt += "用户希望换一个不同的切入点。"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"用户目前写了：\n{context_str}\n\n请给我下一句的引导："}
        ]
        response = client.chat.completions.create(
            model="deepseek-v3", messages=messages, temperature=0.8, max_tokens=100, stream=False 
        )
        return response.choices[0].message.content.strip().replace('"', '').replace("“", "").replace("”", "")
    except Exception as e:
        print(f"❌ API Error: {e}")
        return "请试着深呼吸，感受当下的静谧..."

def analyze_poem_visuals(lines):
    """AI 分析诗歌色彩和意象"""
    if MOCK_AI:
        return "#9B4D73", ["star", "abstract"]

    try:
        client = get_client()
        full_poem = "\n".join(lines)
        prompt = f"""
        阅读这首诗：
        "{full_poem}"
        
        请提取两个视觉信息：
        1. 情感主色调（Hex颜色码）：激情积极用暖色，清冷伤心用冷色，默认用紫红色(#9B4D73)。
        2. 装饰意象（英文关键词，限选2个）：snow, sun, moon, star, flower, leaf, cloud, water, bird。如果没有具体意象，输出 abstract。
        
        请严格按此格式返回：COLOR:#颜色代码|ELEMENTS:意象1,意象2
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

# ================= 绘图辅助函数 =================
def draw_gradient_background(img, main_color_hex):
    """绘制梦幻晕染背景"""
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    # 基础背景色
    draw.rectangle([(0,0), (width, height)], fill="#FDFDFD")
    
    # 解析颜色
    main_color_hex = main_color_hex.replace("#", "")
    if len(main_color_hex) == 6:
        r, g, b = tuple(int(main_color_hex[i:i+2], 16) for i in (0, 2, 4))
    else:
        r, g, b = (155, 77, 115) 
        
    # 晕染层
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
    
    # 噪点
    noise = Image.new('RGBA', (width, height), (0,0,0,0))
    noise_draw = ImageDraw.Draw(noise)
    for _ in range(15000):
        x = random.randint(0, width)
        y = random.randint(0, height)
        noise_draw.point((x, y), fill=(100, 100, 100, 40))
    img.paste(noise, (0,0), noise)

def draw_element(draw, type, x, y, size, color):
    """绘制装饰元素"""
    type = type.strip()
    if type == "snow":
        draw.line([(x-size, y), (x+size, y)], fill=color, width=2)
        draw.line([(x, y-size), (x, y+size)], fill=color, width=2)
    elif type == "star":
        draw.text((x, y), "✦", font=get_chinese_font(size+10), fill=color)
    elif type == "moon":
        draw.chord((x, y, x+size, y+size), 30, 330, fill=color)
    elif type == "flower":
        draw.text((x, y), "❀", font=get_chinese_font(size+10), fill=color)
    else: # abstract
        draw.ellipse((x, y, x+size/2, y+size/2), fill=color)

# ================= 图片生成逻辑 =================
def create_poem_image(lines, reflection="", include_reflection=False):
    width = 700
    
    # 排版计算
    title_height = 100
    line_height = 55
    poem_content_height = max(150, len(lines) * line_height)
    
    reflection_part_height = 0
    if include_reflection and reflection:
        ref_lines = math.ceil(len(reflection) / 25) 
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

    title_font = get_chinese_font(48)
    text_font = get_chinese_font(28)
    small_font = get_chinese_font(18)
    
    draw.text((60, 50), "LumenPoem", fill="#333", font=title_font)
    
    y = 150
    for line in lines:
        draw.text((80, y), line, fill="#111", font=text_font)
        y += line_height
        
    if include_reflection and reflection:
        y += 30
        draw.line([(60, y), (640, y)], fill="#888", width=1)
        y += 30
        draw.text((80, y), "我的反思：", fill=main_color_hex, font=text_font)
        y += 40
        
        chars_per_line = 26
        for i in range(0, len(reflection), chars_per_line):
            line_chunk = reflection[i:i+chars_per_line]
            draw.text((80, y), line_chunk, fill="#444", font=text_font)
            y += 40

    draw.text((width - 200, total_height - 40), "LumenPoem 创作", fill="#888", font=small_font)
    
    return img

# ================= CSS 样式 =================
def local_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@300;400;700&display=swap');

    :root {{
        --ink-color: {THEME_INK_COLOR};
        --paper-color: {THEME_PAPER_COLOR};
    }}

    .stApp {{
        background-color: var(--paper-color);
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.08'/%3E%3C/svg%3E");
        font-family: 'Noto Serif SC', serif;
        color: #333;
    }}

    h1 {{
        color: var(--ink-color) !important;
        font-weight: 300 !important;
        letter-spacing: 0.1rem;
    }}

    /* 欢迎语样式：支持换行 */
    .hi-text {{
        font-size: 0.95rem;
        color: #888;
        margin-bottom: 15px;
        line-height: 1.6; /* 增加行高，让两行文字不挤 */
    }}
    .guide-text {{
        font-size: 1.4rem;
        color: var(--ink-color);
        font-family: 'Noto Serif SC', serif;
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
        font-family: 'Noto Serif SC', serif !important;
        font-size: 1.1rem !important;
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
        font-family: 'Noto Serif SC', serif !important;
    }}

    .block-container {{
        padding-top: 2rem;
    }}
    </style>
    """, unsafe_allow_html=True)

# ================= 主程序 =================
def main():
    st.set_page_config(page_title="LumenPoem", layout="wide")
    local_css()
    
    st.title("LumenPoem")

    if 'poem_lines' not in st.session_state:
        st.session_state.poem_lines = []
    if 'current_guide' not in st.session_state:
        st.session_state.current_guide = "让呼吸如羽毛般，轻轻落在你此刻的觉察上..."
    if 'app_state' not in st.session_state:
        st.session_state.app_state = "writing" 
    if 'user_reflection' not in st.session_state:
        st.session_state.user_reflection = ""

    # ============ 1. 写作模式 ============
    if st.session_state.app_state == "writing":
        col1, col2 = st.columns([1.2, 0.8], gap="large")
        
        with col1:
            # 【这里修改了欢迎语】
            st.markdown('<div class="hi-text">Hi! 欢迎你来到这里，请你察觉当下的感受，完成一首诗的创作。<br>现在，我为你提供一句提示，你可以在提示的引导下，写下一行诗</div>', unsafe_allow_html=True)
            
            p_col1, p_col2 = st.columns([4, 1.2])
            with p_col1:
                st.markdown(f'<div class="guide-text">{st.session_state.current_guide}</div>', unsafe_allow_html=True)
            with p_col2:
                if st.button("换个提示"):
                    with st.spinner("..."):
                        st.session_state.current_guide = get_ai_guidance(st.session_state.poem_lines, retry=True)
                    st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)

            def submit_line():
                if st.session_state.input_line.strip():
                    st.session_state.poem_lines.append(st.session_state.input_line)
                    st.session_state.input_line = ""
                    st.session_state.current_guide = get_ai_guidance(st.session_state.poem_lines)

            st.text_input("Input", key="input_line", on_change=submit_line, placeholder="在这里写下你的诗句...", label_visibility="collapsed")
            
            if st.session_state.poem_lines:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("完成创作"):
                    st.session_state.app_state = "reflecting"
                    st.rerun()

        with col2:
            st.markdown(f'<div style="color:{THEME_INK_COLOR}; font-weight:bold; margin-bottom:10px;">你的诗篇</div>', unsafe_allow_html=True)
            if not st.session_state.poem_lines:
                st.info("等待落笔...")
            else:
                for i, line in enumerate(st.session_state.poem_lines):
                    st.session_state.poem_lines[i] = st.text_input(f"s_line_{i}", line, label_visibility="collapsed")

    # ============ 2. 生成与反思模式 ============
    elif st.session_state.app_state == "reflecting":
        
        if st.button("←"):
            st.session_state.app_state = "writing"
            st.rerun()

        col1, col2 = st.columns([1, 1], gap="large")
        
        with col1:
            st.markdown(f'<h3 style="color:{THEME_INK_COLOR}">你的诗篇</h3>', unsafe_allow_html=True)
            st.caption("你可以在这里修改诗句，右侧的图片会随之更新")
            
            st.markdown('<div style="padding: 10px 0;">', unsafe_allow_html=True)
            for i, line in enumerate(st.session_state.poem_lines):
                st.session_state.poem_lines[i] = st.text_input(
                    f"final_line_{i}", 
                    value=line, 
                    label_visibility="collapsed"
                )
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.subheader("🌿 自我反思")
            st.markdown("""
            <div style="font-size:0.9rem; color:#666; margin-bottom:10px;">
                请写下你做这首诗时的感受。如果你感受到了不好的想法，请你知道，这些想法只是想法，不是事实。
            </div>
            """, unsafe_allow_html=True)
            
            st.session_state.user_reflection = st.text_area("Reflection", height=100, placeholder="我感觉到...", label_visibility="collapsed")
            
            include_ref = st.checkbox("在图片中包含反思", value=True)
            
            if st.button("生成图片"):
                if get_chinese_font().path == ImageFont.load_default().path:
                    st.warning("⚠️ 建议在文件夹放入 font.ttf")
                
                with st.spinner("AI 正在绘制..."):
                    img = create_poem_image(st.session_state.poem_lines, st.session_state.user_reflection, include_ref)
                
                st.image(img, caption="LumenPoem Card", use_container_width=False, width=400)
                
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                byte_im = buf.getvalue()
                st.download_button("下载保存", byte_im, "LumenPoem.png", "image/png")
            
            st.markdown("<br><br>", unsafe_allow_html=True)
            
            if st.button("再写一首"):
                st.session_state.poem_lines = []
                st.session_state.current_guide = "让呼吸如羽毛般，轻轻落在你此刻的觉察上..."
                st.session_state.app_state = "writing"
                st.session_state.user_reflection = ""
                st.rerun()

if __name__ == "__main__":

    main()
