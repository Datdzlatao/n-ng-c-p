import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os

def create_combined_report():
    doc = Document()

    # Cấu hình lề trang theo Nghị định 30/2020/NĐ-CP (Khổ A4 dọc: 21.0 x 29.7 cm)
    # Lề trái 3.0cm, phải 2.0cm, trên 2.0cm, dưới 2.0cm -> Chiều rộng nội dung: 16.0cm
    for s in doc.sections:
        s.top_margin = Cm(2.0)
        s.bottom_margin = Cm(2.0)
        s.left_margin = Cm(3.0)
        s.right_margin = Cm(2.0)
        s.page_width = Cm(21.0)
        s.page_height = Cm(29.7)

    # Cấu hình style mặc định: Times New Roman, 14pt
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(14)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.35
    normal_style.paragraph_format.space_after = Pt(5)
    normal_style.paragraph_format.space_before = Pt(0)

    def format_run(r, bold=False, italic=False, size=14, color=RGBColor(0, 0, 0)):
        r.font.name = 'Times New Roman'
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.color.rgb = color

    def add_p(text="", align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True, bold=False, italic=False, size=14, space_before=0, space_after=5):
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
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.line_spacing = 1.35
        r = p.add_run(text)
        format_run(r, bold=True, size=14.5)
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

    # --- PHẦN TIÊU ĐỀ ĐẦU TRANG THEO THỂ THỨC HÀNH CHÍNH ---
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
    r = p_l.add_run("Số: 04/BC-STEM")
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

    # Tiêu đề báo cáo
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(12)
    p_title.paragraph_format.space_after = Pt(4)
    r_title = p_title.add_run("BÁO CÁO TỔNG HỢP VẬN HÀNH HỆ THỐNG ĐIỂM DANH STEM:\nCHỨC NĂNG CÁC VAI TRÒ VÀ ĐÁNH GIÁ PHÁT TRIỂN")
    format_run(r_title, bold=True, size=15)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(14)
    r_sub = p_sub.add_run("(Tổng hợp ma trận chức năng từng vai trò kết hợp đánh giá kết quả thực hiện và định hướng nâng cấp)")
    format_run(r_sub, italic=True, size=13.5)

    # --- PHẦN 1: BẢNG TỔNG HỢP CÁC VAI TRÒ ---
    add_sec_title("PHẦN I. BẢNG TỔNG HỢP CHỨC NĂNG, KHẢ NĂNG, NHIỆM VỤ VÀ CÁCH SỬ DỤNG TỪNG VAI TRÒ")

    headers = [
        "STT",
        "Vai trò\n(Role)",
        "Nhiệm vụ\nchính",
        "Chức năng &\nKhả năng cốt lõi",
        "Cách sử dụng\n(Quy trình thao tác)"
    ]
    col_widths = [Cm(1.0), Cm(3.0), Cm(3.3), Cm(4.3), Cm(4.4)]

    roles_data = [
        (
            "1",
            "Quản trị viên\nNền tảng\n(Platform Admin)",
            "Quản trị hạ tầng công nghệ toàn bộ hệ thống đa trường học (SaaS); cấp phát tài nguyên, kích hoạt máy chủ trường và bảo đảm an toàn dữ liệu.",
            "- Khởi tạo, kích hoạt hoặc tạm dừng hoạt động máy chủ các trường (ACTIVE/SUSPENDED).\n"
            "- Giám sát tổng số trường, tổng học sinh và lưu lượng điểm danh toàn sàn.\n"
            "- Quản lý bảo mật: Chặn IP nghi vấn, kiểm soát danh sách đen Token, chống quá tải hệ thống.\n"
            "- Cấp tài khoản quản trị ban đầu cho Ban Giám hiệu từng trường.",
            "Bước 1: Đăng nhập tại cổng 'Admin Nền tảng' bằng tài khoản quản trị cấp cao.\n"
            "Bước 2: Vào danh mục trường học, chọn 'Thêm trường mới', nhập thông tin trường.\n"
            "Bước 3: Chọn 'Phê duyệt' để kích hoạt máy chủ trường độc lập.\n"
            "Bước 4: Giám sát lưu lượng máy chủ trên biểu đồ thời gian thực."
        ),
        (
            "2",
            "Hiệu trưởng /\nBan Giám hiệu\n(Headmaster)",
            "Đại diện Hội đồng sư phạm quản trị toàn diện trường học trên môi trường số; ban hành quy chuẩn thời gian, đồng phục; quản lý camera và duyệt thi đua.",
            "- Cấu hình quy định trường: Giờ mở cổng, mốc tính muộn, mốc tính vắng mặt.\n"
            "- Cấu hình đồng phục theo lịch tuần (áo trắng, áo Đoàn, áo truyền thống/dân tộc).\n"
            "- Quản lý trạm Camera AI: Tạo trạm, cấp mã bí mật (Secret Key) cài vào máy Raspberry Pi.\n"
            "- Quản lý cơ cấu: Thiết lập danh sách lớp và phân công Giáo viên chủ nhiệm.\n"
            "- Theo dõi bảng điều hành (Dashboard) sĩ số thời gian thực.\n"
            "- Phê duyệt bảng điểm thi đua nề nếp tuần giữa các lớp.",
            "Bước 1: Đăng nhập tài khoản Hiệu trưởng.\n"
            "Bước 2: Vào 'Cấu hình trường' cài đặt giờ điểm danh và chọn lịch đồng phục trong tuần.\n"
            "Bước 3: Vào 'Trạm Camera', bấm 'Thêm trạm' (ví dụ: Camera Cổng Chính), lấy mã Secret Key.\n"
            "Bước 4: Vào 'Quản lý Lớp' phân công GVCN phụ trách.\n"
            "Bước 5: Cuối tuần vào 'Thi đua' xem xét và bấm 'Phê duyệt bảng điểm'."
        ),
        (
            "3",
            "Giám thị /\nCán bộ Nề nếp\n(Inspector)",
            "Trực tiếp giám sát nề nếp tại hiện trường cổng trường; điều phối các tình huống bất thường; xử lý khiếu nại cấp cao và chấm thi đua nề nếp tuần.",
            "- Giám sát trực tiếp (Live Feed): Theo dõi luồng học sinh qua cổng, xem ảnh chụp đối chiếu.\n"
            "- Điểm danh bổ sung hoặc ghi nhận vi phạm thủ công cho trường hợp đặc biệt.\n"
            "- Xử lý khiếu nại Cấp 2: Thẩm định hồ sơ GVCN chuyển lên, xem ảnh gốc camera để phán quyết.\n"
            "- Chấm thi đua nề nếp tuần: Tự động tổng hợp điểm chuyên cần, trừ lỗi đồng phục, cộng điểm phong trào.\n"
            "- Phát thông báo cảnh báo nề nếp toàn trường.",
            "Bước 1: Đăng nhập tài khoản Giám thị.\n"
            "Bước 2: Mở 'Điểm danh' chế độ 'Giám sát trực tiếp' vào đầu giờ sáng để theo dõi học sinh qua cổng.\n"
            "Bước 3: Bấm vào bản ghi để phóng to ảnh kiểm tra nếu phát hiện vi phạm hoặc lỗi nhận diện.\n"
            "Bước 4: Vào 'Khiếu nại', lọc đơn Cấp 2, thẩm định ảnh gốc và bấm 'Chấp thuận' hoặc 'Từ chối'.\n"
            "Bước 5: Cuối tuần vào 'Thi đua', bấm 'Tính điểm tự động' và gửi Ban Giám hiệu duyệt."
        ),
        (
            "4",
            "Giáo viên\nChủ nhiệm\n(Homeroom Teacher)",
            "Quản lý toàn diện học sinh của lớp phụ trách; kiểm soát tính chính xác dữ liệu sinh trắc học đầu vào; phê duyệt đơn xin nghỉ phép và giải quyết khiếu nại Cấp 1.",
            "- Quản lý danh sách học sinh lớp và tài khoản liên kết phụ huynh.\n"
            "- Duyệt ảnh khuôn mặt mẫu: Thẩm định ảnh chân dung học sinh gửi lên trước khi trích xuất vector AI.\n"
            "- Quản lý đơn xin nghỉ phép: Duyệt đơn trực tuyến của phụ huynh để tự động ghi nhận 'Nghỉ có phép'.\n"
            "- Giải quyết khiếu nại Cấp 1: Xem xét phản ánh của học sinh lớp mình, sửa lỗi hoặc chuyển lên Giám thị.\n"
            "- Theo dõi sĩ số thời gian thực: Nắm bắt chính xác học sinh có mặt hoặc vắng mặt ngay đầu giờ.",
            "Bước 1: Đăng nhập tài khoản Giáo viên.\n"
            "Bước 2: Vào 'Học sinh' mục 'Chờ duyệt ảnh', kiểm tra ảnh chân dung học sinh gửi lên và bấm 'Duyệt'.\n"
            "Bước 3: Vào 'Đơn nghỉ phép', đọc lý do và bấm 'Phê duyệt' để tự động cập nhật sổ điểm danh.\n"
            "Bước 4: Vào 'Khiếu nại', giải quyết đơn của học sinh lớp mình; chọn 'Chấp thuận' hoặc 'Chuyển lên Giám thị'.\n"
            "Bước 5: Đầu giờ vào 'Điểm danh' kiểm tra danh sách vắng mặt của lớp."
        ),
        (
            "5",
            "Phụ huynh\nHọc sinh\n(Parent)",
            "Phối hợp với nhà trường giám sát việc chuyên cần và rèn luyện của con; ký xác nhận thỏa thuận đồng thuận sinh trắc học; nộp đơn xin nghỉ phép trực tuyến.",
            "- Nhận thông báo tức thời trên điện thoại ngay khi con qua cổng, kèm ảnh chụp thực tế tại cổng.\n"
            "- Tra cứu lịch sử đi học, giờ đến trường, trạng thái đồng phục hàng ngày của con.\n"
            "- Nộp đơn xin nghỉ phép trực tuyến có đính kèm lý do mà không cần viết đơn giấy.\n"
            "- Quản lý đồng thuận sinh trắc học (Nghị định 13/2023/NĐ-CP): Ký hoặc thu hồi quyền dùng ảnh mặt của con.\n"
            "- Gửi phản ánh khi phát hiện kết quả ghi nhận điểm danh có sai sót.",
            "Bước 1: Cài ứng dụng di động, đăng ký bằng số điện thoại và liên kết mã định danh của con.\n"
            "Bước 2: Vào mục hồ sơ, đọc quy định và bấm 'Xác nhận đồng thuận' sinh trắc học.\n"
            "Bước 3: Nhận thông báo tự động mỗi sáng kèm ảnh chụp thực tế tại cổng trường.\n"
            "Bước 4: Khi cần xin nghỉ, vào 'Đơn nghỉ phép', bấm 'Tạo đơn mới', chọn ngày, nhập lý do và gửi.\n"
            "Bước 5: Theo dõi kết quả phê duyệt của GVCN trực tiếp trên ứng dụng."
        ),
        (
            "6",
            "Học sinh\n(Student)",
            "Tự giác thực hiện điểm danh không chạm khi đến trường; chấp hành nghiêm túc quy định đồng phục; chủ động theo dõi chuyên cần và thẻ QR dự phòng.",
            "- Điểm danh tự động qua camera tại cổng trường (tốc độ 0.2 - 0.5 giây/lượt, quét cùng lúc 2 - 3 bạn).\n"
            "- Sử dụng thẻ mã QR định danh cá nhân trên điện thoại làm phương án dự phòng khi cần.\n"
            "- Tự tải ảnh chân dung mẫu qua điện thoại gửi Giáo viên chủ nhiệm kiểm duyệt.\n"
            "- Tra cứu lịch sử điểm danh, điểm nề nếp thi đua cá nhân.\n"
            "- Gửi đơn khiếu nại nề nếp Cấp 1 tới GVCN nếu bị ghi nhận sai thời gian hoặc lỗi đồng phục.",
            "Bước 1: Đăng nhập tài khoản Học sinh trên điện thoại, vào mục hồ sơ tải ảnh chân dung rõ nét gửi GVCN.\n"
            "Bước 2: Điểm danh hàng ngày: Đi bộ bình thường qua cổng trường trong tầm nhìn của camera.\n"
            "Bước 3: Dự phòng: Mở mục 'Thẻ QR cá nhân' trên ứng dụng để quét trước camera nếu có sự cố.\n"
            "Bước 4: Nếu bị chấm muộn sai, vào 'Khiếu nại nề nếp', chọn bản ghi, ghi giải trình và bấm 'Gửi khiếu nại'."
        )
    ]

    table = doc.add_table(rows=len(roles_data) + 1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Header
    hdr_cells = table.rows[0].cells
    for i, h_text in enumerate(headers):
        hdr_cells[i].width = col_widths[i]
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(h_text)
        format_run(r, bold=True, size=13)
        tcPr = hdr_cells[i]._element.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="EAEAEA"/>')
        tcPr.append(shd)

    # Data
    for row_idx, row_data in enumerate(roles_data, start=1):
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
                format_run(r, bold=True, size=12.5)
            elif col_idx == 1:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(text)
                format_run(r, bold=True, size=12.5)
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                lines = text.split("\n")
                for line_idx, line in enumerate(lines):
                    if line_idx > 0:
                        p = row_cells[col_idx].add_paragraph()
                        p.paragraph_format.line_spacing = 1.2
                        p.paragraph_format.space_before = Pt(2)
                        p.paragraph_format.space_after = Pt(2)
                        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    if line.startswith("Bước") or line.startswith("- "):
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            r_b = p.add_run(parts[0] + ":")
                            format_run(r_b, bold=True, size=12)
                            r_t = p.add_run(parts[1])
                            format_run(r_t, bold=False, size=12)
                        else:
                            r_t = p.add_run(line)
                            format_run(r_t, bold=False, size=12)
                    else:
                        r_t = p.add_run(line)
                        format_run(r_t, bold=False, size=12)

    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = parse_xml(f'''
            <w:tblBorders {nsdecls("w")}>
                <w:top w:val="single" w:sz="8" w:space="0" w:color="000000"/>
                <w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/>
                <w:left w:val="single" w:sz="8" w:space="0" w:color="000000"/>
                <w:right w:val="single" w:sz="8" w:space="0" w:color="000000"/>
                <w:insideH w:val="single" w:sz="4" w:space="0" w:color="999999"/>
                <w:insideV w:val="single" w:sz="4" w:space="0" w:color="999999"/>
            </w:tblBorders>
        ''')
        tblPr[0].append(borders)

    add_p("", indent=False, space_before=6, space_after=6)

    # --- PHẦN 2: ĐÁNH GIÁ VÀ ĐỊNH HƯỚNG PHÁT TRIỂN (NGẮN GỌN, TRỌNG TÂM) ---
    add_sec_title("PHẦN II. ĐÁNH GIÁ KẾT QUẢ ĐÃ LÀM ĐƯỢC VÀ ĐỊNH HƯỚNG PHÁT TRIỂN TIẾP THEO")

    p_intro = doc.add_paragraph()
    p_intro.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_intro.paragraph_format.first_line_indent = Cm(1.27)
    p_intro.paragraph_format.space_before = Pt(4)
    p_intro.paragraph_format.space_after = Pt(6)
    r = p_intro.add_run("1. Những kết quả trọng tâm đã làm được:")
    format_run(r, bold=True, size=14)

    add_bullet_item("Kiến trúc Đa trường học (SaaS)", "Một máy chủ duy nhất phục vụ độc lập nhiều trường học; dữ liệu và cấu hình phân vùng biệt lập an toàn.")
    add_bullet_item("Tự chủ tải mẫu khuôn mặt qua điện thoại", "Học sinh tự gửi ảnh chân dung qua điện thoại cá nhân; Giáo viên chủ nhiệm trực tiếp kiểm duyệt trước khi đồng bộ nhận diện.")
    add_bullet_item("Điểm danh quét đồng thời 2 - 3 học sinh", "Camera AI tại cổng phát hiện và đối sánh song song 2 đến 3 học sinh cùng lúc (thời gian xử lý 0.2 - 0.5 giây/lượt), giải tỏa hoàn toàn ùn tắc giờ cao điểm.")
    add_bullet_item("Kiểm tra đồng phục tự động (Hybrid AI)", "Kết hợp phân tích màu sắc HSV (áo trắng, áo Đoàn) và mô hình học sâu MobileNetV2 (áo truyền thống, áo dân tộc), giảm 60% - 70% tải tính toán CPU.")
    add_bullet_item("Truyền tin thời gian thực tức thời", "Hệ thống WebSockets cập nhật ngay sĩ số cho Giáo viên chủ nhiệm và gửi thông báo kèm ảnh con vào cổng đến điện thoại Phụ huynh.")
    add_bullet_item("Hoạt động ngoại tuyến không lo mất mạng", "Trạm camera tự lưu trữ dữ liệu điểm danh vào bộ đệm SQLite khi mất mạng Internet và tự đồng bộ bù 100% khi có mạng trở lại.")
    add_bullet_item("Số hóa đơn từ và quy trình khiếu nại", "Phụ huynh nộp đơn xin nghỉ phép trực tuyến; Giáo viên duyệt trên hệ thống; quy trình giải quyết khiếu nại 2 cấp minh bạch, rõ ràng.")
    add_bullet_item("Tuân thủ pháp lý bảo vệ dữ liệu sinh trắc học", "Tích hợp văn bản đồng thuận có chữ ký của phụ huynh và quyền xóa dữ liệu theo đúng Nghị định số 13/2023/NĐ-CP.")

    p_dev = doc.add_paragraph()
    p_dev.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_dev.paragraph_format.first_line_indent = Cm(1.27)
    p_dev.paragraph_format.space_before = Pt(10)
    p_dev.paragraph_format.space_after = Pt(6)
    r = p_dev.add_run("2. Những phần trọng tâm cần tiếp tục phát triển:")
    format_run(r, bold=True, size=14)

    add_bullet_item("Chuyển đổi cơ sở dữ liệu sang PostgreSQL", "Thay thế SQLite để loại bỏ giới hạn ghi đơn luồng, tránh hiện tượng khóa cơ sở dữ liệu khi nhiều trạm camera cùng đẩy dữ liệu giờ cao điểm.")
    add_bullet_item("Nhận diện chi tiết trang phục phức tạp", "Tích hợp mô hình ước lượng tư thế người (Pose Estimation) và YOLOv8 để nhận diện áo có cổ (trang phục tự do), phù hiệu thêu tay và khăn quàng đỏ.")
    add_bullet_item("Nâng cấp bám vết khi học sinh đi nhóm đông", "Cải tiến thuật toán theo dõi chuyển động để nhận diện chính xác khi nhóm từ 4 - 5 học sinh chen chúc, che khuất nhau sát giờ đóng cổng.")
    add_bullet_item("Tái cấu trúc mô-đun hóa giao diện Web", "Chia tách tệp giao diện nguyên khối hiện tại thành các thành phần độc lập (React/Vue + Vite) để dễ dàng bảo trì và tối ưu tốc độ tải trang.")
    add_bullet_item("Đa dạng hóa kênh thông báo viễn thông", "Tích hợp dịch vụ tin nhắn SMS Brandname và Zalo ZNS nhằm bảo đảm phụ huynh không bật mạng 4G/Wifi hoặc chưa cài app vẫn nhận được thông báo tức thời.")
    add_bullet_item("Chuẩn hóa một nguồn dữ liệu duy nhất cho Mobile", "Quy hoạch ứng dụng Flutter kết nối trực tiếp về Backend FastAPI duy nhất, chuyển dịch vụ Firebase về đúng vai trò chuyên trách đẩy thông báo nền (FCM).")

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

    # Lưu file kết hợp
    download_folder = os.path.expanduser('~/Bản tải về')
    out_path_1 = os.path.join(download_folder, "BAO_CAO_TONG_HOP_TOAN_DIEN_HE_THONG_STEM.docx")
    out_path_2 = "/home/minhphuc/Diem-danh-STEM/docs/reports/BAO_CAO_TONG_HOP_TOAN_DIEN_HE_THONG_STEM.docx"

    doc.save(out_path_1)
    doc.save(out_path_2)
    print(f"File combined successfully:\n1. {out_path_1}\n2. {out_path_2}")

if __name__ == "__main__":
    create_combined_report()
