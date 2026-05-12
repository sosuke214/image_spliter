import streamlit as st
from PIL import Image, ImageDraw
import io
import math

# --- 点線を描画するヘルパー関数 ---
def draw_dashed_line(draw, start, end, fill="red", width=3, dash_length=15):
    """2点間に点線を描画する関数"""
    x1, y1 = start
    x2, y2 = end
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0: return
    dashes = int(length / dash_length)
    for i in range(dashes):
        if i % 2 == 0: # 交互に線を描く
            t1 = i / dashes
            t2 = min((i + 1) / dashes, 1.0)
            xs = x1 + (x2 - x1) * t1
            ys = y1 + (y2 - y1) * t1
            xe = x1 + (x2 - x1) * t2
            ye = y1 + (y2 - y1) * t2
            draw.line([(xs, ys), (xe, ye)], fill=fill, width=width)

def draw_dashed_rectangle(draw, top_left, bottom_right, fill="red", width=3, dash_length=15):
    """矩形（四角形）を点線で描画する関数"""
    x1, y1 = top_left
    x2, y2 = bottom_right
    draw_dashed_line(draw, (x1, y1), (x2, y1), fill=fill, width=width, dash_length=dash_length)
    draw_dashed_line(draw, (x2, y1), (x2, y2), fill=fill, width=width, dash_length=dash_length)
    draw_dashed_line(draw, (x2, y2), (x1, y2), fill=fill, width=width, dash_length=dash_length)
    draw_dashed_line(draw, (x1, y2), (x1, y1), fill=fill, width=width, dash_length=dash_length)

# --- Streamlit アプリ本体 ---
st.set_page_config(page_title="ポスター分割印刷メーカー", layout="centered")

st.title("ポスター分割印刷メーカー")
st.write("横長や大きな画像を、指定したサイズでA4用紙に分割してPDF化する。")

# サイドバーに設定項目を配置
st.sidebar.header("印刷設定")
target_height_cm = st.sidebar.number_input("仕上がりの縦幅 (cm)", min_value=1.0, value=15.0, step=1.0)
page_orientation = st.sidebar.radio("A4用紙の向き", ["横", "縦"])
overlap_cm = st.sidebar.number_input("のり代 (cm)", min_value=0.0, value=1.0, step=0.1)

# メイン画面：画像のアップロード
uploaded_file = st.file_uploader("分割したい画像をアップロード", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    original_image = Image.open(uploaded_file)
    if original_image.mode != 'RGB':
        original_image = original_image.convert('RGB')
        
    img_w, img_h = original_image.size
    
    # 計算処理（分割サイズの決定）
    pixel_per_cm = img_h / target_height_cm
    dpi = pixel_per_cm * 2.54 
    
    if page_orientation == "横":
        a4_w_cm, a4_h_cm = 29.7, 21.0
    else:
        a4_w_cm, a4_h_cm = 21.0, 29.7
        
    page_w_px = a4_w_cm * pixel_per_cm
    page_h_px = a4_h_cm * pixel_per_cm
    overlap_px = overlap_cm * pixel_per_cm

    # --- プレビュー画像の生成 ---
    preview_img = original_image.copy()
    draw = ImageDraw.Draw(preview_img)
    
    # 線の太さと破線の長さを画像解像度に合わせて自動調整
    line_width = max(3, int(img_h * 0.005))
    dash_len = max(10, int(img_h * 0.02))

    pages_info = [] # PDF生成用の切り抜き座標をストックするリスト
    
    # 分割座標の計算とプレビューへの描画
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
            
            # プレビュー画像に赤い点線の枠を描画する
            draw_dashed_rectangle(draw, (crop_left, crop_top), (crop_right, crop_bottom), 
                                  fill="red", width=line_width, dash_length=dash_len)
            
            left += (page_w_px - overlap_px)
            if (page_w_px - overlap_px) <= 0: break
        top += (page_h_px - overlap_px)
        if (page_h_px - overlap_px) <= 0: break

    # プレビューの表示
    st.subheader(f"分割プレビュー（全 {len(pages_info)} 枚）")
    st.write("赤い点線が、A4用紙1枚ごとの切り出し範囲だ。重なり（のり代）も視覚的に確認できる。")
    st.image(preview_img, use_container_width=True)

    # --- PDFの生成とダウンロード ---
    if st.button("PDFを作成する"):
        with st.spinner("PDFを生成中..."):
            pages = []
            for (crop_left, crop_top, crop_right, crop_bottom) in pages_info:
                # プレビューではなく、元のクリーンな画像から切り抜く
                cropped = original_image.crop((crop_left, crop_top, crop_right, crop_bottom))
                canvas = Image.new('RGB', (int(page_w_px), int(page_h_px)), (255, 255, 255))
                canvas.paste(cropped, (0, 0))
                pages.append(canvas)
            
            if pages:
                pdf_bytes = io.BytesIO()
                pages[0].save(pdf_bytes, format='PDF', save_all=True, append_images=pages[1:], resolution=dpi)
                
                st.success(f"成功: {len(pages)}枚のA4用紙（{page_orientation}）に分割完了！")
                
                st.download_button(
                    label="📥 分割されたPDFをダウンロード",
                    data=pdf_bytes.getvalue(),
                    file_name="split_poster.pdf",
                    mime="application/pdf"
                )
