import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os

def generate_practical_steps_docx():
    doc = Document()

    # 1. Cấu hình lề trang theo Nghị định 30/2020/NĐ-CP
    for s in doc.sections:
        s.top_margin = Cm(2.0)
        s.bottom_margin = Cm(2.0)
        s.left_margin = Cm(3.0)
        s.right_margin = Cm(2.0)
        s.page_width = Cm(21.0)
        s.page_height = Cm(29.7)

    # 2. Font Times New Roman 13pt, giãn dòng 1.3
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

    def add_highlight_box(title, content_text):
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
        
        r_h = p.add_run(f"💡 {title}\n")
        format_run(r_h, bold=True, size=12, color=RGBColor(31, 78, 121))
        r_b = p.add_run(content_text)
        format_run(r_b, italic=False, size=12)
        
        p_space = doc.add_paragraph()
        p_space.paragraph_format.space_before = Pt(2)
        p_space.paragraph_format.space_after = Pt(4)

    # --- TIÊU NGỮ ĐẦU TRANG ---
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
    r = p_l.add_run("Tài liệu: Quy trình Vận hành Thực tế")
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
    r = p_r.add_run("Hà Nội, năm học 2025 - 2026")
    format_run(r, bold=False, italic=True, size=11.5)

    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(10)
    p_sp.paragraph_format.space_after = Pt(4)

    # Tiêu đề chính
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(4)
    p_title.paragraph_format.space_after = Pt(4)
    r_title = p_title.add_run("CẨM NANG HƯỚNG DẪN QUY TRÌNH 12 BƯỚC THỰC HIỆN THỰC TẾ\nHỆ THỐNG ĐIỂM DANH & QUẢN LÝ NỀ NẾP HỌC ĐƯỜNG THÔNG MINH STEM")
    format_run(r_title, bold=True, size=15, color=RGBColor(0, 32, 96))

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(14)
    r_sub = p_sub.add_run("(Tài liệu chuẩn hóa dành cho Ban Giám Hiệu, Giáo Viên Chủ Nhiệm, Cán Bộ Giám Thị, Phụ Huynh & Học Sinh)")
    format_run(r_sub, italic=True, size=13)

    add_p("Tài liệu này hướng dẫn chi tiết từng bước thao tác thực tế ngoài đời sống học đường của Hệ thống Điểm danh Thông minh STEM (Edusams STEM). Quy trình được chuẩn hóa thành 12 bước khép kín, phân định rõ ràng giữa các chủ thể tham gia (Hiệu trưởng, Giám thị, GVCN, Phụ huynh, Học sinh) và chia thành 3 giai đoạn tự nhiên: Khởi tạo nền tảng, Vận hành thường nhật mỗi sáng, và Xử lý nghiệp vụ hậu kiểm / thi đua.", italic=True, size=12.5)

    # Bảng tổng hợp 12 bước
    add_sec_title("I. BẢNG TỔNG HỢP QUY TRÌNH 12 BƯỚC THỰC HIỆN THỰC TẾ")
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
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="D9E1F2"/>')
        tcPr.append(shd)
        
    step_data = [
        ("1", "Khởi tạo Trường & Admin", "Hiệu trưởng / Admin", "Web Trang chủ (Landing Page)", "Tạo Server trường riêng & cấp Tenant ID"),
        ("2", "Cài đặt Nội quy & Giờ giấc", "Hiệu trưởng", "Web Dashboard BGH", "Thiết lập mốc giờ trễ & lịch áo theo thứ"),
        ("3", "Tạo Lớp & Cấp Mã GVCN", "Hiệu trưởng / Quản trị", "Web Dashboard BGH", "Danh sách lớp & mã mời GV_NGUYEN_HUE"),
        ("4", "Đăng ký HS & Phụ huynh", "Học sinh & Phụ huynh", "Mobile App / Web", "Tài khoản HS, mã HS1001 & liên kết PH"),
        ("5", "Nộp & Duyệt Khuôn mặt", "HS nộp -> GVCN duyệt", "App Mobile -> Web GVCN", "Vector 128D nạp vào CSDL trạm camera"),
        ("6", "Cấu hình Trạm Camera AI", "Kỹ thuật / Giám thị", "Web BGH -> Raspberry Pi", "Kết nối trạm qua secret_key & cân màu HSV"),
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
        
    add_p("", indent=False, space_before=6, space_after=6)

    # II. GIAI ĐOẠN I
    add_sec_title("II. GIAI ĐOẠN I: THIẾT LẬP & KHỞI TẠO NỀN TẢNG (SETUP & ONBOARDING)")
    add_p("Giai đoạn này diễn ra vào đầu năm học mới hoặc khi nhà trường bắt đầu số hóa quy trình điểm danh:")

    add_subsec_title("Bước 1: Khởi tạo Trường học & Đăng ký Tài khoản Quản trị (Hiệu trưởng)")
    add_bullet_item("Chủ thể thực hiện", "Hiệu trưởng hoặc Cán bộ Quản trị Công nghệ thông tin nhà trường.")
    add_bullet_item("Giao diện thực hiện", "Trình duyệt Web trên máy tính (Trang chủ nền tảng).")
    add_bullet_item("Thao tác chi tiết", "1. Truy cập vào địa chỉ website trường (ví dụ: https://tenmien.vn hoặc http://localhost:5173).\n2. Trên thanh menu hoặc màn hình chính, bấm nút 'Khám Phá Trường Học' -> Chọn 'Tạo Không Gian Trường Mới'.\n3. Điền thông tin pháp lý của trường: Tên trường (Trường THPT Nguyễn Huệ), Địa phương (Hà Nội), Cấp học (Trung học phổ thông).\n4. Khởi tạo tài khoản Quản trị viên trường: Tên đăng nhập (hieutruong), Họ và tên (Nguyễn Văn Hiệu Trưởng), Mật khẩu và Số điện thoại liên hệ.")
    add_bullet_item("Kết quả đầu ra", "Hệ thống cấp mã định danh trường (school_id: 1), khởi tạo vùng cơ sở dữ liệu phân vùng độc lập (Multi-Tenant SaaS) và đưa Hiệu trưởng vào Bảng điều khiển quản trị toàn trường.")

    add_subsec_title("Bước 2: Cài đặt Nội quy Trường học & Lịch Đồng phục theo Tuần")
    add_bullet_item("Chủ thể thực hiện", "Hiệu trưởng / Ban Giám hiệu.")
    add_bullet_item("Giao diện thực hiện", "Web Dashboard -> Tab 'Cấu hình Quy chế & Thời khóa biểu'.")
    add_bullet_item("Thao tác chi tiết", "1. Cài đặt các mốc thời gian: Giờ vào trường chuẩn (06:45), Giờ bắt đầu tính đi trễ (07:00), Giờ khóa sổ điểm danh buổi sáng (07:15).\n2. Cài đặt lịch đồng phục theo từng thứ trong tuần:\n- Thứ Hai: Chọn 'Trang phục truyền thống / Áo dài / Dân tộc'\n- Thứ Ba, Thứ Năm: Chọn 'Áo sơ mi trắng có cổ, quần sẫm màu'\n- Thứ Sáu: Chọn 'Áo Đoàn thanh niên'\n- Thứ Tư, Thứ Bảy: Chọn 'Trang phục tự do có cổ'\n3. Cài đặt biểu điểm thi đua: Đi trễ trừ 2 điểm, Sai đồng phục trừ 3 điểm, Không đeo thẻ học sinh trừ 1 điểm.")
    add_bullet_item("Kết quả đầu ra", "Bộ quy chế điện tử được lưu lên đám mây, tự động đóng vai trò là thước đo chuẩn để các trạm camera AI căn cứ đánh giá mỗi sáng.")

    add_subsec_title("Bước 3: Tạo Danh sách Lớp học & Cấp phát Mã mời Giáo viên (GVCN)")
    add_bullet_item("Chủ thể thực hiện", "Hiệu trưởng / Cán bộ Quản trị.")
    add_bullet_item("Giao diện thực hiện", "Web Dashboard -> Quản lý Lớp học & Nhân sự.")
    add_bullet_item("Thao tác chi tiết", "1. Vào mục 'Lớp học' -> Bấm '+ Thêm lớp' để tạo danh sách các lớp: 10A1, 10A2, 11A1, 12A1...\n2. Vào mục 'Mã mời nhân sự' -> Sinh chuỗi mã mời bảo mật dành riêng cho giáo viên (ví dụ: GV_NGUYEN_HUE_2026).\n3. Giáo viên truy cập web/app, bấm 'Đăng ký', chọn vai trò 'Giáo viên' và dán mã mời GV_NGUYEN_HUE_2026 vào form đăng ký.\n4. Hiệu trưởng thấy yêu cầu trên Dashboard -> Bấm nút 'Chấp thuận' và chọn gán thầy/cô phụ trách làm Giáo viên chủ nhiệm lớp 10A1.")
    add_bullet_item("Kết quả đầu ra", "Giáo viên đăng nhập thành công với quyền hạn quản lý riêng của lớp mình, bảo đảm nguyên tắc đặc quyền tối thiểu (Least Privilege).")

    add_subsec_title("Bước 4: Đăng ký Tài khoản Học sinh & Phụ huynh (Liên kết Tài khoản)")
    add_bullet_item("Chủ thể thực hiện", "Học sinh và Phụ huynh học sinh.")
    add_bullet_item("Giao diện thực hiện", "Ứng dụng di động Flutter hoặc Trình duyệt Web trên điện thoại.")
    add_bullet_item("Thao tác chi tiết", "1. Học sinh đăng ký: Mở app -> Bấm 'Đăng ký' -> Chọn vai trò 'Học sinh' -> Nhập Họ tên (Nguyễn Văn A), chọn Trường THPT Nguyễn Huệ, chọn Lớp 10A1, nhập SĐT -> Hệ thống tự động cấp Mã định danh học sinh: HS1001.\n2. Phụ huynh liên kết: Phụ huynh tải app -> Bấm 'Đăng ký' -> Chọn vai trò 'Phụ huynh' -> Nhập Số điện thoại phụ huynh -> Nhập Mã định danh của con (HS1001) -> Tích chọn xác nhận: 'Tôi đã đọc và đồng thuận cho phép nhà trường thu thập dữ liệu sinh trắc học để điểm danh theo Nghị định 13/2023/NĐ-CP'.")
    add_bullet_item("Kết quả đầu ra", "Thiết lập luồng liên kết thông tin an toàn giữa hồ sơ học sinh và điện thoại phụ huynh; bảo đảm đầy đủ căn cứ pháp lý bảo vệ dữ liệu cá nhân.")

    add_subsec_title("Bước 5: Nộp Ảnh Chân dung Mẫu & GVCN Duyệt Sinh trắc học FaceID")
    add_bullet_item("Chủ thể thực hiện", "Học sinh nộp ảnh mẫu -> Giáo viên chủ nhiệm kiểm duyệt.")
    add_bullet_item("Giao diện thực hiện", "App Mobile Học sinh -> Web Dashboard GVCN.")
    add_bullet_item("Thao tác chi tiết", "1. Học sinh đăng nhập app -> Vào mục 'Đăng ký FaceID': Đứng nơi đủ sáng, mặt nhìn thẳng vào camera, chụp 1 bức ảnh chân dung rõ nét (không khẩu trang, không kính râm) -> Bấm 'Gửi duyệt FaceID'.\n2. Giáo viên chủ nhiệm vào mục 'Kiểm duyệt Khuôn mặt Lớp' trên Web: Thấy ảnh chân dung của học sinh Nguyễn Văn A hiện lên cùng họ tên và mã số -> Thầy/Cô nhìn xác nhận đúng là học sinh lớp mình -> Bấm nút 'Chấp thuận' màu xanh.")
    add_bullet_item("Kết quả đầu ra", "Hệ thống tự động trích xuất vector đặc trưng toán học 128 chiều từ ảnh và nạp vào cơ sở dữ liệu nhận diện tại các trạm camera cổng trường.")

    add_subsec_title("Bước 6: Cấu hình & Kích hoạt Trạm Camera AI tại Cổng trường")
    add_bullet_item("Chủ thể thực hiện", "Cán bộ Kỹ thuật / Giám thị trường.")
    add_bullet_item("Giao diện & Thiết bị", "Bảng điều khiển Web BGH -> Raspberry Pi / Máy tính Mini tại cổng.")
    add_bullet_item("Thao tác chi tiết", "1. Hiệu trưởng vào Web -> 'Trạm Camera' -> Bấm '+ Thêm Trạm' (Đặt tên: 'Cổng Chính 01') -> Nhận chuỗi khóa bí mật secret_key.\n2. Tại cổng trường, cắm Webcam Full HD vào máy tính mini hoặc Raspberry Pi -> Mở terminal chạy lệnh: python main.py --school_id 1 --secret_key <SECRET_KEY> --api_url https://tenmien.vn.\n3. Mở công cụ hsv_picker.html kéo thanh trượt cân chỉnh màu áo trắng trong 1 phút cho khớp với điều kiện ánh sáng thực tế cổng trường.")
    add_bullet_item("Kết quả đầu ra", "Trạm camera chuyển sang trạng thái đèn xanh ONLINE trên máy chủ đám mây, sẵn sàng đón học sinh mỗi buổi sáng.")

    # III. GIAI ĐOẠN II
    add_sec_title("III. GIAI ĐOẠN II: VẬN HÀNH ĐIỂM DANH & GIÁM SÁT NỀ NẾP THƯỜNG NHẬT")
    add_p("Giai đoạn này diễn ra tự động và liên tục mỗi buổi sáng tại cổng trường:")

    add_subsec_title("Bước 7: Khởi động Trạm Camera Cổng trường Buổi Sáng")
    add_bullet_item("Thời gian & Chủ thể", "Đúng 06:15 sáng mỗi ngày; Giám thị trực cổng hoặc hệ thống tự động khởi động.")
    add_bullet_item("Giao diện thực hiện", "Màn hình TV hoặc máy tính tại bốt gác cổng trường hiển thị video luồng trực tiếp góc rộng.")
    add_bullet_item("Thao tác giám sát", "Giám thị quan sát màn hình với các phím tắt nhanh: Nhấn 'S' xem nhanh tổng số học sinh đã vào trường; nhấn 'U' tạm tắt soi đồng phục trong ngày lễ hội; nhấn 'T' hiển thị khung bám vết nhiều người.")
    add_bullet_item("Kết quả đầu ra", "Cổng trường được số hóa hoàn toàn, cán bộ giám sát không cần cầm sổ tay ghi chép thủ công.")

    add_subsec_title("Bước 8: Học sinh Qua Cổng & Tự động Phân tích Đa tầng")
    add_bullet_item("Thời gian & Chủ thể", "Từ 06:30 đến 07:15 sáng; Học sinh đi bộ qua cổng trường với tốc độ tự nhiên.")
    add_bullet_item("Luồng xử lý tự động (0.2s)", "1. Chống gian lận (Anti-spoofing): Kiểm tra vi chuyển động da và cử động chớp mắt, chặn đứng người cầm ảnh in hoặc video điện thoại điểm danh hộ bạn.\n2. Nhận diện khuôn mặt: Bắt trúng khuôn mặt rõ nhất, so khớp vector 128 chiều xác định danh tính: Nguyễn Văn A - Lớp 10A1.\n3. Soi đồng phục: Cắt vùng ngực áo, chuyển sang không gian màu HSV xác nhận: Áo sơ mi trắng Hợp lệ.\n4. Phản hồi trực quan:\n- Khung Xanh Lá Cây + tiếng BEEP nhẹ: Hợp lệ, điểm danh thành công.\n- Khung Đỏ nhấp nháy: Vi phạm (đi trễ hoặc sai áo). Kích hoạt tính năng Smart Best-shot tự động chụp 2 bức ảnh (1 cận mặt + 1 toàn cảnh có khung đỏ) lưu làm bằng chứng.\n5. Lưu trữ ngoại tuyến (Offline-First): Ghi tức thời vào SQLite cục bộ trên máy trạm, bảo đảm mất mạng vẫn hoạt động bình thường 100%.")

    add_subsec_title("Bước 9: Tiếp nhận Dữ liệu Realtime (Web Giáo viên & Mobile Phụ huynh)")
    add_bullet_item("Thời gian & Chủ thể", "Diễn ra đồng thời khi học sinh vừa bước qua cổng (< 1 giây); GVCN và Phụ huynh.")
    add_bullet_item("Tại lớp học (GVCN)", "GVCN mở Web Dashboard trên máy tính: Biểu đồ sĩ số lớp tự động nhảy số theo thời gian thực qua WebSockets (ví dụ: '39/40 học sinh đã có mặt - 1 học sinh chưa đến'). GVCN không tốn một giây nào để gọi tên điểm danh đầu giờ.")
    add_bullet_item("Tại gia đình (Phụ huynh)", "Điện thoại phụ huynh rung chuông thông báo đẩy tức thời: 'Con Nguyễn Văn A đã vào cổng trường lúc 06:48 - Trang phục: Hợp lệ'. Bấm vào thông báo, phụ huynh xem được bức ảnh chụp thực tế con mình tại cổng trường.")

    # IV. GIAI ĐOẠN III
    add_sec_title("IV. GIAI ĐOẠN III: XỬ LÝ NGHIỆP VỤ HẬU KIỂM, KHIẾU NẠI & TỔNG KẾT THI ĐUA")
    add_p("Giai đoạn này xử lý các tình huống phát sinh sau điểm danh và khép lại chu trình quản lý nề nếp học đường:")

    add_subsec_title("Bước 10: Nộp & Phê duyệt Đơn xin Nghỉ phép Trực tuyến")
    add_bullet_item("Chủ thể thực hiện", "Phụ huynh gửi đơn -> Giáo viên chủ nhiệm phê duyệt.")
    add_bullet_item("Thao tác chi tiết", "1. Khi con bị ốm, phụ huynh mở App -> Bấm 'Nộp đơn xin nghỉ học' -> Chọn ngày nghỉ, chọn lý do (ốm/sốt), đính kèm ảnh chụp sổ khám bệnh hoặc đơn viết tay -> Bấm Gửi.\n2. GVCN nhận thông báo trên máy tính -> Bấm 'Chấp thuận'.")
    add_bullet_item("Kết quả đầu ra", "Hệ thống tự động chuyển trạng thái học sinh từ 'Chưa đến' thành 'Nghỉ có phép' vào sổ điểm danh điện tử, lớp học không bị trừ điểm thi đua chuyên cần.")

    add_subsec_title("Bước 11: Quy trình Khiếu nại Nề nếp 2 Cấp (Minh bạch & Nhân văn)")
    add_bullet_item("Chủ thể thực hiện", "Học sinh khiếu nại -> GVCN giải quyết Cấp 1 -> Giám thị duyệt Cấp 2.")
    add_bullet_item("Tình huống thực tế", "Vào đợt rét mùa đông, học sinh Nguyễn Văn A mặc áo khoác ấm che áo sơ mi trắng bên trong nên bị camera ghi nhận 'Sai đồng phục'.")
    add_bullet_item("Thao tác xử lý", "1. Học sinh nộp khiếu nại: Mở app, bấm vào bản ghi vi phạm -> Viết giải trình: 'Em mặc áo khoác giữ ấm do trời rét, bên trong em vẫn mặc áo trắng'.\n2. GVCN xử lý Cấp 1: Mở Dashboard, phóng to bức ảnh gốc độ nét cao do camera lưu lại, thấy đúng học sinh có mặc áo sơ mi trắng bên trong -> Bấm 'Chấp thuận Cấp 1'.")
    add_bullet_item("Kết quả đầu ra", "Hệ thống tự động hủy lỗi vi phạm, tự động hoàn trả +5 điểm thi đua cho lớp 10A1. Trường hợp có tranh chấp phức tạp giữa các lớp sẽ được chuyển tiếp lên Giám thị trưởng duyệt Cấp 2.")

    add_subsec_title("Bước 12: Tổng kết Điểm rèn luyện, Thi đua & Xuất Báo cáo Định kỳ")
    add_bullet_item("Chủ thể thực hiện", "Giám thị chấm điểm -> Hiệu trưởng ký duyệt điện tử -> Văn phòng xuất file.")
    add_bullet_item("Thao tác chi tiết", "1. Chiều thứ Sáu hàng tuần, hệ thống tự động tổng hợp dữ liệu chuyên cần, đi trễ, vi phạm đồng phục của toàn bộ các lớp thành Bảng Xếp Hạng Thi Đua Tuần một cách tuyệt đối khách quan.\n2. Giám thị kiểm tra bảng xếp hạng -> Trình Ban Giám hiệu.\n3. Hiệu trưởng xem biểu đồ phân tích toàn trường trên Web Dashboard -> Bấm 'Ký duyệt điện tử'.\n4. Văn phòng nhà trường bấm nút 'Xuất Excel / PDF' để tải về sổ điểm danh điện tử và thông báo trong lễ chào cờ đầu tuần kế tiếp.")
    add_bullet_item("Kết quả đầu ra", "Toàn bộ quy trình nề nếp học đường được số hóa khép kín 100%, bảo đảm tính công bằng, minh bạch, giảm tải áp lực cho thầy cô và xây dựng môi trường học đường số văn minh.")

    add_highlight_box("LỜI KHUYÊN CHO BUỔI THUYẾT TRÌNH BẢO VỆ DỰ ÁN", 
                      "Khi trình bày 12 bước này trước Ban Giám khảo, bạn nên nhấn mạnh 3 thông điệp lớn:\n"
                      "1. Tính khép kín: Dự án không dừng lại ở một camera nhận diện mà giải quyết trọn vẹn chu trình quản lý nề nếp từ A đến Z.\n"
                      "2. Tính nhân văn: Có quy trình khiếu nại 2 cấp và nộp đơn nghỉ phép online, không phạt oan học sinh.\n"
                      "3. Tính tự động hóa: Giảm 100% thời gian điểm danh gọi tên thủ công, phụ huynh yên tâm tuyệt đối mỗi ngày.")

    # --- CHỮ KÝ XÁC NHẬN ---
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
    r = p_fl.add_run("- Ban Giám hiệu Nhà trường;\n")
    format_run(r, size=11.5)
    r = p_fl.add_run("- Hội đồng Chấm thi KHKT / STEM;\n")
    format_run(r, size=11.5)
    r = p_fl.add_run("- Cán bộ Giám thị & GVCN;\n")
    format_run(r, size=11.5)
    r = p_fl.add_run("- Lưu: Hồ sơ Kỹ thuật Dự án.")
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
    phu_luc_folder = os.path.expanduser('~/PHU LUC STEM')
    if not os.path.exists(phu_luc_folder):
        os.makedirs(phu_luc_folder, exist_ok=True)
        
    download_folder = os.path.expanduser('~/Bản tải về')
    if not os.path.exists(download_folder):
        os.makedirs(download_folder, exist_ok=True)
        
    out_path_phu_luc = os.path.join(phu_luc_folder, "QUY_TRINH_THUC_HIEN_THUC_TE_STEM.docx")
    out_path_download = os.path.join(download_folder, "QUY_TRINH_THUC_HIEN_THUC_TE_STEM.docx")
    out_path_repo = "/home/minhphuc/Diem-danh-STEM/docs/reports/QUY_TRINH_THUC_HIEN_THUC_TE_STEM.docx"

    doc.save(out_path_phu_luc)
    doc.save(out_path_download)
    doc.save(out_path_repo)
    print(f"Xuat file docx thanh cong:")
    print(f"1. {out_path_phu_luc}")
    print(f"2. {out_path_download}")
    print(f"3. {out_path_repo}")

if __name__ == "__main__":
    generate_practical_steps_docx()
