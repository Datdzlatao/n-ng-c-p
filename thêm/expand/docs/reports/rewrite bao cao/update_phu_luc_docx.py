import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def update_phu_luc():
    orig_path = "/home/minhphuc/Diem-danh-STEM/docs/reports/rewrite bao cao/PHỤ LỤC 01 - BAN_GOC_BACKUP.docx"
    output_path = "/home/minhphuc/Diem-danh-STEM/docs/reports/rewrite bao cao/PHỤ LỤC 01.docx"

    orig_doc = Document(orig_path)
    new_doc = Document()

    # 1. Căn lề trang chuẩn
    for s in new_doc.sections:
        s.top_margin = Cm(2.5)
        s.bottom_margin = Cm(2.5)
        s.left_margin = Cm(3.0)
        s.right_margin = Cm(2.0)
        s.page_width = Cm(21.0)
        s.page_height = Cm(29.7)

    # 2. Cấu hình Style mặc định: Times New Roman, 14pt
    normal_style = new_doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(14)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.35
    normal_style.paragraph_format.space_after = Pt(6)
    normal_style.paragraph_format.space_before = Pt(0)

    def format_run(r, bold=False, italic=False, size=14, color=RGBColor(0, 0, 0)):
        r.font.name = 'Times New Roman'
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.color.rgb = color

    def add_p(text="", align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True, bold=False, italic=False, size=14, space_before=0, space_after=6):
        p = new_doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.first_line_indent = Cm(1.27) if indent else Cm(0)
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.35
        if text:
            r = p.add_run(text)
            format_run(r, bold=bold, italic=italic, size=size)
        return p

    def add_sec_title(text):
        p = new_doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.line_spacing = 1.35
        r = p.add_run(text)
        format_run(r, bold=True, size=14)
        return p

    def add_subsec_title(text):
        p = new_doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.35
        r = p.add_run(text)
        format_run(r, bold=True, size=14)
        return p

    def add_step_title(step_text, desc_text=""):
        p = new_doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.first_line_indent = Cm(1.27)
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.35
        r1 = p.add_run(step_text)
        format_run(r1, bold=True, size=14)
        if desc_text:
            r2 = p.add_run(desc_text)
            format_run(r2, bold=False, size=14)
        return p

    def add_image_placeholder(caption_text, placeholder_text="[Hình ảnh minh họa]"):
        tbl = new_doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = tbl.cell(0, 0)
        cell.width = Cm(15.5)
        
        tcPr = cell._tc.get_or_add_tcPr()
        borders = parse_xml(f'''
            <w:tcBorders {nsdecls("w")}>
                <w:top w:val="dashed" w:sz="6" w:space="0" w:color="A0AEC0"/>
                <w:left w:val="dashed" w:sz="6" w:space="0" w:color="A0AEC0"/>
                <w:bottom w:val="dashed" w:sz="6" w:space="0" w:color="A0AEC0"/>
                <w:right w:val="dashed" w:sz="6" w:space="0" w:color="A0AEC0"/>
            </w:tcBorders>
        ''')
        tcPr.append(borders)
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F7FAFC"/>')
        tcPr.append(shading)

        cp = cell.paragraphs[0]
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.paragraph_format.space_before = Pt(14)
        cp.paragraph_format.space_after = Pt(14)
        cp.paragraph_format.line_spacing = 1.15
        cr = cp.add_run(f"📷 {placeholder_text}\n(Chèn ảnh chụp thực tế vào khung này)")
        format_run(cr, italic=True, size=11, color=RGBColor(113, 128, 150))

        cap_p = new_doc.add_paragraph()
        cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap_p.paragraph_format.first_line_indent = Cm(0)
        cap_p.paragraph_format.space_before = Pt(4)
        cap_p.paragraph_format.space_after = Pt(10)
        r_cap = cap_p.add_run(caption_text)
        format_run(r_cap, italic=True, size=12, color=RGBColor(40, 40, 40))

    # Xác định các đoạn trước Phụ lục 03 và sau Phụ lục 03
    p3_start = None
    p4_start = None
    for i, p in enumerate(orig_doc.paragraphs):
        txt = p.text.strip()
        if "PHỤ LỤC 03" in txt and p3_start is None:
            p3_start = i
        elif "PHỤ LỤC 04" in txt and p4_start is None:
            p4_start = i

    print(f"Phụ lục 03 bắt đầu tại: {p3_start}, Phụ lục 04 bắt đầu tại: {p4_start}")

    # 1. Chép lại Phụ lục 01 và Phụ lục 02
    for i in range(p3_start):
        p_orig = orig_doc.paragraphs[i]
        txt = p_orig.text
        if not txt.strip() and p_orig.text == "":
            continue
        p_new = new_doc.add_paragraph()
        p_new.alignment = p_orig.alignment
        p_new.paragraph_format.first_line_indent = p_orig.paragraph_format.first_line_indent
        p_new.paragraph_format.space_before = p_orig.paragraph_format.space_before or Pt(0)
        p_new.paragraph_format.space_after = p_orig.paragraph_format.space_after or Pt(4)
        p_new.paragraph_format.line_spacing = p_orig.paragraph_format.line_spacing or 1.35
        for r in p_orig.runs:
            r_new = p_new.add_run(r.text)
            f_size = r.font.size.pt if r.font.size else 14
            format_run(r_new, bold=r.bold, italic=r.italic, size=f_size)

    # 2. XÂY DỰNG LẠI HOÀN TOÀN PHỤ LỤC 03: NHẬT KÝ THỰC NGHIỆM VÀ QUY TRÌNH KỸ THUẬT CHI TIẾT
    add_sec_title("PHỤ LỤC 03")
    add_sec_title("NHẬT KÝ THỰC NGHIỆM VÀ QUY TRÌNH KỸ THUẬT CHI TIẾT CỦA DỰ ÁN")

    # Mục 1: Nhận diện khuôn mặt & Chuông cảnh báo
    add_subsec_title("1. Kỹ thuật nhận diện khuôn mặt đa tầng và phản hồi tại cổng trường")
    add_p("Module nhận diện khuôn mặt face_engine.py sử dụng kiến trúc phân tầng tốc độ cao kết hợp giữa thị giác máy tính truyền thống và mạng nơ-ron học sâu:")
    add_p("(1) Lớp 01 - Haar Cascade (cv2.CascadeClassifier): Bộ phát hiện khuôn mặt cổ điển của OpenCV, hoạt động dựa trên các đặc trưng Haar (Haar-like features). Với tốc độ xử lý vượt trội, Haar Cascade được kích hoạt trên toàn bộ khung hình chỉ để xác định tọa độ vùng khuôn mặt (bounding box) mà không tốn nhiều tài nguyên tính toán.")
    add_p("(2) Lớp 02 - Trích xuất đặc trưng 128 chiều bằng dlib (face_recognition): Sử dụng mạng nơ-ron tích chập sâu để trích xuất 128 số thực (128-D face embedding) đại diện cho từng khuôn mặt. Để xác nhận danh tính, hệ thống tính khoảng cách Euclid giữa vector khuôn mặt hiện tại và vector mẫu đã đăng ký của học sinh. Nếu khoảng cách nhỏ hơn ngưỡng cho phép (FACE_TOLERANCE = 0.50), hệ thống xác nhận chính xác đúng người.")
    add_p("(3) Cơ chế điều phối khung hình (FACE_SKIP_FRAMES = 5): Do Lớp 2 tính toán nặng, hệ thống chỉ gọi mô hình trích xuất đặc trưng sau mỗi 5 khung hình. Các khung hình xen kẽ kế tiếp sẽ giữ nguyên kết quả gần nhất để vẽ khung và thông tin. Nhờ đó, chuỗi hình ảnh từ camera đạt độ mượt mà từ 25 - 30 FPS, hoàn toàn không gây hiện tượng giật lag cho máy tính.")
    add_p("(4) Phản hồi trực quan bằng màu sắc và chuông báo âm thanh tại chỗ:")
    add_p("- Khung xanh lá: QR hợp lệ và khuôn mặt khớp -> Điểm danh thành công. Kèm 01 tiếng 'Beep' ngắn vui tai.")
    add_p("- Khung vàng cam: Đã quét QR, đang chờ xác thực khuôn mặt trong 10 giây.")
    add_p("- Khung đỏ: Người lạ (khuôn mặt không có trong danh sách) hoặc vi phạm trang phục. Kèm chuông cảnh báo 'Tít - tít - tít' kéo dài để thông báo cho người trực tại cổng trường và phòng học.")
    add_image_placeholder("Hình PL03.1: Kết quả nhận diện khuôn mặt kết hợp Haar Cascade, trích xuất đặc trưng 128-D và chuông cảnh báo âm thanh", "Mã nguồn và giao diện nhận diện khuôn mặt")

    # Mục 2: Quy trình phát hiện thân người và phân vùng áo quần
    add_subsec_title("2. Quy trình phát hiện thân người và phân vùng trang phục (HOG + SVM + Fallback)")
    add_p("Module person_detector.py thực hiện việc phân vùng trang phục theo quy trình 3 bước chặt chẽ:")
    add_p("- Bước 1 (Phát hiện thân người bằng HOG + SVM): Sử dụng bộ mô tả biểu đồ hướng Gradient kết hợp phân loại SVM (cv2.HOGDescriptor() + getDefaultPeopleDetector()). Ảnh được chia thành các ô nhỏ để tính phân phối hướng của gradient cường độ điểm ảnh, từ đó xác định có người trong khung hình hay không.")
    add_p("- Bước 2 (Cơ chế dự phòng thông minh Fallback Face-to-Body): Khi học sinh đứng gần hoặc góc camera bị khuất nửa thân khiến HOG không phát hiện được dáng người, hệ thống tự động ước lượng vùng thân từ vị trí khuôn mặt tìm thấy theo tỷ lệ nhân trắc học: Chiều rộng thân = 1.8 × chiều rộng mặt; Chiều cao thân = 7.0 × chiều cao mặt.")
    add_p("- Bước 3 (Cắt và phân vùng áo - quần): Vùng thân sau đó được chia đôi theo chiều dọc: phần trên chiếm từ 12% đến 52% chiều cao là vùng áo, phần dưới từ 52% đến 90% chiều cao là vùng quần.")
    add_image_placeholder("Hình PL03.2: Sơ đồ 3 bước phát hiện và khoanh vùng 'Áo' và 'Quần' trên thân người (HOG SVM kết hợp Fallback Face-to-Body)", "Quy trình HOG và Fallback phân vùng áo quần")

    # Mục 3: Thu thập, kiểm kê và tăng cường dữ liệu trang phục
    add_subsec_title("3. Quy trình thu thập, kiểm kê và tăng cường dữ liệu huấn luyện AI")
    add_p("a) Kiểm kê dữ liệu ban đầu bằng step1_dataset_audit.py:", bold=True)
    add_p("Hệ thống cần nhận dạng hai nhóm nhãn: nhãn 'trang_phục_dân_tộc' (học sinh mặc vào Thứ Hai) và nhãn 'other' (áo trắng, áo đoàn). Bộ ảnh gốc thu thập được gồm: 211 ảnh trang phục dân tộc (thuộc 50 nhóm dân tộc) và 7 ảnh 'other'.")
    add_p("Khi chia tập dữ liệu huấn luyện (80% Train / 20% Validation), tập Train chỉ có 168 ảnh dân tộc và 10 ảnh 'other', dẫn đến hiện tượng mất cân bằng dữ liệu nghiêm trọng.")

    add_p("b) Kỹ thuật tăng cường dữ liệu (Data Augmentation) bằng step1_data_prep_v2.py:", bold=True)
    add_p("Để giải quyết sự chênh lệch trên, hệ thống áp dụng các phép biến đổi ngẫu nhiên: xoay ±15°, lật ngang, thay đổi độ sáng và độ tương phản với tỷ lệ nhân bản có chọn lọc:")
    add_p("- Nhãn 'trang_phục_dân_tộc': Nhân bản gấp 4 lần (168 ảnh gốc × 4 = 672 ảnh train).")
    add_p("- Nhãn 'other': Do dữ liệu gốc quá ít nên được nhân bản gấp 16 lần (10 ảnh gốc × 16 = 160 ảnh train).")
    add_p("- Kết quả sau tăng cường: Tổng cộng đạt 832 ảnh huấn luyện (Train) và 46 ảnh kiểm định (Validation), giúp kéo gần khoảng cách giữa hai nhãn.")

    add_p("c) Xử lý mất cân bằng bằng trọng số phạt (class_weight):", bold=True)
    add_p("Bên cạnh việc nhân bản ảnh, trong quá trình huấn luyện mạng nơ-ron, hệ thống sử dụng tham số class_weight (từ thư viện scikit-learn). Thuật toán tự động tính hệ số phạt nặng hơn đối với nhãn có ít ảnh hơn khi dự đoán sai, buộc mô hình AI phải học đều cả hai nhãn và không bị thiên vị.")
    add_image_placeholder("Hình PL03.3: Kết quả kiểm kê dữ liệu ban đầu và số liệu sau khi tăng cường ảnh (832 ảnh train / 46 ảnh val)", "Kết quả kiểm kê và tăng cường dữ liệu")

    # Mục 4: Huấn luyện AI MobileNetV2 và TFLite
    add_subsec_title("4. Huấn luyện mô hình AI MobileNetV2 và tối ưu hóa sang TensorFlow Lite (TFLite)")
    add_p("- Kiến trúc MobileNetV2: Mạng nơ-ron tích chập (CNN) hạng nhẹ của Google, sử dụng phép tích chập tách biệt theo chiều sâu (Depthwise Separable Convolution), giúp giảm số lượng phép tính nhân lên đến 8 - 9 lần so với mạng CNN truyền thống.")
    add_p("- Chuyển giao học tập (Transfer Learning): Sử dụng trọng số đã huấn luyện sẵn từ tập dữ liệu ImageNet khổng lồ. Các tầng trích xuất đặc trưng cơ bản (góc cạnh, hoa văn, màu sắc) được giữ nguyên, chỉ huấn luyện lại tầng phân loại cuối cùng cho 2 nhãn trang phục.")
    add_p("- Xuất định dạng TFLite: Sau khi huấn luyện hoàn tất, mô hình được chuyển đổi sang định dạng TensorFlow Lite (.tflite), cho phép suy luận siêu tốc trực tiếp trên CPU với độ trễ dưới 50ms/khung hình mà không cần trang bị card đồ họa GPU đắt tiền.")
    add_image_placeholder("Hình PL03.4: Log quá trình huấn luyện mô hình MobileNetV2 và biểu đồ độ chính xác đạt 100% trên tập validation", "Quá trình huấn luyện mô hình TFLite")

    # Mục 5: Không gian màu HSV
    add_subsec_title("5. Cơ sở toán học và quy trình phân tích màu sắc trong không gian màu HSV")
    add_p("a) Cơ sở toán học của không gian màu HSV:", bold=True)
    add_p("Không gian màu HSV phân tách màu sắc thành 3 thành phần độc lập:")
    add_p("- Hue (H - Góc màu): Thể hiện sắc thái màu thuần túy trên vòng tròn màu (từ 0 đến 179 trong OpenCV). Ví dụ: màu đỏ ≈ 0/179, màu xanh lá ≈ 60, màu xanh dương ≈ 120.")
    add_p("- Saturation (S - Độ bão hòa): Thể hiện độ đậm nhạt của màu sắc (0 = màu trắng/xám xỉn, 255 = màu thuần đậm nét).")
    add_p("- Value (V - Độ sáng): Thể hiện cường độ sáng (0 = tối đen hoàn toàn, 255 = sáng tối đa).")
    add_p("Ưu điểm vượt trội của HSV so với RGB/BGR: Trong hệ màu RGB, khi ánh sáng thay đổi, cả ba giá trị R, G, B đều bị xáo trộn. Trong khi đó ở hệ HSV, sự thay đổi ánh sáng chủ yếu chỉ tác động vào thành phần V (độ sáng) mà ít làm lệch thành phần H (màu sắc), giúp việc nhận diện màu áo vô cùng ổn định dưới ánh sáng tự nhiên.")

    add_p("b) Quy trình kiểm tra màu áo thực tế (uniform_checker.py):", bold=True)
    add_p("- Bước 1: Chuyển đổi vùng ảnh áo từ BGR sang HSV qua hàm cv2.cvtColor(roi, cv2.COLOR_BGR2HSV).")
    add_p("- Bước 2: Hiệu chỉnh ngưỡng màu thực tế bằng công cụ step1_hsv_calibrator.py, cung cấp các thanh trượt trực quan trên camera để kỹ thuật viên tinh chỉnh bù trừ ánh sáng từng phòng học.")
    add_p("- Bước 3: Đánh giá tỷ lệ pixel thỏa mãn điều kiện quy định:")
    add_p("  + Áo trắng (Thứ 3, Thứ 5): Lọc các pixel có Saturation thấp (S ≤ 60) và Value cao (V ≥ 160).")
    add_p("  + Áo đoàn xanh (Thứ 6): Lọc các pixel có Hue nằm trong khoảng xanh dương (H từ 95 đến 125).")
    add_p("  + Quần tối màu: Lọc các pixel có Value thấp (V ≤ 80) trên phần lớn diện tích vùng quần.")
    add_p("c) Cơ chế định tuyến Hybrid theo tuần: Hệ thống chỉ gọi mô hình AI TFLite nặng vào Thứ Hai (áo dân tộc); gọi bộ lọc màu HSV nhẹ vào Thứ 3, 5, 6; và bỏ qua (SKIP) vào Thứ 4, Thứ 7. Nhờ đó giảm tới 65% - 70% tải tính toán của CPU.")
    add_image_placeholder("Hình PL03.5: Mô hình không gian màu HSV và công cụ kéo thanh trượt cân chỉnh ngưỡng màu thực tế", "Minh họa không gian màu HSV và công cụ calibrator")

    # Mục 6: Tự động ghi nhận bằng chứng và xử lý vi phạm
    add_subsec_title("6. Quy trình tự động ghi nhận bằng chứng và xử lý khi phát hiện vi phạm / người lạ")
    add_p("Khi hệ thống phát hiện kết quả FAIL (mặc sai quy định), UNCLEAR (không rõ nét) hoặc xuất hiện khuôn mặt người lạ, hệ thống tự động kích hoạt chuỗi xử lý bằng chứng:")
    add_p("(1) Tự động chụp lại khung hình camera hiện tại và lưu vào thư mục hệ thống data/violations/ theo định dạng chuẩn: <YYYYMMDD_HHMMSS>_<mã_HS>.jpg (hoặc gán tên STRANGER nếu là người lạ).")
    add_p("(2) Ghi dữ liệu nhật ký vi phạm bao gồm: thời gian chính xác đến từng giây, loại lỗi vi phạm cụ thể, mã học sinh và đường dẫn ảnh bằng chứng vào cơ sở dữ liệu.")
    add_p("(3) Phát còi cảnh báo âm thanh 'Tít - tít - tít' tại cổng trường và lập tức đẩy cảnh báo kèm hình ảnh về Web Dashboard của Giám thị để đối chiếu và xử lý kịp thời.")
    add_image_placeholder("Hình PL03.6: Hình ảnh học sinh vi phạm quy định trang phục và nhật ký ghi nhận vi phạm tự động", "Ảnh minh chứng vi phạm trang phục và nhật ký hệ thống")

    # 3. Chép lại Phụ lục 04 (Danh mục ảnh) nếu có
    if p4_start is not None:
        for i in range(p4_start, len(orig_doc.paragraphs)):
            p_orig = orig_doc.paragraphs[i]
            p_new = new_doc.add_paragraph()
            p_new.alignment = p_orig.alignment
            p_new.paragraph_format.first_line_indent = p_orig.paragraph_format.first_line_indent
            p_new.paragraph_format.space_before = p_orig.paragraph_format.space_before or Pt(0)
            p_new.paragraph_format.space_after = p_orig.paragraph_format.space_after or Pt(4)
            p_new.paragraph_format.line_spacing = p_orig.paragraph_format.line_spacing or 1.35
            for r in p_orig.runs:
                r_new = p_new.add_run(r.text)
                f_size = r.font.size.pt if r.font.size else 14
                format_run(r_new, bold=r.bold, italic=r.italic, size=f_size)

    new_doc.save(output_path)
    print(f"✅ Đã cập nhật thành công PHỤ LỤC 01.docx tại: {output_path}")

if __name__ == "__main__":
    update_phu_luc()
