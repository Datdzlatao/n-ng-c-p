import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os

def create_presentation_docx():
    doc = Document()

    # 1. Cấu hình lề trang theo Nghị định 30/2020/NĐ-CP (Top 2.0cm, Bottom 2.0cm, Left 3.0cm, Right 2.0cm)
    for s in doc.sections:
        s.top_margin = Cm(2.0)
        s.bottom_margin = Cm(2.0)
        s.left_margin = Cm(3.0)
        s.right_margin = Cm(2.0)
        s.page_width = Cm(21.0)
        s.page_height = Cm(29.7)

    # 2. Cấu hình font chữ chuẩn: Times New Roman, 13pt
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(13)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.3
    normal_style.paragraph_format.space_after = Pt(5)
    normal_style.paragraph_format.space_before = Pt(0)

    def format_run(r, bold=False, italic=False, size=13, color=RGBColor(0, 0, 0)):
        r.font.name = 'Times New Roman'
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.color.rgb = color

    def add_p(text="", align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True, bold=False, italic=False, size=13, space_before=0, space_after=5):
        p = doc.add_paragraph()
        p.alignment = align
        if indent:
            p.paragraph_format.first_line_indent = Cm(1.27)
        else:
            p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.3
        if text:
            r = p.add_run(text)
            format_run(r, bold=bold, italic=italic, size=size)
        return p

    def add_sec_title(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.3
        r = p.add_run(text)
        format_run(r, bold=True, size=14.5, color=RGBColor(0, 32, 96))
        return p

    def add_subsec_title(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.3
        r = p.add_run(text)
        format_run(r, bold=True, size=13.5, color=RGBColor(31, 78, 121))
        return p

    def add_subsubsec_title(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.3
        r = p.add_run(text)
        format_run(r, bold=True, italic=True, size=13)
        return p

    def add_bullet_item(bold_prefix, text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Cm(1.27)
        p.paragraph_format.first_line_indent = Cm(-0.6)
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.3
        r_b = p.add_run("• " + bold_prefix + ": ")
        format_run(r_b, bold=True, size=13)
        r_t = p.add_run(text)
        format_run(r_t, bold=False, size=13)
        return p

    def add_speech_box(speaker_title, speech_text):
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        cell = tbl.cell(0, 0)
        cell.width = Cm(16.0)
        
        tcPr = cell._element.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F2F5F9"/>')
        tcPr.append(shd)
        
        borders = parse_xml(f'''
            <w:tcBorders {nsdecls("w")}>
                <w:top w:val="none"/>
                <w:left w:val="single" w:sz="18" w:space="0" w:color="1F4E79"/>
                <w:bottom w:val="none"/>
                <w:right w:val="none"/>
            </w:tcBorders>
        ''')
        tcPr.append(borders)
        
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.25
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.first_line_indent = Cm(0)
        
        r_h = p.add_run(f"🎤 GỢI Ý LỜI THOẠI THUYẾT TRÌNH ({speaker_title}):\n")
        format_run(r_h, bold=True, size=12, color=RGBColor(31, 78, 121))
        r_b = p.add_run(f'"{speech_text}"')
        format_run(r_b, italic=True, size=12)
        
        p_space = doc.add_paragraph()
        p_space.paragraph_format.space_before = Pt(2)
        p_space.paragraph_format.space_after = Pt(4)

    # --- TIÊU ĐỀ ĐẦU TRANG THEO QUY CHUẨN ---
    header_table = doc.add_table(rows=1, cols=2)
    header_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    header_table.autofit = False

    cell_l = header_table.cell(0, 0)
    cell_r = header_table.cell(0, 1)
    cell_l.width = Cm(7.5)
    cell_r.width = Cm(8.5)

    p_l = cell_l.paragraphs[0]
    p_l.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_l.paragraph_format.line_spacing = 1.2
    p_l.paragraph_format.space_after = Pt(0)
    r = p_l.add_run("DỰ ÁN PHẦN MỀM STEM\n")
    format_run(r, bold=False, size=12.5)
    r = p_l.add_run("HỆ THỐNG EDUSAMS STEM\n")
    format_run(r, bold=True, size=12.5)
    r = p_l.add_run("Tài liệu: Kịch bản Thuyết trình")
    format_run(r, italic=True, size=11.5)

    p_r = cell_r.paragraphs[0]
    p_r.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_r.paragraph_format.line_spacing = 1.2
    p_r.paragraph_format.space_after = Pt(0)
    r = p_r.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n")
    format_run(r, bold=True, size=12.5)
    r = p_r.add_run("Độc lập - Tự do - Hạnh phúc\n")
    format_run(r, bold=True, size=12.5)
    r = p_r.add_run("---------------o0o---------------\n")
    format_run(r, bold=False, size=10)
    r = p_r.add_run("Năm học 2025 - 2026")
    format_run(r, bold=False, italic=True, size=11.5)

    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(10)
    p_sp.paragraph_format.space_after = Pt(4)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(4)
    p_title.paragraph_format.space_after = Pt(4)
    r_title = p_title.add_run("HƯỚNG DẪN & KỊCH BẢN THUYẾT TRÌNH TOÀN DIỆN\nDỰ ÁN ĐIỂM DANH & QUẢN LÝ NỀ NẾP HỌC SINH THÔNG MINH STEM")
    format_run(r_title, bold=True, size=15, color=RGBColor(0, 32, 96))

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(16)
    r_sub = p_sub.add_run("(Cấu trúc 2 tuyến nội dung: Tiến trình Nghiên cứu chế tạo R&D và Luồng Vận hành thực tế hệ thống)")
    format_run(r_sub, italic=True, size=13)

    add_p("Tài liệu này được biên soạn chuyên biệt phục vụ các buổi báo cáo dự thi Cuộc thi Nghiên cứu Khoa học Kỹ thuật (KHKT), Cuộc thi Sáng tạo Thanh thiếu niên Nhi đồng, báo cáo đồ án STEM hoặc bảo vệ giải pháp chuyển đổi số học đường trước Ban Giám hiệu nhà trường. Tài liệu cung cấp trọn vẹn cả nội dung kỹ thuật chuyên sâu và lời thoại mẫu cho từng phân cảnh trình bày.", italic=True, size=12.5)

    # =========================================================================
    # PHẦN I: TIẾN TRÌNH R&D (7 BƯỚC THIẾT KẾ KỸ THUẬT)
    # =========================================================================
    add_sec_title("PHẦN I. KỊCH BẢN THUYẾT TRÌNH THEO TỪNG BƯỚC LÀM DỰ ÁN (TIẾN TRÌNH R&D & THIẾT KẾ KỸ THUẬT STEM)")
    add_p("Tiến trình nghiên cứu và phát triển dự án được thực hiện nghiêm ngặt theo Quy trình Thiết kế Kỹ thuật (Engineering Design Process - EDP), bảo đảm tính khoa học, khả năng kiểm chứng và liêm chính học thuật qua 7 bước tuần tự:")

    # BƯỚC 1
    add_subsec_title("Bước 1: Khảo sát thực trạng & Xác định bài toán thực tiễn")
    add_p("1. Thực trạng tại các trường phổ thông: Việc quản lý học sinh hiện nay vẫn phụ thuộc lớn vào các thao tác thủ công lặp lại. Giáo viên chủ nhiệm mất trung bình 3 – 5 phút mỗi tiết chỉ để điểm danh sĩ số (tương đương 15 – 25 giờ giảng dạy bị chiếm dụng mỗi năm học cho mỗi lớp). Tại cổng trường, giám thị phải quan sát bằng mắt để kiểm tra nề nếp trang phục, dễ dẫn đến thiếu sót, tranh chấp khi không có bằng chứng hình ảnh đối chiếu.")
    add_p("2. Khoảng trống công nghệ hiện hữu: Máy chấm công vân tay hoặc thẻ từ gây ùn tắc nghiêm trọng tại cổng trường vào giờ cao điểm và không kiểm tra được tác phong đồng phục. Các hệ thống camera AI thương mại trên thị trường có chi phí đầu tư rất cao (15 – 40 triệu VNĐ/bộ), mã nguồn đóng và chỉ dừng lại ở bài toán nhận diện khuôn mặt, hoàn toàn không có khả năng kiểm tra đồng phục linh hoạt theo lịch từng ngày trong tuần của học sinh Việt Nam.")
    add_p("3. Mục tiêu kỹ thuật đặt ra: Thiết kế một hệ thống trạm thông minh với phần cứng phổ thông (chi phí dưới 3 triệu VNĐ/trạm), ứng dụng Trí tuệ nhân tạo nhận diện khuôn mặt tốc độ cao, phân loại đồng phục tự động theo thời khóa biểu và vận hành ổn định ngay cả khi mất kết nối mạng Internet.")
    add_speech_box("Mở đầu - Đặt vấn đề", 
                   "Kính thưa Ban Giám khảo, mỗi năm học có hàng chục giờ giảng dạy quý báu bị lãng phí chỉ để điểm danh gọi tên từng học sinh. Cùng với đó là áp lực của các thầy cô giám thị khi phải căng mắt kiểm tra đồng phục cho hàng nghìn học sinh tại cổng trường mỗi sáng. Để giải quyết triệt để bài toán này, nhóm chúng em đã nghiên cứu và hoàn thiện dự án: Hệ thống Điểm danh và Quản lý Nề nếp Học sinh Thông minh bằng Trí tuệ Nhân tạo Lai (Hybrid AI). Hệ thống vừa nhận diện khuôn mặt chính xác, vừa tự động kiểm tra trang phục theo quy định từng ngày trong tuần với chi phí phần cứng siêu tiết kiệm.")

    # BƯỚC 2
    add_subsec_title("Bước 2: Cơ sở lý luận & Đề xuất giải pháp liên môn STEM")
    add_p("Hệ thống là sự kết tinh chặt chẽ của 4 trụ cột giáo dục STEM:")
    add_bullet_item("S - Khoa học (Science)", "Ứng dụng nguyên lý quang học của không gian màu HSV (Hue - Saturation - Value) để phân tách thành phần màu sắc thuần khỏi cường độ sáng. Nhờ đó, việc phân loại áo trắng (S <= 60, V >= 160) và áo Đoàn thanh niên đạt độ ổn định cao trước sự thay đổi của ánh sáng tự nhiên. Đồng thời, ứng dụng khoa học nhân trắc học giải phẫu cơ thể người để ước lượng tỷ lệ thân người từ khuôn mặt khi bị góc khuất.")
    add_bullet_item("T - Công nghệ (Technology)", "Sáng tạo kiến trúc Hybrid AI có chọn lọc: Dùng mô hình học sâu MobileNetV2 lượng tử hóa (TFLite INT8) cho trang phục dân tộc có họa tiết phức tạp (Thứ 2), và chuyển sang thuật toán phân tích màu HSV cho các ngày áo trắng/áo xanh (Thứ 3, 5, 6). Giải pháp này giúp giảm tải từ 60% đến 70% tài nguyên CPU so với việc sử dụng mô hình học sâu toàn phần.")
    add_bullet_item("E - Kỹ thuật (Engineering)", "Thiết kế kiến trúc hệ thống ngoại tuyến ưu tiên (Offline-First Architecture). Trang bị bộ nhớ đệm SQLite cục bộ trên máy trạm biên tại cổng trường, bảo đảm tỷ lệ toàn vẹn dữ liệu đạt 100%, không bị mất bản ghi điểm danh dù đường truyền Internet bị đứt đoạn.")
    add_bullet_item("M - Toán học (Math)", "Ứng dụng khoảng cách Euclidean trong không gian vector đặc trưng 128 chiều để so khớp khuôn mặt; giải thuật giao cắt trên diện tích hợp (Intersection over Union - IoU) kết hợp triệt tiêu cực đại (Non-Maximum Suppression - NMS) để lọc bỏ các khung nhận diện trùng lặp.")
    add_bullet_item("Căn cứ pháp lý", "Tuân thủ nghiêm ngặt Nghị định số 13/2023/NĐ-CP của Chính phủ về Bảo vệ dữ liệu cá nhân: Dữ liệu sinh trắc học được mã hóa một chiều thành vector toán học, có phân hệ ký thỏa thuận đồng thuận của phụ huynh và chức năng thực thi quyền xóa dữ liệu theo yêu cầu.")
    add_speech_box("Giải thích Cơ sở STEM", 
                   "Điểm sáng tạo cốt lõi của đề tài nằm ở việc chúng em không lạm dụng trí tuệ nhân tạo học sâu một cách máy móc. Đối với trang phục có hoa văn phức tạp như áo truyền thống thứ Hai, chúng em dùng mô hình MobileNetV2. Nhưng đối với áo trắng và áo Đoàn, chúng em chỉ áp dụng thuật toán phân tích không gian màu HSV. Nhờ tư duy tối ưu kỹ thuật này, hệ thống đã cắt giảm được 70% tải tính toán của CPU, giúp trạm camera chạy cực kỳ mượt mà ngay trên các dòng máy tính mini hay vi máy tính Raspberry Pi giá rẻ.")

    # BƯỚC 3
    add_subsec_title("Bước 3: Thiết kế Kiến trúc Tổng thể Hệ thống")
    add_p("Hệ thống được tổ chức thành 4 phân hệ chuyên trách, kết nối chặt chẽ và an toàn:")
    add_bullet_item("1. Trạm Camera AI Biên (Edge Station)", "Đặt tại cổng trường, đảm nhiệm thu hình ảnh, phát hiện thân người (HOG), bám vết đối tượng (Tracker), chống giả mạo (Anti-spoofing), nhận diện khuôn mặt và phân loại đồng phục.")
    add_bullet_item("2. Máy chủ Dịch vụ Trung tâm (Cloud Backend)", "Xây dựng trên nền tảng FastAPI (Python), cung cấp giao diện lập trình RESTful API, quản trị dữ liệu đa trường học (Multi-Tenant SaaS), băm mật khẩu an toàn chuẩn PBKDF2 và phát sóng dữ liệu thời gian thực qua WebSockets.")
    add_bullet_item("3. Bảng điều khiển Web (Web Dashboard Launchpad)", "Giao diện trang đơn hiện đại với 5 vai trò phân quyền rạch ròi: Hiệu trưởng, Giám thị, Giáo viên chủ nhiệm, Phụ huynh và Học sinh.")
    add_bullet_item("4. Ứng dụng Di động (Mobile App Flutter)", "Tối ưu hóa trải nghiệm trên điện thoại thông minh cho phụ huynh và học sinh, hỗ trợ nhận thông báo đẩy tức thời và nộp đơn nghỉ phép trực tuyến.")
    add_speech_box("Kiến trúc Hệ thống", 
                   "Thưa Thầy Cô, hệ thống của chúng em được thiết kế theo kiến trúc Đa trường học Multi-Tenant SaaS. Điều này có nghĩa là chỉ với một máy chủ đám mây duy nhất, hệ thống có thể phục vụ hàng chục trường học độc lập, mỗi trường có cơ sở dữ liệu và cấu hình quy định riêng. Tại cổng mỗi trường chỉ cần đặt một trạm Camera AI độc lập, dữ liệu được truyền mã hóa an toàn về trung tâm.")

    # BƯỚC 4
    add_subsec_title("Bước 4: Thu thập Dữ liệu, Tiền xử lý & Huấn luyện Mô hình AI")
    add_p("1. Xây dựng tập dữ liệu (Dataset): Nhóm tiến hành thu thập và gán nhãn tập dữ liệu trang phục học đường gồm các mẫu áo truyền thống/dân tộc đa dạng vùng miền và các trang phục thường ngày. Đồng thời xây dựng bộ cơ sở dữ liệu khuôn mặt học sinh phục vụ trích xuất vector 128 chiều.")
    add_p("2. Kỹ thuật tiền xử lý và tăng cường dữ liệu (Data Augmentation): Áp dụng các phép biến đổi hình học (xoay góc nghiêng, lật gương, phóng to/thu nhỏ) và biến đổi quang học (thay đổi độ sáng, cân bằng tương phản histogram) để mô phỏng điều kiện thời tiết thực tế cổng trường. Áp dụng kỹ thuật cân bằng trọng số nhãn (class_weight) để xử lý triệt để hiện tượng mất cân bằng dữ liệu.")
    add_p("3. Lượng tử hóa mô hình (INT8 Quantization): Sau khi huấn luyện mô hình học sâu MobileNetV2 đạt độ hội tụ cao, nhóm thực hiện lượng tử hóa toàn bộ tham số từ dạng số thực dấu phẩy động 32-bit (float32) sang số nguyên 8-bit (int8). Kỹ thuật này giúp giảm kích thước mô hình từ hơn 16MB xuống chỉ còn 4 – 6MB, đẩy tốc độ suy luận trên CPU đạt mức kỷ lục xấp xỉ 30 mili-giây mỗi khung hình.")

    # BƯỚC 5
    add_subsec_title("Bước 5: Lập trình Phát triển 4 Phân hệ Cốt lõi")
    add_p("Quá trình phát triển mã nguồn được triển khai đồng bộ qua 4 phân hệ chính:")
    add_bullet_item("Phân hệ Edge AI", "Lập trình đa luồng (Multi-threading) tách biệt giữa luồng đọc khung hình camera và luồng phân tích nhận diện. Xây dựng thuật toán Smart Capture tự động chọn khung hình có độ sắc nét và diện tích khuôn mặt lớn nhất để xử lý.")
    add_bullet_item("Phân hệ Backend API", "Hoàn thiện 19 bộ định tuyến (Routers) xử lý toàn bộ nghiệp vụ: Điểm danh, xin nghỉ phép, xử lý khiếu nại nề nếp 2 cấp, đánh giá thi đua và quản lý camera. Thiết lập bộ lọc bảo mật chặn tấn công từ chối dịch vụ (Rate Limiting).")
    add_bullet_item("Phân hệ Web Launchpad", "Thiết kế giao diện các khối thẻ chức năng (Launchpad Grid) với kích thước lớn, thân thiện với người lớn tuổi, tích hợp huy hiệu thông báo số liệu tức thời.")
    add_bullet_item("Phân hệ Mobile App", "Lập trình ứng dụng di động Flutter với giao diện cuộn thẻ dọc (Vertical Card Feed) và quy trình phụ huynh tra cứu thông tin con 1-chạm.")

    # BƯỚC 6
    add_subsec_title("Bước 6: Thử nghiệm Thực địa, Đánh giá Kết quả & Tối ưu hóa")
    add_p("Hệ thống đã trải qua quá trình thử nghiệm thực tế với hàng trăm lượt học sinh qua cổng trường trong các điều kiện môi trường khác nhau. Dưới đây là kết quả định lượng đạt được:")
    
    # Bảng số liệu thực nghiệm
    exp_table = doc.add_table(rows=5, cols=4)
    exp_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    exp_table.autofit = False
    
    col_w = [Cm(1.5), Cm(6.0), Cm(4.0), Cm(4.5)]
    headers_exp = ["STT", "Hạng mục đánh giá", "Kết quả thực nghiệm", "Ghi chú kỹ thuật"]
    
    for i, h_txt in enumerate(headers_exp):
        c = exp_table.rows[0].cells[i]
        c.width = col_w[i]
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(h_txt)
        format_run(r, bold=True, size=12)
        tcPr = c._element.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="D9E1F2"/>')
        tcPr.append(shd)
        
    exp_data = [
        ("1", "Độ chính xác nhận diện khuôn mặt", "96.6% (Ánh sáng chuẩn)\n88.9% (Ánh sáng yếu)", "Tolerance = 0.5; khoảng cách 1.5m - 4.0m"),
        ("2", "Độ chính xác phân loại đồng phục", "93% (Áo trắng HSV)\n87% (Áo dân tộc AI)", "Đánh giá theo chỉ số F1-Score"),
        ("3", "Thời gian xử lý toàn bộ Pipeline", "115ms (Nhánh HSV)\n145ms (Nhánh AI TFLite)", "Bảo đảm tốc độ khung hình 15 - 25 FPS"),
        ("4", "Tỷ lệ bảo toàn dữ liệu khi mất mạng", "100% (Không mất bản ghi)", "Nhờ cơ chế đệm SQLite Offline-First")
    ]
    
    for r_idx, r_val in enumerate(exp_data, start=1):
        for c_idx, val in enumerate(r_val):
            c = exp_table.rows[r_idx].cells[c_idx]
            c.width = col_w[c_idx]
            p = c.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.2
            if c_idx == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(val)
                format_run(r, size=11.5)
            elif c_idx == 1:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(val)
                format_run(r, bold=True, size=11.5)
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(val)
                format_run(r, size=11.5)
                
    tblPr = exp_table._element.xpath('w:tblPr')
    if tblPr:
        borders = parse_xml(f'''
            <w:tblBorders {nsdecls("w")}>
                <w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:left w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:right w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:insideH w:val="single" w:sz="4" w:space="0" w:color="D3D3D3"/>
                <w:insideV w:val="single" w:sz="4" w:space="0" w:color="D3D3D3"/>
            </w:tblBorders>
        ''')
        tblPr[0].append(borders)
        
    add_p("", indent=False, space_before=4, space_after=4)
    add_p("Các sáng kiến tối ưu kỹ thuật nảy sinh từ thực tế thử nghiệm:")
    add_bullet_item("Công cụ cân chỉnh màu sắc trực quan (HSV Calibrator)", "Khi ánh sáng tại vị trí lắp đặt thay đổi giữa các mùa, người quản lý không cần can thiệp vào mã nguồn mà chỉ cần mở giao diện GUI kéo thanh trượt để cập nhật lại ngưỡng màu trong 1 phút.")
    add_bullet_item("Cơ chế Fallback thông minh", "Khi học sinh bị che khuất thân người hoặc đứng quá gần camera, thuật toán tự động ước lượng vùng áo dựa trên tỷ lệ khuôn mặt thay vì báo lỗi.")
    add_bullet_item("Bỏ qua khung hình có chọn lọc", "Chỉ chạy thuật toán nhận diện khuôn mặt nặng mỗi 5 khung hình (FACE_SKIP_FRAMES = 5), các khung còn lại dùng thuật toán bám vết nhẹ, giúp tăng gấp đôi độ mượt của video.")

    # BƯỚC 7
    add_subsec_title("Bước 7: Đóng gói, Triển khai Thực tế & Kế hoạch Tương lai")
    add_p("1. Triển khai môi trường Production: Hệ thống đã được đóng gói và vận hành thử nghiệm trên máy chủ đám mây Linux VPS, định tuyến qua Nginx Reverse Proxy, kích hoạt chứng chỉ bảo mật mã hóa HTTPS SSL miễn phí tự động gia hạn (Let's Encrypt). Trạm Camera Raspberry Pi kết nối ổn định về Cloud qua tên miền thực tế.")
    add_p("2. Kế hoạch nâng cấp và hoàn thiện: Nhóm đã thẳng thắn nhận diện các hạn chế hiện tại (theo báo cáo kỹ thuật LIMITATIONS.md) và lập lộ trình phát triển giai đoạn tiếp theo: Chuyển đổi cơ sở dữ liệu sang PostgreSQL phân tán để phục vụ các trường trên 3.000 học sinh; tích hợp mô hình YOLOv8-Nano nhận diện chi tiết cổ áo, phù hiệu trường và khăn quàng đỏ; tích hợp tin nhắn Zalo ZNS và SMS Brandname để tiếp cận cả các phụ huynh không sử dụng smartphone.")
    add_speech_box("Đúc kết Tiến trình R&D", 
                   "Kính thưa Ban Giám khảo, trải qua 7 bước nghiên cứu và chế tạo nghiêm túc, sản phẩm của chúng em không chỉ dừng lại ở một ý tưởng mô phỏng trong phòng thí nghiệm mà đã trở thành một hệ sinh thái phần mềm - phần cứng hoàn chỉnh, có tính ứng dụng thực tiễn cao, sẵn sàng triển khai đại trà tại các trường học với mức chi phí đầu tư vô cùng hợp lý.")

    # =========================================================================
    # PHẦN II: LUỒNG VẬN HÀNH THỰC TẾ (9 BƯỚC RUNTIME)
    # =========================================================================
    add_sec_title("PHẦN II. KỊCH BẢN THUYẾT TRÌNH THEO TỪNG BƯỚC HOẠT ĐỘNG CỦA HỆ THỐNG (SYSTEM RUNTIME WORKFLOW)")
    add_p("Phần này trình bày chi tiết luồng dữ liệu khép kín diễn ra trong thực tế từ khoảnh khắc học sinh bước vào cổng trường cho đến khi phụ huynh và nhà trường nhận được thông báo, minh họa sinh động cho phần Trình diễn Thực tế (Live Demo):")

    # Bảng tóm tắt luồng 9 bước
    wf_table = doc.add_table(rows=10, cols=4)
    wf_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    wf_table.autofit = False
    
    col_wf = [Cm(1.4), Cm(3.8), Cm(6.5), Cm(4.3)]
    headers_wf = ["Bước", "Giai đoạn vận hành", "Hành động kỹ thuật của hệ thống", "Thời gian đáp ứng"]
    
    for i, h_txt in enumerate(headers_wf):
        c = wf_table.rows[0].cells[i]
        c.width = col_wf[i]
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(h_txt)
        format_run(r, bold=True, size=12)
        tcPr = c._element.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="E2EFDA"/>')
        tcPr.append(shd)
        
    wf_data = [
        ("1", "Đăng ký đầu vào (Onboarding)", "Học sinh tự chụp ảnh chân dung qua app -> GVCN duyệt -> Hệ thống sinh vector 128D nạp vào trạm camera", "Thực hiện 1 lần đầu năm học"),
        ("2", "Phát hiện & Bám vết (Detection)", "Camera quét luồng video, HOG phát hiện người, Multi-Object Tracker bám vết 2 - 3 học sinh cùng lúc", "Liên tục (15 - 25 FPS)"),
        ("3", "Chống giả mạo (Anti-Spoofing)", "Phân tích vi chuyển động da mặt, kết cấu phản quang và chớp mắt, ngăn chặn dùng ảnh in hoặc video điện thoại", "Dưới 30 ms"),
        ("4", "Nhận diện khuôn mặt (Recognition)", "Trích xuất vector 128 chiều, đối chiếu khoảng cách Euclidean <= 0.5 với CSDL nạp sẵn", "Khoảng 0.15 - 0.20 giây"),
        ("5", "Kiểm tra đồng phục (Uniform Check)", "Kiểm tra theo thứ: Thứ 2 chạy MobileNetV2; Thứ 3/5/6 phân tích màu HSV; Thứ 4/7 ghi nhận tự do", "8ms (HSV) hoặc 30ms (AI)"),
        ("6", "Ghi nhận cục bộ (Offline Buffer)", "Ghi tức thời bản ghi điểm danh và ảnh chụp bằng chứng vào bộ nhớ đệm SQLite trên trạm biên", "Dưới 5 ms (Tức thời)"),
        ("7", "Đồng bộ đám mây (Cloud Sync)", "server_bridge.py gửi dữ liệu an toàn qua HTTPS POST /attendance/sync kèm ảnh nén", "Phụ thuộc mạng (100 - 300ms)"),
        ("8", "Phát sóng Real-time & Báo đẩy", "FastAPI phát WebSockets cập nhật sĩ số Web Dashboard; gửi Push Notification đến máy Phụ huynh", "Dưới 1.0 giây"),
        ("9", "Hậu kiểm & Khiếu nại 2 cấp", "Phụ huynh nộp đơn nghỉ phép online; Học sinh gửi khiếu nại nề nếp kèm ảnh -> GVCN và Giám thị duyệt", "Tùy thời điểm tương tác")
    ]
    
    for r_idx, r_val in enumerate(wf_data, start=1):
        for c_idx, val in enumerate(r_val):
            c = wf_table.rows[r_idx].cells[c_idx]
            c.width = col_wf[c_idx]
            p = c.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.2
            if c_idx == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(val)
                format_run(r, size=11.5)
            elif c_idx == 1:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(val)
                format_run(r, bold=True, size=11.5)
            elif c_idx == 2:
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                r = p.add_run(val)
                format_run(r, size=11.5)
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(val)
                format_run(r, italic=True, size=11.5)
                
    tblPr_wf = wf_table._element.xpath('w:tblPr')
    if tblPr_wf:
        borders = parse_xml(f'''
            <w:tblBorders {nsdecls("w")}>
                <w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:left w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:right w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:insideH w:val="single" w:sz="4" w:space="0" w:color="D3D3D3"/>
                <w:insideV w:val="single" w:sz="4" w:space="0" w:color="D3D3D3"/>
            </w:tblBorders>
        ''')
        tblPr_wf[0].append(borders)
        
    add_p("", indent=False, space_before=4, space_after=4)

    # CHI TIẾT CÁC BƯỚC VẬN HÀNH
    add_subsec_title("Mô tả chi tiết 9 bước vận hành của hệ thống:")
    
    add_subsubsec_title("Bước 1: Chuẩn bị & Đăng ký sinh trắc học ban đầu (Onboarding)")
    add_p("Để hệ thống nhận diện được học sinh, vào đầu năm học, học sinh hoặc phụ huynh dùng điện thoại cá nhân tự chụp ảnh chân dung theo hướng dẫn chuẩn và gửi lên hệ thống. Giáo viên chủ nhiệm đăng nhập tài khoản Web để kiểm tra tính chính xác và bấm duyệt. Ngay sau đó, hệ thống tự động trích xuất vector đặc trưng khuôn mặt 128 chiều và đồng bộ xuống Trạm Camera tại cổng trường. Nhờ cơ chế này, nhà trường hoàn toàn không tốn nhân lực chụp ảnh thủ công cho từng em.")

    add_subsubsec_title("Bước 2: Bắt hình & Bám vết đối tượng tại cổng trường (Detection & Tracking)")
    add_p("Mỗi sáng khi học sinh đi bộ qua cổng trường, Camera góc rộng truyền luồng video về máy tính biên. Thuật toán HOG Person Detector kết hợp Haar Cascade quét khung hình liên tục. Bộ theo dõi đa đối tượng (Multi-Object Tracker) lập tức gắn nhãn và bám vết từng học sinh. Cơ chế này cho phép hệ thống phân tích song song 2 đến 3 học sinh cùng bước qua cổng, triệt tiêu hoàn toàn hiện tượng ùn tắc.")

    add_subsubsec_title("Bước 3: Xác thực người thật, chống gian lận (Anti-Spoofing)")
    add_p("Trước khi công nhận danh tính, module chống giả mạo lập tức kiểm tra vi chuyển động tự nhiên của các điểm mốc trên mặt, độ phản quang của da mặt và tần số chớp mắt. Nếu học sinh cầm ảnh in giấy hoặc mở video trên điện thoại để điểm danh hộ bạn, hệ thống sẽ nhận diện là hành vi giả mạo, lập tức từ chối và chụp ảnh cảnh báo gửi về giám thị.")

    add_subsubsec_title("Bước 4: Nhận diện danh tính khuôn mặt siêu tốc (Face Recognition)")
    add_p("Khi học sinh bước vào khoảng cách nét nhất (1.5m - 2.5m), thuật toán Smart Capture trích xuất vector 128 chiều và so sánh khoảng cách Euclidean với tập dữ liệu học sinh của trường. Với ngưỡng dung sai 0.5, hệ thống xác định chính xác họ tên, mã học sinh và lớp học trong vòng chưa đầy 0.2 giây.")

    add_subsubsec_title("Bước 5: Phân tích & Kiểm tra đồng phục theo thời khóa biểu (Uniform Check)")
    add_p("Hệ thống tự động tra cứu lịch quy định trang phục trong tuần của nhà trường:")
    add_bullet_item("Thứ Hai", "Kích hoạt mô hình học sâu TFLite MobileNetV2 nhận diện trang phục truyền thống/dân tộc (ngưỡng tin cậy >= 0.55).")
    add_bullet_item("Thứ Ba, Năm, Sáu", "Cắt vùng ngực áo và chuyển sang không gian màu HSV để nhận diện áo sơ mi trắng hoặc áo Đoàn thanh niên chỉ trong 8 mili-giây.")
    add_bullet_item("Thứ Tư, Bảy", "Ghi nhận trang phục tự do theo nội quy.")
    add_p("Kết quả kiểm tra được tự động phân loại thành: HỢP LỆ (OK), VI PHẠM (FAIL) hoặc CHƯA RÕ (UNCLEAR).")

    add_subsubsec_title("Bước 6: Ghi nhận Offline & Bảo toàn dữ liệu (Edge Logging & Buffer)")
    add_p("Ngay khi có kết quả, trạm camera lập tức ghi bản ghi điểm danh (Họ tên, thời gian, trạng thái đúng giờ/đi trễ, kết quả đồng phục và ảnh chụp bằng chứng) vào cơ sở dữ liệu SQLite cục bộ. Điều này bảo đảm nếu trường học bị mất mạng Internet hoặc chập chờn WiFi, cổng trường vẫn vận hành bình thường 100%, tuyệt đối không làm mất dữ liệu của học sinh.")

    add_subsubsec_title("Bước 7: Truyền tải dữ liệu lên Cloud Backend (Cloud Sync)")
    add_p("Tiến trình ngầm server_bridge.py liên tục kiểm tra kết nối Internet. Khi mạng thông suốt, trạm camera tự động đóng gói các bản ghi mới và gửi qua giao thức bảo mật HTTPS REST API lên máy chủ trung tâm. Dữ liệu được lưu trữ an toàn trong cơ sở dữ liệu nền tảng.")

    add_subsubsec_title("Bước 8: Phát sóng Real-time & Báo đẩy đến Phụ huynh")
    add_p("Máy chủ trung tâm lập tức kích hoạt 2 kênh truyền thông tức thời:")
    add_bullet_item("Kênh WebSocket Nhà trường", "Phát sóng dữ liệu trong vòng dưới 1 giây tới màn hình của Giáo viên chủ nhiệm và Giám thị. Biểu đồ sĩ số lớp và danh sách vắng mặt tự động nhảy số theo thời gian thực mà không cần tải lại trang.")
    add_bullet_item("Kênh Mobile Push Notification", "Gửi thông báo đẩy về ứng dụng di động của Phụ huynh kèm ảnh chụp thực tế: 'Học sinh Nguyễn Văn A đã vào trường lúc 06:42 - Đồng phục: Hợp lệ'. Phụ huynh hoàn toàn an tâm khi biết con đã đến trường an toàn.")

    add_subsubsec_title("Bước 9: Chu trình nghiệp vụ sau điểm danh & Xử lý khiếu nại 2 cấp")
    add_p("Hệ thống số hóa toàn diện quy trình sau điểm danh:")
    add_bullet_item("Nghỉ phép có lý do", "Phụ huynh gửi đơn xin nghỉ trực tuyến trên app; GVCN xem lý do và bấm duyệt, hệ thống tự động đổi trạng thái thành 'Nghỉ có phép' và lớp không bị trừ điểm thi đua.")
    add_bullet_item("Khiếu nại nề nếp 2 cấp", "Nếu học sinh bị ghi nhận vi phạm nhầm (do mặc áo khoác mùa đông che áo đồng phục), học sinh gửi khiếu nại trên app. GVCN xem ảnh chụp gốc lúc vào cổng và bấm chấp thuận Cấp 1 để tự động hoàn điểm thi đua. Những vụ việc tranh chấp phức tạp được chuyển lên Giám thị trưởng duyệt Cấp 2.")

    add_speech_box("Lời thoại Demo Vận hành Trực tiếp", 
                   "Kính mời Ban Giám khảo cùng quan sát màn hình Live Demo. Em xin phép bước qua trước ống kính camera... Ngay lập tức, trên màn hình trạm biên, hệ thống đã nhận diện ra em là học sinh Nguyễn Văn A - Lớp 10A1, trang phục áo sơ mi trắng Hợp lệ. Đồng thời, quý Thầy Cô có thể quan sát trên chiếc điện thoại của phụ huynh đặt tại đây: Một thông báo đẩy vừa xuất hiện tức thời, kèm theo bức ảnh chụp em vừa bước qua cổng trường. Toàn bộ chu trình từ nhận diện, phân tích đồng phục, đồng bộ máy chủ và báo về điện thoại diễn ra chỉ trong vòng chưa đầy 1 giây!")

    # =========================================================================
    # PHẦN III: BỘ CẨM NANG THUYẾT TRÌNH & ĐỐI ĐÁP PHẢN BIỆN
    # =========================================================================
    add_sec_title("PHẦN III. BỘ CẨM NANG THUYẾT TRÌNH & HƯỚNG DẪN ĐỐI ĐÁP PHẢN BIỆN XUẤT SẮC TRƯỚC BAN GIÁM KHẢO")
    
    add_subsec_title("1. Bảng phân bổ thời lượng thuyết trình chuẩn (Kịch bản 8 – 10 phút)")
    add_p("Để bài thuyết trình mạch lạc, tránh cháy giáo án và gây ấn tượng mạnh với Ban Giám khảo, nhóm nên phân chia thời gian theo tỷ lệ vàng sau:")
    add_bullet_item("Slide 1 - 2 (1.0 phút)", "Đặt vấn đề: Nỗi đau điểm danh thủ công và khoảng trống công nghệ hiện nay.")
    add_bullet_item("Slide 3 - 4 (1.5 phút)", "Giải pháp liên môn STEM: Ý tưởng kiến trúc Hybrid AI và tính toán tối ưu tài nguyên.")
    add_bullet_item("Slide 5 - 6 (2.0 phút)", "Kiến trúc hệ thống 4 module và cơ chế bảo toàn dữ liệu Offline-First.")
    add_bullet_item("Slide 7 (3.0 phút)", "Trình diễn trực tiếp (Live Demo) hoặc chiếu video minh họa luồng hoạt động thực tế 9 bước.")
    add_bullet_item("Slide 8 (1.5 phút)", "Bảng số liệu thực nghiệm định lượng, chi phí giá thành và tính tuân thủ pháp lý.")
    add_bullet_item("Slide 9 (1.0 phút)", "Đánh giá hạn chế, kế hoạch phát triển tương lai và lời cảm ơn kết thúc.")

    add_subsec_title("2. Top 5 từ khóa 'ghi điểm tuyệt đối' cần nhắc lại nhiều lần")
    add_bullet_item("1. Trí tuệ Nhân tạo Lai (Hybrid AI)", "Khẳng định sự sáng tạo trong việc kết hợp linh hoạt giữa Deep Learning MobileNetV2 và giải thuật màu HSV, tiết kiệm 70% tài nguyên CPU.")
    add_bullet_item("2. Ngoại tuyến ưu tiên (Offline-First)", "Khẳng định độ tin cậy công nghiệp, bảo toàn 100% dữ liệu ngay cả khi mất mạng.")
    add_bullet_item("3. Đa trường học (Multi-Tenant SaaS)", "Khẳng định khả năng mở rộng thương mại hóa, một máy chủ quản lý nhiều trường biệt lập.")
    add_bullet_item("4. Quy trình Khiếu nại 2 cấp (Two-tier Dispute Resolution)", "Chứng minh phần mềm thấu hiểu thực tế quản lý nề nếp học đường, minh bạch và nhân văn.")
    add_bullet_item("5. Tuân thủ Nghị định 13/2023/NĐ-CP", "Thể hiện trách nhiệm pháp lý và đạo đức công nghệ trong việc bảo vệ dữ liệu sinh trắc học học sinh.")

    add_subsec_title("3. Bộ 6 câu hỏi phản biện hóc búa nhất và kịch bản trả lời mẫu")

    # Q1
    add_subsubsec_title("Câu hỏi 1: 'Vào đầu giờ sáng, hàng trăm học sinh cùng ùa vào cổng thì camera có bị quá tải hoặc bỏ sót không?'")
    add_p("Trả lời mẫu: Dạ kính thưa Ban Giám khảo, đây chính là bài toán thực tế mà nhóm chúng em đã chú trọng giải quyết ngay từ khi thiết kế kiến trúc. Thứ nhất, hệ thống ứng dụng giải thuật bám vết đa đối tượng (Multi-object Tracking) kết hợp phát hiện đa khuôn mặt, cho phép nhận diện song song 2 đến 3 học sinh cùng lúc trong khoảng 0.2 đến 0.5 giây khi học sinh bước qua cổng với tốc độ đi bộ tự nhiên. Thứ hai, đối với các trường học có quy mô lớn, giải pháp của nhóm là phân làn đi bộ tại cổng trường (mỗi làn rộng 1.2m - 1.5m ứng với 1 camera độc lập). Nhờ áp dụng kiến trúc tính toán tại biên (Edge Computing), mỗi máy trạm tự xử lý hình ảnh tại chỗ nên khi mở rộng số làn camera thì máy chủ trung tâm hoàn toàn không bị quá tải.", italic=True)

    # Q2
    add_subsubsec_title("Câu hỏi 2: 'Nếu trời mưa âm u hoặc ánh sáng cổng trường thay đổi thì thuật toán màu HSV có bị nhận diện sai đồng phục không?'")
    add_p("Trả lời mẫu: Dạ kính thưa Thầy Cô, không gian màu HSV vốn dĩ đã tách biệt thành phần độ sáng (Value) khỏi tông màu thuần (Hue) nên độ bền vững trước thay đổi ánh sáng vượt trội hơn hẳn hệ màu RGB. Đặc biệt, nhóm đã tự xây dựng công cụ hiệu chỉnh trực quan step1_hsv_calibrator.py. Khi thời tiết chuyển mùa hoặc thay đổi vị trí đèn cổng trường, người quản lý chỉ mất 1 phút kéo thanh trượt để cập nhật lại dải màu tối ưu. Ngoài ra, với những khung hình quá tối hoặc ngược sáng gắt, hệ thống tự động gán nhãn CHƯA RÕ (UNCLEAR) và lưu ảnh để giáo viên xác nhận thủ công, tuyệt đối không tự ý phạt vi phạm học sinh khi độ tin cậy chưa đạt.", italic=True)

    # Q3
    add_subsubsec_title("Câu hỏi 3: 'Việc thu thập dữ liệu khuôn mặt học sinh có vi phạm quyền riêng tư và tiềm ẩn rủi ro lộ lọt thông tin không?'")
    add_p("Trả lời mẫu: Dạ kính thưa Ban Giám khảo, đề tài tuân thủ nghiêm ngặt Nghị định số 13/2023/NĐ-CP của Chính phủ về Bảo vệ dữ liệu cá nhân theo 3 nguyên tắc: (1) Nguyên tắc đồng thuận: Chỉ thu thập ảnh khi phụ huynh đã ký xác nhận trực tuyến trên ứng dụng; (2) Nguyên tắc tối thiểu hóa dữ liệu: Tại các máy trạm cổng trường, hệ thống không lưu trữ ảnh khuôn mặt gốc mà chỉ lưu vector đặc trưng toán học 128 chiều. Đây là phép biến đổi một chiều, kẻ xấu dù có đánh cắp được vector cũng không thể dựng ngược lại thành ảnh chân dung; (3) Toàn bộ mật khẩu và mã khóa được băm mã hóa chuẩn PBKDF2/JWT, đồng thời hệ thống cung cấp đầy đủ chức năng xóa vĩnh viễn dữ liệu khi học sinh chuyển trường hoặc phụ huynh rút lại đồng thuận.", italic=True)

    # Q4
    add_subsubsec_title("Câu hỏi 4: 'Chi phí triển khai thực tế cho một trường học là bao nhiêu so với các giải pháp thương mại?'")
    add_p("Trả lời mẫu: Dạ kính thưa Thầy Cô, một hệ thống camera AI thương mại trên thị trường hiện nay có giá từ 15 đến 40 triệu đồng cho một điểm quét, chưa kể phí bản quyền phần mềm hàng năm. Trong khi đó, giải pháp của nhóm tận dụng phần cứng nhúng phổ thông: Một vi máy tính Raspberry Pi 4 hoặc Mini PC đã qua sử dụng kết hợp Webcam Full HD có tổng chi phí chỉ từ 2.0 đến 2.8 triệu đồng/trạm. Phần mềm máy chủ được xây dựng trên nền tảng mã nguồn mở, không tốn phí bản quyền định kỳ, giúp nhà trường tiết kiệm từ 70% đến 80% ngân sách đầu tư.", italic=True)

    # Q5
    add_subsubsec_title("Câu hỏi 5: 'Tại sao nhóm không dùng luôn mô hình AI tiên tiến như YOLOv8 để nhận diện cả người và đồng phục mà lại chia thành HSV và TFLite?'")
    add_p("Trả lời mẫu: Dạ đây là một câu hỏi rất sâu về kỹ thuật ạ. Mặc dù các mô hình như YOLOv8 có độ chính xác nhận diện vật thể rất cao, nhưng chi phí tính toán phần cứng của chúng vượt quá khả năng xử lý của các thiết bị nhúng giá rẻ nếu không có card đồ họa GPU chuyên dụng đắt tiền (sẽ làm giá thành đội lên hàng chục triệu đồng). Quyết định kỹ thuật của nhóm là một sự đánh đổi có chủ đích (Engineering Trade-off): Bằng cách phối hợp giữa HSV cho các trang phục đơn sắc và TFLite INT8 cho trang phục họa tiết phức tạp, nhóm vẫn giải quyết trọn vẹn bài toán nề nếp học đường mà tốc độ pipeline luôn đạt mức thời gian thực (real-time) trên phần cứng bình dân.", italic=True)

    # Q6
    add_subsubsec_title("Câu hỏi 6: 'Hệ thống hiện tại còn những điểm hạn chế nào và nhóm dự định khắc phục ra sao?'")
    add_p("Trả lời mẫu: (Thẳng thắn thừa nhận hạn chế thể hiện tính liêm chính khoa học): Dạ kính thưa Ban Giám khảo, nhóm thẳng thắn ghi nhận 2 hạn chế kỹ thuật hiện tại: Thứ nhất, hệ thống đang phải bỏ qua quy định áo có cổ ngày Thứ Tư vì phân tích màu HSV không nhận diện được hình học cổ áo; thứ hai, cơ sở dữ liệu SQLite hiện tại có nguy cơ nghẽn ghi dữ liệu khi quy mô trường vượt quá 3.000 học sinh. Hướng khắc phục trong giai đoạn 2 của nhóm là chuyển đổi toàn diện sang cơ sở dữ liệu phân tán PostgreSQL và huấn luyện mô hình mạng nơ-ron chuyên biệt YOLOv8-Nano kích thước siêu nhỏ để nhận diện chi tiết cổ áo, phù hiệu thêu và khăn quàng đỏ.", italic=True)


    # =========================================================================
    # PHẦN IV: CÁC BƯỚC THỰC HIỆN THỰC TẾ TRONG ĐỜI SỐNG HỌC ĐƯỜNG (A - Z)
    # =========================================================================
    add_sec_title("PHẦN IV. QUY TRÌNH 12 BƯỚC THỰC HIỆN THỰC TẾ HỆ THỐNG TRONG ĐỜI SỐNG HỌC ĐƯỜNG (TỪ KHỞI TẠO ĐẾN VẬN HÀNH)")
    add_p("Để minh họa trực quan và thuyết phục Hội đồng Giám khảo về tính khả thi của dự án, phần này mô tả chi tiết toàn bộ chu trình 12 bước thực hiện thực tế ngoài đời sống trường học, từ khâu khởi tạo tài khoản ban đầu cho đến công tác quản trị, điểm danh mỗi sáng và tổng kết thi đua cuối tuần:")

    # Bảng tổng hợp 12 bước thực hiện
    step_table = doc.add_table(rows=13, cols=5)
    step_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    step_table.autofit = False
    
    col_st = [Cm(1.2), Cm(3.2), Cm(3.0), Cm(3.8), Cm(4.8)]
    headers_st = ["Bước", "Tên bước thực hiện", "Người thực hiện", "Giao diện / Thiết bị", "Kết quả đầu ra thực tế"]
    
    for i, h_txt in enumerate(headers_st):
        c = step_table.rows[0].cells[i]
        c.width = col_st[i]
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(h_txt)
        format_run(r, bold=True, size=11.5)
        tcPr = c._element.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="FFF2CC"/>')
        tcPr.append(shd)
        
    step_data = [
        ("1", "Khởi tạo Trường & Admin", "Hiệu trưởng / Admin", "Web Trang chủ (Landing Page)", "Tạo Server trường riêng & cấp Tenant ID"),
        ("2", "Cài đặt Nội quy & Giờ giấc", "Hiệu trưởng", "Web Dashboard BGH", "Thiết lập mốc giờ trễ & lịch áo theo thứ"),
        ("3", "Tạo Lớp & Cấp Mã GVCN", "Hiệu trưởng / Ban KT", "Web Dashboard BGH", "Danh sách lớp & mã mời GV_NGUYEN_HUE"),
        ("4", "Đăng ký HS & Phụ huynh", "Học sinh & Phụ huynh", "Mobile App / Web", "Tài khoản HS, mã HS1001 & liên kết PH"),
        ("5", "Nộp & Duyệt Khuôn mặt", "HS nộp -> GVCN duyệt", "App Mobile -> Web GVCN", "Vector 128D nạp vào CSDL trạm camera"),
        ("6", "Cấu hình Trạm Camera AI", "Kỹ thuật / Giám thị", "Web BGH -> Raspberry Pi", "Kết nối trạm qua Secret Key & cân màu HSV"),
        ("7", "Mở Điểm danh Buổi Sáng", "Giám thị / Tự động", "Bốt gác cổng trường", "Camera live WebRTC kèm khung xanh/đỏ"),
        ("8", "Học sinh Qua Cổng", "Học sinh & Camera AI", "Cổng trường (Khoảng cách 2m)", "Quét 0.2s: Nhận diện, chống gian lận, soi áo"),
        ("9", "Nhận Báo Cáo Tức Thì", "GVCN & Phụ huynh", "Web Lớp học & App Mobile", "Sĩ số lớp nhảy số; App phụ huynh hiện ảnh con"),
        ("10", "Nộp Đơn Nghỉ Phép Online", "Phụ huynh -> GVCN", "Mobile App -> Web GVCN", "Duyệt nghỉ có phép, không bị trừ điểm"),
        ("11", "Xử lý Khiếu nại 2 Cấp", "HS -> GVCN -> Giám thị", "Mobile App & Web Dashboard", "Đối soát ảnh gốc camera, hoàn +5đ thi đua"),
        ("12", "Tổng kết Thi đua Tuần", "Giám thị -> Hiệu trưởng", "Web Dashboard toàn trường", "Ký duyệt điện tử bảng xếp hạng, xuất Excel/PDF")
    ]
    
    for r_idx, r_val in enumerate(step_data, start=1):
        for c_idx, val in enumerate(r_val):
            c = step_table.rows[r_idx].cells[c_idx]
            c.width = col_st[c_idx]
            p = c.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.2
            if c_idx == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(val)
                format_run(r, size=11)
            elif c_idx == 1:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(val)
                format_run(r, bold=True, size=11)
            elif c_idx == 2:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(val)
                format_run(r, size=11)
            elif c_idx == 3:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(val)
                format_run(r, italic=True, size=11)
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                r = p.add_run(val)
                format_run(r, size=11)
                
    tblPr_st = step_table._element.xpath('w:tblPr')
    if tblPr_st:
        borders = parse_xml(f'''
            <w:tblBorders {nsdecls("w")}>
                <w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:left w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:right w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:insideH w:val="single" w:sz="4" w:space="0" w:color="D3D3D3"/>
                <w:insideV w:val="single" w:sz="4" w:space="0" w:color="D3D3D3"/>
            </w:tblBorders>
        ''')
        tblPr_st[0].append(borders)
        
    add_p("", indent=False, space_before=4, space_after=4)

    # 3 GIAI ĐOẠN CHI TIẾT
    add_subsec_title("GIAI ĐOẠN I: THIẾT LẬP & KHỞI TẠO NỀN TẢNG (SETUP & ONBOARDING)")

    add_subsubsec_title("Bước 1: Khởi tạo Trường học & Đăng ký Tài khoản Quản trị (Hiệu trưởng)")
    add_bullet_item("Người thực hiện", "Hiệu trưởng hoặc Cán bộ Công nghệ thông tin nhà trường.")
    add_bullet_item("Thao tác thực tế", "Truy cập cổng thông tin hệ thống tại địa chỉ website nhà trường -> Bấm nút 'Khám phá Trường học' -> Chọn 'Tạo Không gian Trường Mới' -> Điền tên trường (ví dụ: Trường THPT Nguyễn Huệ), địa phương, cấp học -> Điền thông tin tài khoản Quản trị viên (Tên đăng nhập: hieutruong, Mật khẩu, Số điện thoại).")
    add_bullet_item("Kết quả đầu ra", "Hệ thống tự động cấp mã định danh trường học (School ID: 1), khởi tạo không gian cơ sở dữ liệu phân vùng độc lập (Tenant) và đưa người dùng vào Bảng điều khiển Quản trị toàn trường.")

    add_subsubsec_title("Bước 2: Cài đặt Nội quy Trường học & Lịch Đồng phục theo Tuần")
    add_bullet_item("Người thực hiện", "Hiệu trưởng / Ban Giám hiệu.")
    add_bullet_item("Thao tác thực tế", "Trên Dashboard, vào mục 'Cài đặt Quy chế & Thời khóa biểu': (1) Cài đặt mốc thời gian: Giờ vào trường chuẩn (06:45), Giờ tính đi trễ (07:00), Giờ đóng cổng (07:15); (2) Cài đặt lịch đồng phục trong tuần: Thứ Hai chọn 'Trang phục truyền thống/dân tộc', Thứ Ba/Năm/Sáu chọn 'Áo sơ mi trắng có cổ', Thứ Sáu chọn 'Áo Đoàn thanh niên', Thứ Tư chọn 'Tự do có cổ'; (3) Cài đặt biểu điểm thi đua: Đi trễ trừ 2 điểm, Sai đồng phục trừ 3 điểm, Không đeo thẻ trừ 1 điểm.")
    add_bullet_item("Kết quả đầu ra", "Bảng quy chế điện tử được lưu vào hệ thống, tự động làm thước đo chuẩn để các trạm camera AI căn cứ đánh giá mỗi buổi sáng.")

    add_subsubsec_title("Bước 3: Tạo Danh sách Lớp học & Cấp phát Mã mời Giáo viên Chủ nhiệm")
    add_bullet_item("Người thực hiện", "Hiệu trưởng / Cán bộ Quản trị.")
    add_bullet_item("Thao tác thực tế", "Vào mục 'Quản lý Lớp học' -> Bấm '+ Thêm lớp mới' để tạo danh sách các lớp (10A1, 10A2...). Tiếp tục vào mục 'Mã Mời Nhân sự' -> Sinh chuỗi mã mời bảo mật dành riêng cho giáo viên (ví dụ: GV_NGUYEN_HUE_2026). Giáo viên truy cập web, bấm 'Đăng ký', chọn vai trò 'Giáo viên' và dán mã mời này vào -> Hiệu trưởng bấm 'Chấp thuận' và phân công làm GVCN lớp tương ứng.")
    add_bullet_item("Kết quả đầu ra", "Giáo viên được phân quyền đúng chức năng quản lý lớp mình, không thể can thiệp vào dữ liệu lớp khác.")

    add_subsubsec_title("Bước 4: Đăng ký Tài khoản Học sinh & Phụ huynh (Liên kết Tài khoản)")
    add_bullet_item("Người thực hiện", "Học sinh và Phụ huynh học sinh.")
    add_bullet_item("Thao tác thực tế", "Học sinh tải ứng dụng di động hoặc mở trình duyệt web -> Bấm 'Đăng ký' -> Chọn vai trò 'Học sinh' -> Nhập Họ tên, chọn Lớp 10A1, nhập SĐT -> Hệ thống tự động cấp mã học sinh (ví dụ: HS1001). Phụ huynh tải ứng dụng -> Chọn vai trò 'Phụ huynh' -> Nhập Số điện thoại và nhập Mã học sinh của con để tạo liên kết bảo mật -> Ký xác nhận điện tử bản thỏa thuận đồng thuận thu thập dữ liệu sinh trắc học theo Nghị định số 13/2023/NĐ-CP.")
    add_bullet_item("Kết quả đầu ra", "Thiết lập thành công luồng liên kết thông tin 1-1 an toàn giữa hồ sơ học sinh và điện thoại phụ huynh.")

    add_subsubsec_title("Bước 5: Nộp Ảnh Chân dung Mẫu & GVCN Duyệt Sinh trắc học FaceID")
    add_bullet_item("Người thực hiện", "Học sinh nộp mẫu -> Giáo viên chủ nhiệm kiểm duyệt.")
    add_bullet_item("Thao tác thực tế", "Học sinh sử dụng camera điện thoại tự chụp 1 bức ảnh chân dung rõ nét (chính diện, đủ sáng, không đeo kính râm hay khẩu trang) và bấm 'Gửi phê duyệt FaceID'. Trên máy tính của GVCN, giao diện 'Kiểm duyệt Khuôn mặt Lớp' lập tức hiển thị ảnh kèm tên học sinh -> GVCN kiểm tra đúng học sinh của lớp mình và bấm nút 'Chấp thuận' màu xanh.")
    add_bullet_item("Kết quả đầu ra", "Hệ thống tự động trích xuất vector đặc trưng 128 chiều từ ảnh và nạp vào cơ sở dữ liệu nhận diện tại các trạm camera cổng trường. Nhà trường hoàn toàn không phải mất công tổ chức chụp ảnh thủ công cho từng em.")

    add_subsubsec_title("Bước 6: Cấu hình & Kích hoạt Trạm Camera AI tại Cổng trường")
    add_bullet_item("Người thực hiện", "Cán bộ Kỹ thuật / Giám thị.")
    add_bullet_item("Thao tác thực tế", "Hiệu trưởng vào Web -> 'Trạm Camera' -> Bấm '+ Thêm Trạm' (đặt tên: 'Trạm Cổng Chính 1') -> Nhận mã khóa bí mật Secret Key. Tại cổng trường, cắm Webcam Full HD vào máy tính mini hoặc Raspberry Pi -> Mở terminal chạy lệnh kết nối: python main.py --school_id 1 --secret_key <SECRET_KEY> --api_url https://tenmien.vn. Cán bộ kỹ thuật mở công cụ hsv_picker.html kéo thanh trượt cân chỉnh màu áo trắng trong 1 phút phù hợp với ánh sáng thực tế cổng trường.")
    add_bullet_item("Kết quả đầu ra", "Trạm camera chuyển sang trạng thái đèn xanh ONLINE, sẵn sàng đón học sinh vào sáng hôm sau.")

    add_subsec_title("GIAI ĐOẠN II: VẬN HÀNH ĐIỂM DANH & GIÁM SÁT NỀ NẾP THƯỜNG NHẬT (DAILY OPERATIONS)")

    add_subsubsec_title("Bước 7: Khởi động Trạm Camera Cổng trường Buổi Sáng")
    add_bullet_item("Người thực hiện", "Cán bộ Giám thị hoặc hệ thống tự khởi động theo lịch hẹn giờ.")
    add_bullet_item("Thao tác thực tế", "Đúng 06:15 sáng, hệ thống camera tự động kích hoạt luồng thu hình ảnh. Màn hình bốt trực hiển thị video trực tiếp với các phím tắt nhanh (nhấn 'S' xem sĩ số tức thì, nhấn 'U' tạm tắt soi đồng phục trong ngày lễ hội, nhấn 'T' hiển thị khung bám vết nhiều người).")
    add_bullet_item("Kết quả đầu ra", "Cổng trường được số hóa hoàn toàn, giám thị không cần cầm sổ tay ghi chép.")

    add_subsubsec_title("Bước 8: Học sinh Qua Cổng & Tự động Phân tích Đa tầng")
    add_bullet_item("Người thực hiện", "Học sinh đi bộ qua cổng trường tự nhiên (Khoảng cách 1.5m - 3.5m).")
    add_bullet_item("Thao tác thực tế", "Học sinh không cần dừng lại quẹt thẻ hay áp mặt sát camera. Khi bước qua cổng: (1) Thuật toán Anti-spoofing kiểm tra vi chuyển động và phản quang da mặt để chặn gian lận ảnh/video; (2) Thuật toán nhận diện so khớp vector 128 chiều xác định chính xác danh tính em Nguyễn Văn A trong 0.2 giây; (3) Thuật toán màu HSV quét vùng thân áo xác nhận áo trắng Hợp lệ; (4) Màn hình phát âm thanh BEEP nhẹ kèm khung viền màu Xanh Lá Cây thân thiện.")
    add_bullet_item("Nếu có vi phạm", "Nếu học sinh đi trễ sau 07:00 hoặc mặc áo màu không đúng quy định, màn hình lập tức nhấp nháy khung Đỏ kèm thông báo vi phạm, tự động kích hoạt tính năng Smart Best-shot chụp 2 bức ảnh bằng chứng (1 ảnh cận mặt + 1 ảnh toàn cảnh có khung đỏ) lưu vào hệ thống.")

    add_subsubsec_title("Bước 9: Tiếp nhận Dữ liệu Realtime (Web Giáo viên & Mobile Phụ huynh)")
    add_bullet_item("Người thực hiện", "Giáo viên chủ nhiệm trên lớp & Phụ huynh ở nhà/nơi làm việc.")
    add_bullet_item("Thao tác thực tế", "Tại lớp học, GVCN mở Web Dashboard: Biểu đồ sĩ số lớp tự động nhảy số theo thời gian thực (ví dụ: 39/40 em đã có mặt, 1 em chưa đến) mà không cần nhấn F5 tải lại trang. Cùng lúc đó, trên điện thoại của phụ huynh rung chuông thông báo đẩy: 'Con Nguyễn Văn A đã vào cổng trường lúc 06:48 - Trang phục: Hợp lệ' kèm theo ảnh chụp của con lúc bước qua cổng trường.")
    add_bullet_item("Kết quả đầu ra", "Phụ huynh hoàn toàn an tâm khi biết con đã đến trường bình an; GVCN không tốn một giây nào để gọi tên điểm danh đầu giờ.")

    add_subsec_title("GIAI ĐOẠN III: XỬ LÝ NGHIỆP VỤ PHÁT SINH, KHIẾU NẠI & THI ĐUA (POST-ATTENDANCE)")

    add_subsubsec_title("Bước 10: Nộp & Phê duyệt Đơn xin Nghỉ phép Trực tuyến")
    add_bullet_item("Người thực hiện", "Phụ huynh gửi đơn -> GVCN phê duyệt.")
    add_bullet_item("Thao tác thực tế", "Nếu học sinh bị ốm, phụ huynh mở ứng dụng di động -> Bấm 'Nộp đơn xin nghỉ phép' -> Chọn ngày nghỉ, đính kèm ảnh đơn viết tay hoặc giấy khám bệnh -> Bấm Gửi. GVCN nhận thông báo trên điện thoại hoặc web, xem lý do và bấm nút 'Chấp thuận'.")
    add_bullet_item("Kết quả đầu ra", "Hệ thống tự động cập nhật trạng thái học sinh thành 'Nghỉ có phép' vào sổ điểm danh điện tử, lớp học không bị trừ điểm chuyên cần thi đua.")

    add_subsubsec_title("Bước 11: Quy trình Khiếu nại Nề nếp 2 Cấp (Minh bạch & Nhân văn)")
    add_bullet_item("Người thực hiện", "Học sinh gửi khiếu nại -> GVCN duyệt Cấp 1 -> Giám thị duyệt Cấp 2.")
    add_bullet_item("Thao tác thực tế", "Trong đợt rét mùa đông, học sinh mặc áo khoác ấm che mất áo sơ mi trắng bên trong và bị camera ghi nhận 'Sai đồng phục'. Học sinh mở ứng dụng bấm 'Khiếu nại' kèm lời giải trình: 'Em mặc áo khoác giữ ấm, bên trong vẫn mặc áo trắng'. GVCN mở Dashboard, xem ảnh gốc độ phân giải cao do camera lưu lại, xác nhận đúng hoàn cảnh rét đậm -> Bấm 'Chấp thuận Cấp 1'.")
    add_bullet_item("Kết quả đầu ra", "Hệ thống tự động xóa lỗi vi phạm, tự động hoàn trả +5 điểm thi đua cho lớp học. Các khiếu nại phức tạp sẽ được chuyển tiếp lên Giám thị trưởng duyệt Cấp 2.")

    add_subsubsec_title("Bước 12: Tổng kết Điểm rèn luyện, Thi đua & Xuất Báo cáo Định kỳ")
    add_bullet_item("Người thực hiện", "Giám thị chấm điểm -> Hiệu trưởng ký duyệt điện tử -> Văn phòng xuất file.")
    add_bullet_item("Thao tác thực tế", "Chiều thứ Sáu hàng tuần, hệ thống tự động tổng hợp toàn bộ dữ liệu điểm danh, đi trễ, vi phạm đồng phục và đơn nghỉ phép thành Bảng Xếp Hạng Thi Đua Nề Nếp toàn trường một cách tuyệt đối khách quan. Giám thị kiểm tra bảng tổng kết -> Trình Ban Giám hiệu -> Hiệu trưởng bấm 'Ký duyệt điện tử'. Văn phòng nhà trường bấm nút 'Xuất Excel / PDF' để gửi cho các khối lớp và thông báo trong lễ chào cờ đầu tuần.")
    add_bullet_item("Kết quả đầu ra", "Toàn bộ quy trình nề nếp học đường được số hóa khép kín 100%, tiết kiệm hàng trăm giờ lao động cho thầy cô và xây dựng môi trường học đường văn minh, kỷ cương, hiện đại.")

    add_speech_box("Lời thoại Chốt Quy trình Thực tế", 
                   "Kính thưa Ban Giám khảo, qua 12 bước vận hành thực tế nêu trên, quý Thầy Cô có thể thấy rõ ràng: Hệ thống Điểm danh STEM của chúng em không chỉ là một thuật toán máy tính đơn lẻ, mà là một quy trình chuyển đổi số khép kín, chạm đến từng chủ thể trong nhà trường: Từ Hiệu trưởng ra quyết định, Thầy cô chủ nhiệm giảm tải áp lực, Phụ huynh an tâm mỗi ngày, cho đến các bạn Học sinh được đối xử công bằng, minh bạch trong thi đua nề nếp.")

    # --- PHẦN KẾT VÀ CHỮ KÝ ---
    add_p("", indent=False, space_before=12, space_after=6)
    footer_table = doc.add_table(rows=1, cols=2)
    footer_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    footer_table.autofit = False

    c_l = footer_table.cell(0, 0)
    c_r = footer_table.cell(0, 1)
    c_l.width = Cm(8.0)
    c_r.width = Cm(8.0)

    p_fl = c_l.paragraphs[0]
    p_fl.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_fl.paragraph_format.line_spacing = 1.2
    p_fl.paragraph_format.space_after = Pt(2)
    r = p_fl.add_run("Nơi nhận tài liệu:\n")
    format_run(r, bold=True, italic=True, size=11.5)
    r = p_fl.add_run("- Ban Giám hiệu / Hội đồng Chấm thi;\n")
    format_run(r, size=11.5)
    r = p_fl.add_run("- Giáo viên hướng dẫn đề tài;\n")
    format_run(r, size=11.5)
    r = p_fl.add_run("- Thành viên Nhóm nghiên cứu;\n")
    format_run(r, size=11.5)
    r = p_fl.add_run("- Lưu: Hồ sơ Kỹ thuật Dự án STEM.")
    format_run(r, size=11.5)

    p_fr = c_r.paragraphs[0]
    p_fr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fr.paragraph_format.line_spacing = 1.2
    p_fr.paragraph_format.space_after = Pt(2)
    r = p_fr.add_run("ĐẠI DIỆN NHÓM NGHIÊN CỨU & PHÁT TRIỂN\n")
    format_run(r, bold=True, size=12.5)
    r = p_fr.add_run("(Ký, ghi rõ họ tên)\n\n\n\n\n")
    format_run(r, italic=True, size=12)
    r = p_fr.add_run("NHÓM TÁC GIẢ DỰ ÁN EDUSAMS STEM")
    format_run(r, bold=True, size=13)

    # 3. Lưu tài liệu ra các vị trí
    download_folder = os.path.expanduser('~/Bản tải về')
    if not os.path.exists(download_folder):
        os.makedirs(download_folder, exist_ok=True)

    phu_luc_folder = os.path.expanduser('~/PHU LUC STEM')
    if not os.path.exists(phu_luc_folder):
        os.makedirs(phu_luc_folder, exist_ok=True)
        
    out_path_download = os.path.join(download_folder, "KICH_BAN_THUYET_TRINH_DU_AN_DIEM_DANH_STEM.docx")
    out_path_phu_luc = os.path.join(phu_luc_folder, "KICH_BAN_THUYET_TRINH_DU_AN_DIEM_DANH_STEM.docx")
    out_path_repo = "/home/minhphuc/Diem-danh-STEM/docs/reports/KICH_BAN_THUYET_TRINH_DU_AN_DIEM_DANH_STEM.docx"

    doc.save(out_path_download)
    doc.save(out_path_phu_luc)
    doc.save(out_path_repo)
    print(f"Xuat file docx thanh cong:")
    print(f"1. {out_path_phu_luc}")
    print(f"2. {out_path_download}")
    print(f"3. {out_path_repo}")

if __name__ == "__main__":
    create_presentation_docx()
