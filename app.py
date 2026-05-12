import streamlit as st
from PIL import Image
import io

st.title("ポスター分割印刷メーカー")
st.write("横長や大きな画像を、指定したサイズでA4用紙に分割してPDF化します。")

# サイドバーに設定項目を配置
st.sidebar.header("印刷設定")
target_height_cm = st.sidebar.number_input("仕上がりの縦幅 (cm)", min_value=1.0, value=15.0, step=1.0)
page_orientation = st.sidebar.radio("A4用紙の向き", ["横", "縦"])
overlap_cm = st.sidebar.number_input("のり代 (cm)", min_value=0.0, value=1.0, step=0.1)

# メイン画面：画像のアップロード
uploaded_file = st.file_uploader("分割したい画像をアップロード", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # 画像のプレビュー表示
    image = Image.open(uploaded_file)
    st.image(image, caption="アップロードされた画像", use_container_width=True)
    
    # 実行ボタン
    if st.button("PDFを作成する"):
        with st.spinner("PDFを生成中..."):
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            img_w, img_h = image.size
            pixel_per_cm = img_h / target_height_cm
            dpi = pixel_per_cm * 2.54 
            
            if page_orientation == "横":
                a4_w_cm, a4_h_cm = 29.7, 21.0
            else:
                a4_w_cm, a4_h_cm = 21.0, 29.7
                
            page_w_px = a4_w_cm * pixel_per_cm
            page_h_px = a4_h_cm * pixel_per_cm
            overlap_px = overlap_cm * pixel_per_cm
            
            pages = []
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
                    
                    cropped = image.crop((crop_left, crop_top, crop_right, crop_bottom))
                    canvas = Image.new('RGB', (int(page_w_px), int(page_h_px)), (255, 255, 255))
                    canvas.paste(cropped, (0, 0))
                    pages.append(canvas)
                    
                    left += (page_w_px - overlap_px)
                    if (page_w_px - overlap_px) <= 0: break
                top += (page_h_px - overlap_px)
                if (page_h_px - overlap_px) <= 0: break
            
            if pages:
                # メモリ上にPDFデータを書き出す
                pdf_bytes = io.BytesIO()
                pages[0].save(pdf_bytes, format='PDF', save_all=True, append_images=pages[1:], resolution=dpi)
                
                st.success(f"成功: {len(pages)}枚のA4用紙（{page_orientation}）に分割完了！")
                
                # ダウンロードボタンの表示
                st.download_button(
                    label="📥 分割されたPDFをダウンロード",
                    data=pdf_bytes.getvalue(),
                    file_name="split_poster.pdf",
                    mime="application/pdf"
                )
