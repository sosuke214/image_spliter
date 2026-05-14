import streamlit as st
from PIL import Image, ImageDraw
import io
import math

# --- コールバック関数（値が変更された時に呼ばれる） ---
def update_width():
    # 縦幅が変更されたら、縦横比を使って横幅を再計算
    st.session_state.target_width = st.session_state.target_height * st.session_state.aspect_ratio

def update_height():
    # 横幅が変更されたら、縦横比を使って縦幅を再計算
    if st.session_state.aspect_ratio > 0:
        st.session_state.target_height = st.session_state.target_width / st.session_state.aspect_ratio

# --- セッションステート（状態保存）の初期化 ---
if 'target_height' not in st.session_state:
    st.session_state.target_height = 15.0
if 'target_width' not in st.session_state:
    st.session_state.target_width = 15.0
if 'aspect_ratio' not in st.session_state:
    st.session_state.aspect_ratio = 1.0
if 'uploaded_filename' not in st.session_state:
    st.session_state.uploaded_filename = ""

# --- 用紙サイズの定義（短辺, 長辺）センチメートル ---
PAPER_SIZES = {
    "A3": (29.7, 42.0),
    "A4": (21.0, 29.7),
    "B4": (25.7, 36.4),
    "B5": (18.2, 25.7)
}

# --- 点線を描画するヘルパー関数 ---
def draw_dashed_line(draw, start, end, fill="red", width=3, dash_length=15):
    x1, y1 = start
    x2, y2 = end
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0: return
    dashes = int(length / dash_length)
    for i in range(dashes):
        if i % 2 == 0:
            t1 = i / dashes
            t2 = min((i + 1) / dashes, 1.0)
            xs = x1 + (x2 - x1) * t1
            ys = y1 + (y2 - y1) * t1
            xe = x1 + (x2 - x1) * t2
            ye = y1 + (y2 - y1) * t2
            draw.line([(xs, ys), (xe, ye)], fill=fill, width=width)

def draw_dashed_rectangle(draw, top_left, bottom_right, fill="red", width=3, dash_length=15):
    x1, y1 = top_left
    x2, y2 = bottom_right
    draw_dashed_line(draw, (x1, y1), (x2, y1), fill=fill, width=width, dash_length=dash_length)
    draw_dashed_line(draw, (x2, y1), (x2, y2), fill=fill, width=width, dash_length=dash_length)
    draw_dashed_line(draw, (x2, y2), (x1, y2), fill=fill, width=width, dash_length=dash_length)
    draw_dashed_line(draw, (x1, y2), (x1, y1), fill=fill, width=width, dash_length=dash_length)

# --- Streamlit アプリ本体 ---
st.set_page_config(page_title="ポスター分割印刷メーカー", layout="centered")

st.title("ポスター分割印刷メーカー")
st.write("横長や大きな画像を、指定したサイズで複数枚の用紙に分割してPDF化する。")

# メイン画面：まず画像をアップロードさせる
uploaded_file = st.file_uploader("分割したい画像をアップロードしてください", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    original_image = Image.open(uploaded_file)
    if original_image.mode != 'RGB':
        original_image = original_image.convert('RGB')
        
    img_w, img_h = original_image.size
    
    # 画像の縦横比を計算
    aspect_ratio = img_w / img_h
    
    # 新しい画像がアップロードされた時に、比率と横幅の初期値をセットする
    if st.session_state.uploaded_filename != uploaded_file.name:
        st.session_state.aspect_ratio = aspect_ratio
        st.session_state.target_width = st.session_state.target_height * aspect_ratio
        st.session_state.uploaded_filename = uploaded_file.name

    # --- サイドバーの設定UI ---
    st.sidebar.header("印刷設定")
    
    # 縦幅と横幅の入力欄
    st.sidebar.number_input("仕上がりの縦幅 (cm)", min_value=1.0, step=1.0, 
                            key="target_height", on_change=update_width)
    st.sidebar.number_input("仕上がりの横幅 (cm)", min_value=1.0, step=1.0, 
                            key="target_width", on_change=update_height)
    
    # 用紙サイズと向きの選択
    paper_size = st.sidebar.selectbox("用紙サイズ", list(PAPER_SIZES.keys()), index=1)
    page_orientation = st.sidebar.radio("用紙の向き", ["横", "縦"])
    overlap_cm = st.sidebar.number_input("のり代 (cm)", min_value=0.0, value=1.0, step=0.1)

    # 現在の縦幅を取得して計算処理へ
    target_height_cm = st.session_state.target_height
    pixel_per_cm = img_h / target_height_cm
    dpi = pixel_per_cm * 2.54 
    
    # 選択された用紙サイズ（A3, A4など）の物理サイズを取得
    short_side_cm, long_side_cm = PAPER_SIZES[paper_size]
    
    if page_orientation == "横":
        paper_w_cm, paper_h_cm = long_side_cm, short_side_cm
    else:
        paper_w_cm, paper_h_cm = short_side_cm, long_side_cm
        
    page_w_px = paper_w_cm * pixel_per_cm
    page_h_px = paper_h_cm * pixel_per_cm
    overlap_px = overlap_cm * pixel_per_cm

    # --- プレビュー画像の生成 ---
    preview_img = original_image.copy()
    draw = ImageDraw.Draw(preview_img)
    
    line_width = max(3, int(img_h * 0.005))
    dash_len = max(10, int(img_h * 0.02))

    pages_info = [] 
    
    top = 0
    while top < img_h:
        bottom = top + page_h_px
        left = 0
        while left < img_w:
            right = left + page_w_px
            
            crop_left = int(left)
            crop_top = int(top)
            crop_right = int(min(right, img_w))
            crop_bottom = int(min(bottom, img_h))
            
            pages_info.append((crop_left, crop_top, crop_right, crop_bottom))
            
            draw_dashed_rectangle(draw, (crop_left, crop_top), (crop_right, crop_bottom), 
                                  fill="red", width=line_width, dash_length=dash_len)
            
            left += (page_w_px - overlap_px)
            if (page_w_px - overlap_px) <= 0: break
        top += (page_h_px - overlap_px)
        if (page_h_px - overlap_px) <= 0: break

    # プレビューの表示
    st.subheader(f"分割プレビュー（全 {len(pages_info)} 枚）")
    st.write(f"赤い点線が、{paper_size}用紙1枚ごとの切り出し範囲だ。重なり（のり代）も視覚的に確認できる。")
    st.image(preview_img, use_container_width=True)

    # --- PDFの生成とダウンロード ---
    if st.button("PDFを作成する"):
        with st.spinner("PDFを生成中..."):
            pages = []
            for (crop_left, crop_top, crop_right, crop_bottom) in pages_info:
                cropped = original_image.crop((crop_left, crop_top, crop_right, crop_bottom))
                canvas = Image.new('RGB', (int(page_w_px), int(page_h_px)), (255, 255, 255))
                canvas.paste(cropped, (0, 0))
                pages.append(canvas)
            
            if pages:
                pdf_bytes = io.BytesIO()
                pages[0].save(pdf_bytes, format='PDF', save_all=True, append_images=pages[1:], resolution=dpi)
                
                st.success(f"成功: {len(pages)}枚の{paper_size}用紙（{page_orientation}）に分割完了！")
                
                st.download_button(
                    label="📥 分割されたPDFをダウンロード",
                    data=pdf_bytes.getvalue(),
                    file_name="split_poster.pdf",
                    mime="application/pdf"
                )