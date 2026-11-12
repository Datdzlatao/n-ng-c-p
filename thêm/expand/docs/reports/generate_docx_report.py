import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os

def create_full_report():
    doc = Document()

    # 1. Cấu hình lề trang theo Nghị định 30/2020/NĐ-CP
    sections = doc.sections
    for s in sections:
        s.top_margin = Cm(2.0)
        s.bottom_margin = Cm(2.0)
        s.left_margin = Cm(3.0)
        s.right_margin = Cm(2.0)
        s.page_width = Cm(21.0)
        s.page_height = Cm(29.7)

    # 2. Cấu hình style mặc định: Times New Roman, 14pt
    normal_style = doc.styles['Normal']
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
        p = doc.add_paragraph()
        p.alignment = align
        if indent:
            p.paragraph_format.first_line_indent = Cm(1.27)
        else:
            p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.35
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
        p.paragraph_format.line_spacing = 1.35
        r = p.add_run(text)
        format_run(r, bold=True, size=14.5)
        return p

    def add_subsec_title(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.35
        r = p.add_run(text)
        format_run(r, bold=True, size=14)
        return p

    def add_subsubsec_title(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.35
        r = p.add_run(text)
        format_run(r, bold=True, italic=True, size=14)
        return p

    def add_bullet_item(bold_prefix, text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Cm(1.27)
        p.paragraph_format.first_line_indent = Cm(-0.6)
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.35
        r_b = p.add_run("- " + bold_prefix + ": ")
        format_run(r_b, bold=True, size=14)
        r_t = p.add_run(text)
        format_run(r_t, bold=False, size=14)
        return p

    def add_ordered_item(num_prefix, text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Cm(1.27)
        p.paragraph_format.first_line_indent = Cm(-0.6)
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.35
        r_b = p.add_run(num_prefix + " ")
        format_run(r_b, bold=True, size=14)
        r_t = p.add_run(text)
        format_run(r_t, bold=False, size=14)
        return p

    # --- PHẦN ĐẦU TRANG: QUỐC HIỆU, TIÊU NGỮ & CƠ QUAN BAN HÀNH ---
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
    format_run(r, bold=False, size=13)
    r = p_l.add_run("HỆ THỐNG EDUSAMS STEM\n")
    format_run(r, bold=True, size=13)
    r = p_l.add_run("Số: 01/BC-STEM")
    format_run(r, bold=False, size=13)

    p_r = cell_r.paragraphs[0]
    p_r.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_r.paragraph_format.line_spacing = 1.2
    p_r.paragraph_format.space_after = Pt(0)
    r = p_r.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n")
    format_run(r, bold=True, size=13)
    r = p_r.add_run("Độc lập - Tự do - Hạnh phúc\n")
    format_run(r, bold=True, size=13)
    r = p_r.add_run("---------------o0o---------------\n")
    format_run(r, bold=False, size=11)
    r = p_r.add_run("Hà Nội, ngày 10 tháng 09 năm 2026")
    format_run(r, bold=False, italic=True, size=12)

    # Khoảng cách trước tiêu đề chính
    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(12)
    p_sp.paragraph_format.space_after = Pt(4)

    # Tiêu đề báo cáo
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(6)
    p_title.paragraph_format.space_after = Pt(4)
    r_title = p_title.add_run("BÁO CÁO TỔNG HỢP TOÀN BỘ CHỨC NĂNG VÀ HƯỚNG DẪN VẬN HÀNH\nHỆ THỐNG ĐIỂM DANH HỌC SINH THÔNG MINH STEM")
    format_run(r_title, bold=True, size=15)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(16)
    r_sub = p_sub.add_run("(Hệ thống nhận diện khuôn mặt và kiểm soát nề nếp học đường tích hợp Trí tuệ nhân tạo)")
    format_run(r_sub, italic=True, size=13.5)

    # --- PHẦN I ---
    add_sec_title("PHẦN I. TỔNG QUAN VỀ HỆ THỐNG")

    add_subsec_title("1. Giới thiệu chung")
    add_p("Hệ thống Điểm danh Thông minh STEM (Edusams STEM) là giải pháp chuyển đổi số toàn diện trong công tác quản lý chuyên cần, giám sát nề nếp và kiểm tra tác phong đồng phục học sinh tại các cơ sở giáo dục phổ thông. Hệ thống được nghiên cứu và phát triển dựa trên mô hình kiến trúc phần mềm hiện đại, ứng dụng Trí tuệ nhân tạo (AI) và Thị giác máy tính (Computer Vision) tại các trạm biên (Edge Computing), kết hợp hệ thống máy chủ dịch vụ đa người dùng (Multi-Tenant SaaS).")
    add_p("Giải pháp khắc phục triệt để các hạn chế của phương pháp điểm danh truyền thống (gọi tên thủ công gây mất từ 15 đến 25 giờ giảng dạy mỗi năm cho mỗi lớp học, chấm công thẻ từ hoặc vân tay gây ùn tắc tại cổng trường), đồng thời tự động hóa hoàn toàn quy trình giám sát đồng phục theo lịch trình linh hoạt của từng ngày trong tuần.")

    add_subsec_title("2. Kiến trúc kỹ thuật và nền tảng công nghệ")
    add_p("Hệ thống được tổ chức theo cấu trúc kho mã nguồn hợp nhất (Monorepo), bao gồm 4 phân hệ chính hoạt động đồng bộ và bảo mật:")
    add_bullet_item("Phân hệ Máy chủ Dịch vụ (Backend API)", "Xây dựng trên nền tảng FastAPI (Python), cung cấp giao diện lập trình ứng dụng RESTful API hiệu năng cao, cơ chế kết nối thời gian thực qua WebSockets. Hệ thống cơ sở dữ liệu hỗ trợ linh hoạt giữa SQLite (tối ưu hóa chế độ Write-Ahead Logging - WAL) và PostgreSQL phục vụ môi trường quy mô lớn. Quy trình xác thực được mã hóa bằng thuật toán băm mật khẩu PBKDF2 kết hợp khóa bảo mật JWT.")
    add_bullet_item("Phân hệ Ứng dụng Web (Frontend Web App)", "Ứng dụng trang đơn (Single Page Application - SPA) được tối ưu hóa hiển thị đáp ứng (Responsive), phục vụ công tác quản trị, điều hành và tác nghiệp của Ban Giám hiệu, Giám thị và Giáo viên trên máy tính để bàn cũng như thiết bị di động.")
    add_bullet_item("Phân hệ Trạm Camera Thông minh (Edge AI Station)", "Triển khai trên các máy tính biên độc lập (Raspberry Pi hoặc máy tính mini) đặt tại cổng trường. Tích hợp camera thu hình tốc độ cao, xử lý song song thuật toán trích xuất vector đặc trưng khuôn mặt (Face Embeddings 128 chiều), thuật toán chống giả mạo sinh trắc học (Anti-spoofing) và mô hình phân loại đồng phục kết hợp (Hybrid AI giữa không gian màu HSV và mạng nơ-ron tích chập TFLite MobileNetV2).")
    add_bullet_item("Phân hệ Ứng dụng Di động (Mobile App)", "Xây dựng trên nền tảng Flutter, hỗ trợ hai hệ điều hành Android và iOS, phục vụ nhu cầu tra cứu chuyên cần, nhận thông báo tức thời và gửi phản ánh của Phụ huynh và Học sinh.")

    add_subsec_title("3. Khả năng đặc tả của hệ thống")
    add_bullet_item("Khả năng nhận diện tốc độ cao và chính xác", "Thời gian suy luận dưới 100 mili-giây trên mỗi khung hình, nhận diện khuôn mặt chính xác ở khoảng cách từ 1.5 mét đến 4 mét, độ tin cậy đạt trên 95%.")
    add_bullet_item("Khả năng kiểm tra đồng phục tự động theo lịch tuần", "Phân loại chính xác đồng phục áo trắng, áo Đoàn thanh niên thông qua phân tích không gian màu HSV, và nhận diện trang phục họa tiết (áo truyền thống, áo dân tộc) thông qua mô hình học sâu MobileNetV2.")
    add_bullet_item("Khả năng duy trì hoạt động ngoại tuyến (Offline-First)", "Khi xảy ra sự cố mất kết nối mạng Internet, trạm camera tại cổng vẫn tiếp tục nhận diện và lưu trữ dữ liệu cục bộ an toàn trên bộ nhớ đệm SQLite. Ngay khi có mạng trở lại, hệ thống tự động đồng bộ bù dữ liệu về máy chủ trung tâm, bảo đảm không thất thoát dữ liệu.")
    add_bullet_item("Khả năng truyền thông tin thời gian thực", "Dữ liệu điểm danh được phát sóng ngay lập tức qua giao thức WebSocket đến bảng điều khiển của Giám thị và gửi thông báo trực tiếp đến thiết bị di động của Phụ huynh học sinh.")
    add_bullet_item("Khả năng tuân thủ pháp lý về bảo vệ dữ liệu cá nhân", "Tích hợp đầy đủ phân hệ quản lý thỏa thuận đồng thuận sinh trắc học và thực thi quyền hủy bỏ dữ liệu (Right to Erasure) theo đúng tinh thần Nghị định số 13/2023/NĐ-CP của Chính phủ.")

    # --- PHẦN II ---
    add_sec_title("PHẦN II. MA TRẬN NHIỆM VỤ VÀ PHÂN QUYỀN HỆ THỐNG")
    add_p("Hệ thống thiết lập cơ chế kiểm soát truy cập dựa trên vai trò người dùng (Role-Based Access Control - RBAC) nghiêm ngặt, phân định rõ ràng quyền hạn và trách nhiệm của từng chủ thể tham gia:")

    # Bảng phân quyền
    table = doc.add_table(rows=7, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    col_widths = [Cm(1.2), Cm(4.5), Cm(6.5), Cm(4.0)]
    headers = ["STT", "Vai trò (Role)", "Nhiệm vụ cốt lõi", "Phạm vi quản lý"]

    hdr_cells = table.rows[0].cells
    for i, h_text in enumerate(headers):
        hdr_cells[i].width = col_widths[i]
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(h_text)
        format_run(r, bold=True, size=13)
        tcPr = hdr_cells[i]._element.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F2F2F2"/>')
        tcPr.append(shd)

    data = [
        ("1", "Quản trị viên Nền tảng\n(Platform Super Admin)", "Quản trị hạ tầng công nghệ, vận hành hệ thống đa trường học (SaaS), cấp phát tài nguyên và kiểm tra an toàn thông tin toàn hệ thống.", "Toàn bộ các máy chủ trường học trên nền tảng."),
        ("2", "Hiệu trưởng / Ban Giám hiệu\n(Headmaster / School Admin)", "Thiết lập nội quy nhà trường, quy định giờ giấc, quản lý trạm camera, phê duyệt bảng điểm thi đua và giám sát chỉ số chuyên cần toàn trường.", "Toàn trường nơi được phân công quyền quản trị."),
        ("3", "Giám thị / Cán bộ Nề nếp\n(Inspector)", "Giám sát trực tiếp quá trình học sinh qua cổng, giải quyết khiếu nại Cấp 2, chấm điểm thi đua nề nếp hàng tuần và phát cảnh báo trường học.", "Khu vực cổng trường, các lớp học và toàn thể học sinh trong trường."),
        ("4", "Giáo viên Chủ nhiệm\n(Homeroom Teacher)", "Quản lý học sinh lớp chủ nhiệm, duyệt ảnh khuôn mặt đầu vào, duyệt đơn xin nghỉ phép, giải quyết khiếu nại Cấp 1 và theo dõi chuyên cần lớp.", "Lớp học được nhà trường phân công phụ trách."),
        ("5", "Phụ huynh Học sinh\n(Parent)", "Theo dõi thời gian vào trường thực tế của con, gửi đơn xin phép nghỉ học trực tuyến, ký thỏa thuận đồng thuận sinh trắc học và phản ánh sai sót.", "Học sinh là con em được liên kết xác thực."),
        ("6", "Học sinh\n(Student)", "Thực hiện điểm danh qua camera hoặc mã QR dự phòng, theo dõi lịch sử chuyên cần cá nhân, nộp minh chứng khuôn mặt và gửi khiếu nại khi có sai lệch.", "Tài khoản cá nhân của học sinh.")
    ]

    for row_idx, row_data in enumerate(data, start=1):
        row_cells = table.rows[row_idx].cells
        for col_idx, text in enumerate(row_data):
            row_cells[col_idx].width = col_widths[col_idx]
            p = row_cells[col_idx].paragraphs[0]
            p.paragraph_format.line_spacing = 1.2
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)
            if col_idx == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(text)
                format_run(r, bold=False, size=12.5)
            elif col_idx == 1:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(text)
                format_run(r, bold=True, size=12.5)
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                r = p.add_run(text)
                format_run(r, bold=False, size=12.5)

    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = parse_xml(f'''
            <w:tblBorders {nsdecls("w")}>
                <w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:left w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:right w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:insideH w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>
                <w:insideV w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>
            </w:tblBorders>
        ''')
        tblPr[0].append(borders)

    add_p("", indent=False, space_before=6, space_after=6)

    # --- PHẦN III ---
    add_sec_title("PHẦN III. CHI TIẾT CHỨC NĂNG, KHẢ NĂNG VÀ CÁCH SỬ DỤNG CỦA TỪNG VAI TRÒ")

    # Vai trò 1
    add_subsec_title("1. Vai trò Quản trị viên Nền tảng (Platform Super Admin)")
    add_subsubsec_title("a) Nhiệm vụ:")
    add_p("Chịu trách nhiệm cao nhất về mặt kỹ thuật, quản lý toàn bộ hệ sinh thái đa trường học, kiểm soát việc đăng ký và cấp quyền cho các trường mới, đảm bảo tính ổn định và bảo mật của cơ sở dữ liệu trung tâm.")
    add_subsubsec_title("b) Chức năng và Khả năng:")
    add_bullet_item("Quản lý danh sách trường học", "Khởi tạo hồ sơ trường học mới, kích hoạt hoặc tạm dừng hoạt động của máy chủ trường học (trạng thái ACTIVE hoặc SUSPENDED).")
    add_bullet_item("Giám sát chỉ số tài nguyên", "Thống kê số lượng trường tham gia, tổng số học sinh, tổng lượt điểm danh trong ngày và mức tiêu thụ tài nguyên máy chủ.")
    add_bullet_item("Quản trị an toàn thông tin", "Kiểm soát danh sách đen các khóa phiên làm việc (Token Blacklist), rà soát nhật ký truy cập trái phép và bảo vệ hệ thống trước các cuộc tấn công từ chối dịch vụ (Rate Limiting).")
    add_bullet_item("Khởi tạo mã quản trị gốc", "Thiết lập tài khoản quản trị ban đầu cho Hiệu trưởng của từng trường.")
    add_subsubsec_title("c) Hướng dẫn sử dụng:")
    add_ordered_item("Bước 1 (Đăng nhập):", "Truy cập vào trang chủ hệ thống, chọn mục 'Admin Nền tảng', nhập thông tin tài khoản và mật khẩu quản trị cấp cao.")
    add_ordered_item("Bước 2 (Quản lý trường học):", "Tại màn hình 'Quản trị Nền tảng', chọn 'Thêm trường mới' để điền thông tin trường (Tên trường, mã định danh, địa chỉ, niên khóa). Chọn 'Phê duyệt' để cấp quyền mở máy chủ trường học.")
    add_ordered_item("Bước 3 (Giám sát):", "Theo dõi biểu đồ số liệu thời gian thực trên màn hình tổng quan để nắm bắt lưu lượng truy cập toàn nền tảng.")

    # Vai trò 2
    add_subsec_title("2. Vai trò Hiệu trưởng / Ban Giám hiệu (Headmaster)")
    add_subsubsec_title("a) Nhiệm vụ:")
    add_p("Đại diện cho Hội đồng sư phạm nhà trường quản lý toàn bộ hoạt động nề nếp trên môi trường số; ban hành quy chuẩn thời gian, đồng phục; quản lý thiết bị camera và phê duyệt các đánh giá xếp loại thi đua.")
    add_subsubsec_title("b) Chức năng và Khả năng:")
    add_bullet_item("Cấu hình quy định trường học (School Rules Configuration)", "Tùy chỉnh khung giờ điểm danh (giờ mở cổng, mốc tính muộn, mốc tính vắng); thiết lập quy định trang phục theo lịch tuần (ví dụ: Thứ Hai mặc áo truyền thống/áo dài; Thứ Ba, Năm mặc áo sơ mi trắng; Thứ Sáu mặc áo Đoàn thanh niên).")
    add_bullet_item("Quản lý mã mời tham gia (Role Invite Codes)", "Tạo và phát hành mã xác thực riêng biệt cho Giáo viên, Giám thị và Cán bộ Ban Giám hiệu để đăng ký tài khoản vào hệ thống trường.")
    add_bullet_item("Quản lý trạm Camera AI", "Thêm mới, đổi tên trạm camera (Cổng chính, Cổng phụ); tạo mã bí mật (Secret Key) để cài đặt vào máy tính biên Raspberry Pi; giám sát trạng thái trực tuyến/ngoại tuyến của từng trạm.")
    add_bullet_item("Quản lý cơ cấu tổ chức", "Thiết lập danh sách các khối lớp, tạo lớp học mới và phân công chỉ định Giáo viên chủ nhiệm.")
    add_bullet_item("Bảng điều khiển điều hành (Executive Dashboard)", "Xem trực quan tỷ lệ học sinh đến trường theo thời gian thực, biểu đồ phân tích chuyên cần theo khối và các trường hợp vi phạm nề nếp nổi bật.")
    add_bullet_item("Phê duyệt thi đua tuần", "Xem xét, nhận xét và bấm duyệt bảng tổng hợp điểm nề nếp thi đua giữa các lớp do Giám thị đệ trình.")
    add_subsubsec_title("c) Hướng dẫn sử dụng:")
    add_ordered_item("Bước 1 (Thiết lập quy định):", "Đăng nhập tài khoản Hiệu trưởng, truy cập mục 'Cấu hình trường'. Nhập khung giờ điểm danh chuẩn và chọn quy định đồng phục tương ứng cho từng ngày từ Thứ Hai đến Thứ Bảy, sau đó bấm 'Lưu cấu hình'.")
    add_ordered_item("Bước 2 (Khởi tạo trạm camera):", "Vào mục 'Trạm Camera', chọn 'Thêm Trạm', điền tên vị trí (ví dụ: 'Camera Cổng Chính'). Hệ thống tự sinh mã khóa bí mật (Secret Key). Sao chép chuỗi mã này để cấu hình cho thiết bị Raspberry Pi tại cổng trường.")
    add_ordered_item("Bước 3 (Phân công chủ nhiệm):", "Vào mục 'Quản lý Lớp', chọn lớp học cần chỉnh sửa, chọn Giáo viên từ danh sách nhân sự đã kích hoạt và bấm 'Cập nhật'.")
    add_ordered_item("Bước 4 (Duyệt thi đua):", "Cuối mỗi tuần, vào mục 'Thi đua nề nếp', kiểm tra bảng xếp loại các lớp, ghi chú chỉ đạo và bấm 'Phê duyệt bảng điểm'.")

    # Vai trò 3
    add_subsec_title("3. Vai trò Giám thị / Cán bộ Nề nếp (Inspector)")
    add_subsubsec_title("a) Nhiệm vụ:")
    add_p("Trực tiếp giám sát nề nếp học sinh tại hiện trường cổng trường; điều phối các tình huống bất thường trong giờ cao điểm; giải quyết các tranh chấp điểm danh phức tạp và tổng hợp điểm thi đua học đường.")
    add_subsubsec_title("b) Chức năng và Khả năng:")
    add_bullet_item("Màn hình giám sát trực tiếp (Live Stream & Logs Monitor)", "Theo dõi liên tục dòng dữ liệu điểm danh truyền về từ các trạm camera theo thời gian thực. Hệ thống hiển thị rõ ràng ảnh chụp hiện trường, tên học sinh, lớp, thời gian chính xác, trạng thái đúng giờ/muộn và kết quả kiểm tra đồng phục.")
    add_bullet_item("Điểm danh bổ sung và ghi nhận lỗi thủ công", "Thực hiện tra cứu nhanh học sinh để điểm danh hoặc bổ sung ghi chú vi phạm đối với các trường hợp đặc biệt không thể nhận diện qua camera.")
    add_bullet_item("Xử lý khiếu nại Cấp 2 (Level 2 Dispute Resolution)", "Tiếp nhận các hồ sơ khiếu nại vượt cấp hoặc do Giáo viên chủ nhiệm chuyển lên. Xem xét hình ảnh bằng chứng gốc lưu trữ trên máy chủ để đưa ra phán quyết phê duyệt điều chỉnh hoặc bác bỏ khiếu nại.")
    add_bullet_item("Tổng kết và chấm điểm thi đua", "Khởi tạo bảng điểm tuần cho các lớp học. Hệ thống tự động tổng hợp điểm chuyên cần, điểm trừ vi phạm đồng phục; Giám thị nhập bổ sung điểm kỷ luật hoặc điểm thưởng phong trào và chuyển trình Hiệu trưởng.")
    add_bullet_item("Phát cảnh báo trường học", "Gửi thông báo khẩn cấp tới toàn trường hoặc từng khối lớp khi có tình huống phát sinh.")
    add_subsubsec_title("c) Hướng dẫn sử dụng:")
    add_ordered_item("Bước 1 (Trực cổng đầu giờ):", "Đăng nhập tài khoản Giám thị, mở mục 'Điểm danh' và chọn chế độ 'Giám sát trực tiếp'. Màn hình sẽ tự động cập nhật mỗi khi có học sinh bước qua cổng trạm camera.")
    add_ordered_item("Bước 2 (Xử lý sự cố tại cổng):", "Nếu học sinh chưa được nhận diện hoặc vi phạm đồng phục, Giám thị bấm vào bản ghi để kiểm tra ảnh phóng to và điều chỉnh trạng thái nếu cần thiết.")
    add_ordered_item("Bước 3 (Giải quyết khiếu nại):", "Truy cập mục 'Khiếu nại', chọn bộ lọc 'Cấp 2 (Giám thị)'. Đọc tường trình của học sinh/phụ huynh, kiểm tra ảnh chụp đối chiếu và chọn 'Chấp thuận' hoặc 'Từ chối' kèm lý do giải quyết.")
    add_ordered_item("Bước 4 (Chấm thi đua tuần):", "Vào mục 'Thi đua', chọn tuần học cần tổng kết, bấm 'Tính toán tự động', rà soát điểm số các lớp và bấm 'Gửi Ban Giám hiệu duyệt'.")

    # Vai trò 4
    add_subsec_title("4. Vai trò Giáo viên Chủ nhiệm (Homeroom Teacher)")
    add_subsubsec_title("a) Nhiệm vụ:")
    add_p("Quản lý toàn diện cơ sở dữ liệu học sinh của lớp phụ trách; kiểm soát tính chính xác của dữ liệu sinh trắc học đầu vào; phê duyệt đơn nghỉ phép của phụ huynh và giải quyết các khiếu nại chuyên cần ban đầu.")
    add_subsubsec_title("b) Chức năng và Khả năng:")
    add_bullet_item("Quản trị danh sách học sinh lớp", "Theo dõi hồ sơ lý lịch, số điện thoại liên lạc của cha mẹ học sinh và trạng thái liên kết tài khoản phụ huynh.")
    add_bullet_item("Phê duyệt dữ liệu khuôn mặt (Biometric Approval)", "Kiểm tra chất lượng hình ảnh học sinh gửi lên hệ thống (đảm bảo rõ nét, chụp thẳng mặt, không đeo kính râm, không bị che khuất) trước khi bấm duyệt để hệ thống trích xuất vector khuôn mặt.")
    add_bullet_item("Xử lý đơn xin nghỉ phép (Leave Requests Management)", "Xem danh sách đơn xin phép nghỉ học do phụ huynh nộp qua ứng dụng di động; xem xét lý do và bấm 'Duyệt' hoặc 'Từ chối'. Dữ liệu duyệt sẽ tự động cập nhật trạng thái 'Nghỉ có phép' vào sổ điểm danh ngày.")
    add_bullet_item("Giải quyết khiếu nại Cấp 1 (Level 1 Dispute Resolution)", "Tiếp nhận phản ánh của học sinh hoặc phụ huynh về việc bị ghi nhận muộn hoặc nhận diện nhầm đồng phục. Giáo viên có quyền sửa đổi bản ghi điểm danh hoặc chuyển tiếp (Escalate) lên Giám thị nếu cần xác minh bằng chứng phức tạp.")
    add_bullet_item("Thống kê báo cáo lớp", "Xem báo cáo tổng hợp chuyên cần theo tuần, tháng để kịp thời đôn đốc, nhắc nhở học sinh và thông tin đến gia đình.")
    add_subsubsec_title("c) Hướng dẫn sử dụng:")
    add_ordered_item("Bước 1 (Kiểm duyệt khuôn mặt):", "Vào mục 'Học sinh', chọn tab 'Chờ duyệt ảnh'. Xem xét từng ảnh chân dung của học sinh trong lớp. Nếu đạt tiêu chuẩn, bấm 'Duyệt ảnh'. Nếu mờ hoặc sai quy cách, bấm 'Yêu cầu chụp lại'.")
    add_ordered_item("Bước 2 (Duyệt đơn nghỉ phép):", "Khi có thông báo mới, vào mục 'Đơn nghỉ phép', đọc nội dung đơn và thời gian nghỉ của học sinh, chọn 'Phê duyệt' để hệ thống tự động ghi nhận học sinh nghỉ có phép.")
    add_ordered_item("Bước 3 (Xử lý khiếu nại):", "Vào mục 'Khiếu nại', chọn đơn của học sinh lớp mình, kiểm tra thời gian vào cổng thực tế, chọn 'Chấp thuận sửa đổi' hoặc 'Chuyển lên Giám thị'.")
    add_ordered_item("Bước 4 (Điểm danh tại lớp):", "Vào mục 'Điểm danh', chọn ngày hiện tại để kiểm tra danh sách học sinh vắng mặt; có thể cập nhật trạng thái thủ công nếu học sinh vào lớp muộn vì lý do việc chung của trường.")

    # Vai trò 5
    add_subsec_title("5. Vai trò Phụ huynh Học sinh (Parent)")
    add_subsubsec_title("a) Nhiệm vụ:")
    add_p("Phối hợp chặt chẽ với nhà trường trong công tác quản lý giờ giấc và rèn luyện của con em; thực hiện đầy đủ nghĩa vụ xác nhận pháp lý về dữ liệu sinh trắc học cá nhân của trẻ vị thành niên.")
    add_subsubsec_title("b) Chức năng và Khả năng:")
    add_bullet_item("Nhận thông báo điểm danh tức thời", "Nhận tin nhắn thông báo trên ứng dụng di động ngay khi con bước qua cổng trường, kèm thời gian chi tiết và hình ảnh chụp tại trạm camera.")
    add_bullet_item("Tra cứu lịch sử chuyên cần", "Theo dõi nhật ký đi học của con theo từng ngày, kiểm tra các lần đi muộn hoặc vi phạm đồng phục để kịp thời phối hợp giáo dục.")
    add_bullet_item("Nộp đơn xin nghỉ phép trực tuyến", "Soạn và gửi đơn xin phép nghỉ học cho con ngay trên ứng dụng di động, đính kèm lý do chính đáng và thời gian nghỉ cụ thể mà không cần viết đơn giấy.")
    add_bullet_item("Quản lý đồng thuận sinh trắc học (Biometric Consent)", "Ký xác nhận cho phép nhà trường thu thập và xử lý hình ảnh khuôn mặt của con phục vụ điểm danh, hoặc thực hiện quyền thu hồi văn bản đồng thuận theo quy định pháp luật.")
    add_bullet_item("Gửi phản ánh, khiếu nại nề nếp", "Gửi yêu cầu xem xét lại khi phát hiện kết quả điểm danh của con có dấu hiệu nhầm lẫn hoặc camera nhận diện chưa chính xác.")
    add_subsubsec_title("c) Hướng dẫn sử dụng:")
    add_ordered_item("Bước 1 (Đăng ký và liên kết):", "Cài đặt ứng dụng di động, đăng ký tài khoản bằng số điện thoại đã cung cấp cho nhà trường. Nhập mã định danh học sinh của con để hoàn tất liên kết tài khoản.")
    add_ordered_item("Bước 2 (Ký đồng thuận sinh trắc học):", "Tại màn hình hồ sơ học sinh, đọc văn bản quy định bảo vệ dữ liệu, tích chọn đồng ý và bấm 'Xác nhận đồng thuận'.")
    add_ordered_item("Bước 3 (Theo dõi điểm danh):", "Mở mục 'Lịch sử điểm danh' để xem giờ vào cổng và ảnh minh chứng hàng ngày.")
    add_ordered_item("Bước 4 (Gửi đơn xin nghỉ):", "Mở mục 'Đơn nghỉ phép', chọn 'Tạo đơn mới', chọn ngày bắt đầu, ngày kết thúc, ghi rõ lý do và bấm 'Gửi đơn'. Theo dõi phản hồi phê duyệt từ Giáo viên chủ nhiệm ngay trên ứng dụng.")

    # Vai trò 6
    add_subsec_title("6. Vai trò Học sinh (Student)")
    add_subsubsec_title("a) Nhiệm vụ:")
    add_p("Tự giác thực hiện điểm danh khi đến trường; chấp hành nghiêm túc quy định về trang phục học đường; chủ động kiểm tra thông tin chuyên cần cá nhân.")
    add_subsubsec_title("b) Chức năng và Khả năng:")
    add_bullet_item("Điểm danh tự động bằng khuôn mặt", "Đi qua cổng trường trong tầm quét của camera trạm, hệ thống tự động ghi nhận trong vòng 1 đến 2 giây mà không cần tiếp xúc.")
    add_bullet_item("Điểm danh dự phòng bằng mã QR", "Mở mã QR định danh cá nhân trên ứng dụng di động để đưa vào máy quét tại cổng trường trong trường hợp gặp sự cố về ánh sáng hoặc khuôn mặt chưa nhận diện được.")
    add_bullet_item("Tra cứu thông tin cá nhân", "Xem lịch sử vào cổng của bản thân, điểm nề nếp rèn luyện và xếp hạng thi đua của lớp mình.")
    add_bullet_item("Cập nhật ảnh nhận diện", "Tải ảnh chụp chân dung đúng quy cách lên hệ thống để gửi Giáo viên chủ nhiệm phê duyệt khi mới nhập học hoặc khi thay đổi diện mạo.")
    add_bullet_item("Gửi khiếu nại nề nếp", "Tạo yêu cầu giải trình trực tiếp trên ứng dụng nếu bị hệ thống ghi nhận sai thời gian hoặc nhầm lẫn lỗi đồng phục.")
    add_subsubsec_title("c) Hướng dẫn sử dụng:")
    add_ordered_item("Bước 1 (Điểm danh hàng ngày):", "Khi đi qua cổng trường, học sinh nhìn thẳng hướng camera của trạm biên trong khoảng 1 đến 2 giây cho đến khi trạm báo tín hiệu nhận diện thành công.")
    add_ordered_item("Bước 2 (Sử dụng mã QR dự phòng):", "Nếu trạm camera gặp sự cố mạng hoặc nhận diện chưa thành công, học sinh mở ứng dụng di động, chọn 'Thẻ QR cá nhân' và đưa màn hình điện thoại trước ống kính camera quét mã.")
    add_ordered_item("Bước 3 (Gửi khiếu nại):", "Nếu bị chấm muộn do lỗi hệ thống, học sinh vào mục 'Khiếu nại nề nếp', chọn bản ghi điểm danh tương ứng, viết rõ lý do giải trình và bấm 'Gửi khiếu nại' để chuyển tới Giáo viên chủ nhiệm.")

    # --- PHẦN IV ---
    add_sec_title("PHẦN IV. QUY TRÌNH VẬN HÀNH VÀ PHỐI HỢP LIÊN VAI TRÒ")

    add_subsec_title("1. Quy trình điểm danh và giám sát buổi sáng")
    add_p("Quy trình phối hợp vận hành hàng ngày được chuẩn hóa qua 6 bước tuần tự:")
    add_bullet_item("Bước 1", "Trạm Camera AI tại cổng trường khởi động, tự động kết nối với máy chủ trung tâm qua giao thức API an toàn.")
    add_bullet_item("Bước 2", "Học sinh đi qua cổng trường, trạm camera chụp ảnh, trích xuất vector khuôn mặt và phân tích màu sắc đồng phục.")
    add_bullet_item("Bước 3", "Trạm camera đồng bộ dữ liệu về máy chủ thông qua giao diện API. Nếu mất mạng Internet, dữ liệu tự động lưu vào bộ nhớ đệm SQLite cục bộ tại trạm.")
    add_bullet_item("Bước 4", "Máy chủ xác nhận dữ liệu, tự động đẩy bản ghi thời gian thực lên màn hình giám sát của Giám thị qua WebSockets.")
    add_bullet_item("Bước 5", "Hệ thống kích hoạt dịch vụ thông báo, gửi tin nhắn kèm hình ảnh đến điện thoại của Phụ huynh học sinh.")
    add_bullet_item("Bước 6", "Đầu giờ học, Giáo viên chủ nhiệm mở bảng điểm danh lớp, rà soát danh sách vắng mặt để đối chiếu với các đơn nghỉ phép đã được duyệt.")

    add_subsec_title("2. Quy trình xử lý khiếu nại hai cấp (Two-Level Dispute Workflow)")
    add_p("Nhằm đảm bảo tính minh bạch, công bằng và tôn trọng quyền lợi của học sinh, hệ thống thiết lập quy trình giải quyết phản ánh nề nếp theo mô hình 2 cấp chặt chẽ:")
    add_bullet_item("Cấp 1 - Xử lý tại lớp (Giáo viên chủ nhiệm)", "Học sinh hoặc Phụ huynh khởi tạo đơn khiếu nại đối với một bản ghi điểm danh bị nghi ngờ sai lệch. Giáo viên chủ nhiệm tiếp nhận đơn, kiểm tra tính xác thực. Nếu khiếu nại đúng, Giáo viên bấm 'Chấp thuận' để tự động hiệu chỉnh bản ghi. Nếu nhận thấy trường hợp phức tạp cần xem xét bằng chứng trích xuất từ camera, Giáo viên bấm 'Chuyển tiếp lên Giám thị'.")
    add_bullet_item("Cấp 2 - Thẩm định tại trường (Giám thị)", "Giám thị tiếp nhận hồ sơ khiếu nại đã chuyển tiếp từ Cấp 1. Giám thị mở kho lưu trữ ảnh gốc trích xuất từ camera trạm biên tại thời điểm xảy ra sự việc để thẩm định độc lập. Giám thị đưa ra phán quyết cuối cùng (Chấp thuận hiệu chỉnh hoặc Giữ nguyên bản ghi vi phạm). Phán quyết của Giám thị là kết luận có hiệu lực thi hành để tính điểm thi đua cuối tuần.")

    # --- PHẦN V: ĐÁNH GIÁ CÁC PHẦN ĐÃ LÀM ĐƯỢC VÀ CẦN PHÁT TRIỂN ---
    add_sec_title("PHẦN V. ĐÁNH GIÁ CÁC KẾT QUẢ ĐÃ ĐẠT ĐƯỢC VÀ NHỮNG NỘI DUNG CẦN TIẾP TỤC PHÁT TRIỂN")

    add_subsec_title("1. Những kết quả nổi bật đã hoàn thành (Các phần đã làm được)")
    add_p("Trong quá trình nghiên cứu, thiết kế và triển khai thử nghiệm, hệ thống đã hoàn thành trọn vẹn các mục tiêu kỹ thuật và nghiệp vụ trọng tâm sau đây:")
    add_bullet_item("Kiến trúc Đa trường học (Multi-Tenant SaaS)", "Đã xây dựng thành công mô hình phần mềm dịch vụ cho phép một máy chủ duy nhất có thể phân vùng dữ liệu an toàn để phục vụ đồng thời nhiều cơ sở giáo dục khác nhau. Mỗi trường học sở hữu một không gian dữ liệu độc lập (Tenant Isolation), cấu hình quy định và hệ sinh thái tài khoản riêng biệt.")
    add_bullet_item("Phân hệ Máy chủ Hiệu năng cao (FastAPI Backend)", "Đã lập trình hoàn chỉnh hệ thống RESTful API kết hợp WebSockets với tốc độ phản hồi tính bằng mili-giây. Tích hợp đầy đủ các tiêu chuẩn bảo mật dữ liệu: cơ chế băm mật khẩu PBKDF2 với muối ngẫu nhiên (Salt), xác thực an toàn bằng JWT Token, kiểm soát tần suất truy cập (Rate Limiting) và danh sách đen thu hồi phiên làm việc (Token Blacklist).")
    add_bullet_item("Phân hệ Thị giác máy tính và AI Biên (Edge Station)", "Đã phát triển và làm chủ module camera AI chạy độc lập trên phần cứng nhúng phổ thông (Raspberry Pi / máy tính mini). Đạt độ chính xác nhận diện khuôn mặt trên 95% ở cự ly 1.5m - 4m. Thuật toán chống giả mạo (Anti-spoofing) ngăn chặn hiệu quả hành vi gian lận bằng hình ảnh in ấn hoặc màn hình điện thoại.")
    add_bullet_item("Giải pháp AI Lai kiểm tra đồng phục (Hybrid AI Uniform Check)", "Sáng tạo trong việc kết hợp linh hoạt giữa phân tích không gian màu HSV (cho trang phục có đặc trưng màu rõ ràng như áo trắng, áo Đoàn) và mạng nơ-ron tích chập TFLite MobileNetV2 (cho trang phục có họa tiết phức tạp như áo truyền thống, áo dân tộc). Giải pháp này giúp giảm tải từ 60% đến 70% tài nguyên xử lý CPU so với việc dùng mô hình học sâu toàn phần.")
    add_bullet_item("Kiến trúc Hoạt động Ngoại tuyến (Offline-First Resilience)", "Trạm camera tại cổng duy trì hoạt động hoàn toàn bình thường ngay cả khi mất kết nối Internet nhờ bộ nhớ đệm SQLite cục bộ. Cơ chế tự động đồng bộ bù (Auto Re-sync) bảo đảm tỷ lệ toàn vẹn dữ liệu đạt 100%, không bị mất mát bản ghi điểm danh trong bất kỳ tình huống gián đoạn mạng nào.")
    add_bullet_item("Phân hệ Ứng dụng Web Dashboard Đa chức năng", "Xây dựng giao diện Web tương tác đáp ứng (Responsive), tích hợp đầy đủ bảng điều hành thời gian thực (Executive Dashboard) cho Ban Giám hiệu, màn hình giám sát trực tiếp (Live Feed) cho Giám thị, các module quản lý lớp học, phê duyệt ảnh sinh trắc học, quản lý đơn xin nghỉ và giải quyết khiếu nại nề nếp.")
    add_bullet_item("Phân hệ Ứng dụng Di động (Flutter Mobile App)", "Đã phát triển ứng dụng di động đa nền tảng (Android/iOS) cho Phụ huynh và Học sinh, cung cấp tính năng hiển thị mã QR định danh dự phòng, tra cứu lịch sử chuyên cần cá nhân và tiếp nhận thông báo điểm danh kèm ảnh bằng chứng tức thời.")
    add_bullet_item("Hệ thống Quy trình Nghiệp vụ Số hóa Hoàn chỉnh", "Thiết lập thành công quy trình điểm danh phối hợp 6 bước và quy trình giải quyết khiếu nại 2 cấp minh bạch (Cấp 1 tại Giáo viên chủ nhiệm, Cấp 2 tại Giám thị), giúp giảm thiểu tối đa các xung đột và sai sót nề nếp trong trường học.")
    add_bullet_item("Tuân thủ Pháp lý về Dữ liệu Sinh trắc học", "Đã tích hợp đầy đủ quy trình xác nhận thỏa thuận đồng thuận sinh trắc học của phụ huynh và chức năng xóa dữ liệu theo yêu cầu (Right to Erasure) theo đúng quy định tại Nghị định số 13/2023/NĐ-CP của Chính phủ về bảo vệ dữ liệu cá nhân.")

    add_subsec_title("2. Những hạn chế tồn tại và định hướng nghiên cứu phát triển (Các phần cần phát triển)")
    add_p("Bên cạnh các thành quả đã đạt được, thông qua quá trình đánh giá kỹ thuật chuyên sâu và kiểm thử tải thực tế, nhóm nghiên cứu đã xác định các hạn chế kỹ thuật hiện hữu và đề ra kế hoạch nâng cấp cụ thể:")
    add_bullet_item("Nâng cấp Cơ sở dữ liệu cho Môi trường Siêu tải", "Hạn chế hiện tại: SQLite đang được sử dụng ở chế độ WAL phù hợp cho các trường quy mô vừa và nhỏ, tuy nhiên vẫn có giới hạn ghi đơn luồng (Single Writer), tiềm ẩn nguy cơ khóa cơ sở dữ liệu (Database is locked) khi nhiều trạm camera đồng thời gửi dữ liệu giờ cao điểm. Định hướng: Chuyển đổi toàn diện sang hệ quản trị cơ sở dữ liệu phân tán PostgreSQL (kết hợp thư viện bất đồng bộ AsyncPG) để phục vụ quy mô hàng chục nghìn học sinh và hàng trăm trạm camera song song.")
    add_bullet_item("Tái cấu trúc Mã nguồn Giao diện Web (Frontend Modularization)", "Hạn chế hiện tại: Tệp giao diện Web Dashboard (index.html) đang được tổ chức theo dạng nguyên khối lớn (Monolithic), gộp toàn bộ logic giao diện của cả 5 vai trò vào một tệp duy nhất, gây khó khăn cho việc bảo trì, tối ưu mã nguồn và kiểm thử tự động. Định hướng: Tách rời giao diện thành các thành phần độc lập (Component-based architecture) dựa trên các bộ khung hiện đại như React hoặc Vue, đóng gói mã nguồn và tối ưu hóa tải trang qua công cụ Vite.")
    add_bullet_item("Nâng cấp Thị giác máy tính nhận diện Chi tiết Trang phục", "Hạn chế hiện tại: Hệ thống hiện tại đang bỏ qua (Skip) việc kiểm tra đồng phục tự do có cổ áo (như quy định Thứ Tư) do phân tích màu sắc không thể xác định cấu trúc hình học của cổ áo; chưa nhận diện được phù hiệu trường hoặc khăn quàng đỏ. Định hướng: Nghiên cứu tích hợp mô hình ước lượng tư thế người (Human Pose Estimation) và mạng nhận diện vật thể nhỏ (YOLOv8-Nano) nhằm phát hiện chính xác cổ áo, bảng tên và phù hiệu trường thêu tay.")
    add_bullet_item("Nâng cấp Công nghệ Chống Giả mạo Đa tầng (Advanced Anti-Spoofing)", "Hạn chế hiện tại: Thuật toán chống giả mạo hiện tại dựa trên kiểm tra chớp mắt và vi chuyển động quang học (Optical Flow), có thể bị ảnh hưởng nếu học sinh di chuyển quá nhanh hoặc điều kiện ánh sáng tại cổng quá tối. Định hướng: Nâng cấp lên mô hình Silent-Face-Anti-Spoofing chuyên dụng hoặc tích hợp cảm biến đo chiều sâu quang học 3D (3D Depth Camera) để triệt tiêu hoàn toàn nguy cơ giả mạo bằng mặt nạ silicon hoặc video phân giải cao.")
    add_bullet_item("Hoàn thiện Hạ tầng Xác thực Di động Thương mại", "Hạn chế hiện tại: Cơ chế xác thực mã OTP đăng ký số điện thoại đang hoạt động ở chế độ mô phỏng nội bộ máy chủ, chưa liên kết với cổng viễn thông bên ngoài. Định hướng: Tích hợp dịch vụ tin nhắn thương hiệu SMS Brandname để gửi mã OTP xác minh số điện thoại chính chủ cho phụ huynh khi liên kết hồ sơ học sinh.")
    add_bullet_item("Đồng nhất Kiến trúc Tầng Dữ liệu Ứng dụng Di động", "Hạn chế hiện tại: Ứng dụng Flutter hiện đang sử dụng song song hai luồng dữ liệu (FastAPI Backend và Firebase Firestore), gây phân tán trong việc quản trị dữ liệu. Định hướng: Chuẩn hóa toàn bộ ứng dụng di động về một nguồn dữ liệu duy nhất (Single Source of Truth) từ Backend FastAPI, đồng thời sử dụng Firebase Cloud Messaging (FCM) chuyên trách duy nhất cho tác vụ đẩy thông báo nền tức thời.")

    # --- PHẦN VI: KẾT LUẬN VÀ KIẾN NGHỊ ---
    add_sec_title("PHẦN VI. KẾT LUẬN VÀ KIẾN NGHỊ")

    add_subsec_title("1. Đánh giá tổng kết")
    add_p("Hệ thống Điểm danh Thông minh STEM (Edusams STEM) đã hiện thực hóa thành công một giải pháp công nghệ giáo dục toàn diện, kết hợp hài hòa giữa phần cứng nhúng chi phí thấp, thuật toán trí tuệ nhân tạo biên hiệu năng cao và nền tảng máy chủ dịch vụ hiện đại. Dự án giải quyết xuất sắc bài toán thực tiễn tại trường học Việt Nam: tiết kiệm thời gian giảng dạy, minh bạch hóa nề nếp thi đua, tăng cường sợi dây liên kết giữa gia đình và nhà trường, đồng thời bảo đảm nghiêm ngặt quyền riêng tư dữ liệu theo quy định của pháp luật.")

    add_subsec_title("2. Kiến nghị triển khai")
    add_p("Nhóm nghiên cứu kính đề nghị Ban Giám hiệu nhà trường và các đơn vị chuyên môn:")
    add_bullet_item("Về hạ tầng", "Tiếp tục tạo điều kiện bố trí vị trí lắp đặt trạm camera cố định tại cổng trường với điều kiện ánh sáng ổn định, bảo đảm nguồn điện và đường truyền mạng phục vụ công tác thử nghiệm mở rộng.")
    add_bullet_item("Về dữ liệu", "Phối hợp với Giáo viên chủ nhiệm các khối lớp đôn đốc học sinh và phụ huynh hoàn tất việc đăng ký ảnh chân dung chuẩn và ký xác nhận thỏa thuận đồng thuận sinh trắc học trước thềm năm học mới.")
    add_bullet_item("Về phát triển", "Bố trí nguồn lực hỗ trợ nhóm kỹ thuật tiếp tục hoàn thiện giai đoạn 2 của dự án theo đúng lộ trình nâng cấp kỹ thuật đã nêu tại Phần V.")

    # --- CHỮ KÝ VÀ NƠI NHẬN ---
    footer_table = doc.add_table(rows=1, cols=2)
    footer_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    footer_table.autofit = False

    c_l = footer_table.cell(0, 0)
    c_r = footer_table.cell(0, 1)
    c_l.width = Cm(8.0)
    c_r.width = Cm(8.0)

    p_fl = c_l.paragraphs[0]
    p_fl.paragraph_format.line_spacing = 1.2
    p_fl.paragraph_format.space_after = Pt(2)
    r = p_fl.add_run("Nơi nhận:\n")
    format_run(r, bold=True, italic=True, size=12)
    r = p_fl.add_run("- Ban Giám hiệu nhà trường;\n")
    format_run(r, size=11.5)
    r = p_fl.add_run("- Tổ Giám thị và Quản lý nề nếp;\n")
    format_run(r, size=11.5)
    r = p_fl.add_run("- Hội đồng Giáo viên chủ nhiệm;\n")
    format_run(r, size=11.5)
    r = p_fl.add_run("- Ban Đại diện Cha mẹ học sinh;\n")
    format_run(r, size=11.5)
    r = p_fl.add_run("- Lưu: Hồ sơ Kỹ thuật Dự án.")
    format_run(r, size=11.5)

    p_fr = c_r.paragraphs[0]
    p_fr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fr.paragraph_format.line_spacing = 1.2
    p_fr.paragraph_format.space_after = Pt(2)
    r = p_fr.add_run("ĐẠI DIỆN BỘ PHẬN NGHIÊN CỨU & PHÁT TRIỂN\n")
    format_run(r, bold=True, size=12.5)
    r = p_fr.add_run("(Ký, ghi rõ họ tên)\n\n\n\n\n")
    format_run(r, italic=True, size=12)
    r = p_fr.add_run("BAN DỰ ÁN PHẦN MỀM STEM")
    format_run(r, bold=True, size=13)

    # Lưu file
    download_folder = os.path.expanduser('~/Bản tải về')
    if not os.path.exists(download_folder):
        os.makedirs(download_folder, exist_ok=True)
        
    out_path_1 = os.path.join(download_folder, "BAO_CAO_TONG_HOP_CHUC_NANG_HE_THONG_STEM.docx")
    out_path_2 = "/home/minhphuc/Diem-danh-STEM/docs/reports/BAO_CAO_TONG_HOP_CHUC_NANG_HE_THONG_STEM.docx"

    doc.save(out_path_1)
    doc.save(out_path_2)
    print(f"Cap nhat file docx thanh cong:\n1. {out_path_1}\n2. {out_path_2}")

if __name__ == "__main__":
    create_full_report()
