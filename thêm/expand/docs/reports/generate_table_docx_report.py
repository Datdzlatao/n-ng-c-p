import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os

def create_table_report():
    doc = Document()

    # Cấu hình lề trang theo Nghị định 30/2020/NĐ-CP (khổ dọc A4: 21 x 29.7 cm)
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
    normal_style.paragraph_format.line_spacing = 1.3
    normal_style.paragraph_format.space_after = Pt(4)
    normal_style.paragraph_format.space_before = Pt(0)

    def format_run(r, bold=False, italic=False, size=14, color=RGBColor(0, 0, 0)):
        r.font.name = 'Times New Roman'
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.color.rgb = color

    # Tiêu đề báo cáo
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(4)
    r_title = p_title.add_run("BẢNG TỔNG HỢP TOÀN BỘ CHỨC NĂNG, KHẢ NĂNG, NHIỆM VỤ\nVÀ CÁCH SỬ DỤNG CỦA TỪNG VAI TRÒ TRONG HỆ THỐNG ĐIỂM DANH STEM")
    format_run(r_title, bold=True, size=15)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(14)
    r_sub = p_sub.add_run("(Hệ thống Điểm danh Thông minh & Quản trị Nề nếp Học đường Edusams STEM)")
    format_run(r_sub, italic=True, size=13.5)

    # Định nghĩa cấu trúc dữ liệu cho bảng
    # 5 cột: STT (1.0cm), Vai trò (3.0cm), Nhiệm vụ (3.2cm), Chức năng & Khả năng (4.4cm), Cách sử dụng (4.4cm) -> Tổng 16.0cm
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
            "Quản trị viên\nNền tảng\n(Platform Super Admin)",
            "Quản trị hạ tầng công nghệ toàn bộ hệ sinh thái đa trường học (Multi-Tenant SaaS); cấp phát tài nguyên, kích hoạt máy chủ trường và bảo đảm an toàn dữ liệu.",
            "- Khởi tạo, kích hoạt hoặc tạm dừng hoạt động các trường học (ACTIVE/SUSPENDED).\n"
            "- Giám sát tổng số trường, tổng học sinh và lưu lượng điểm danh toàn sàn.\n"
            "- Quản lý bảo mật: Chặn IP nghi vấn, kiểm soát danh sách đen Token (Token Blacklist), giới hạn tần suất truy cập.\n"
            "- Cấp tài khoản quản trị viên ban đầu cho Ban Giám hiệu từng trường.",
            "Bước 1: Đăng nhập tại cổng 'Admin Nền tảng' bằng tài khoản quản trị cấp cao.\n"
            "Bước 2: Vào danh mục trường học, chọn 'Thêm trường mới', nhập mã trường, địa chỉ, niên khóa.\n"
            "Bước 3: Chọn 'Phê duyệt' để khởi tạo máy chủ trường độc lập.\n"
            "Bước 4: Giám sát biểu đồ lưu lượng và kiểm tra nhật ký hệ thống."
        ),
        (
            "2",
            "Hiệu trưởng /\nBan Giám hiệu\n(Headmaster)",
            "Đại diện Hội đồng sư phạm quản trị toàn diện trường học trên môi trường số; ban hành quy chuẩn thời gian, đồng phục; quản lý thiết bị camera và phê duyệt bảng điểm thi đua.",
            "- Cấu hình quy định trường: Thiết lập giờ vào cổng, mốc tính muộn, mốc tính vắng.\n"
            "- Cấu hình đồng phục theo lịch tuần (áo trắng, áo Đoàn, áo truyền thống/dân tộc).\n"
            "- Quản lý trạm Camera AI: Khởi tạo trạm, cấp phát mã khóa bí mật (Secret Key) cho máy Raspberry Pi tại cổng.\n"
            "- Quản lý cơ cấu: Thiết lập danh sách lớp và chỉ định Giáo viên chủ nhiệm.\n"
            "- Xem bảng điều khiển điều hành (Executive Dashboard) thời gian thực.\n"
            "- Phê duyệt bảng điểm thi đua nề nếp tuần giữa các lớp.",
            "Bước 1: Đăng nhập tài khoản Hiệu trưởng.\n"
            "Bước 2: Vào 'Cấu hình trường' cài đặt khung giờ điểm danh và chọn lịch đồng phục cho từng ngày trong tuần.\n"
            "Bước 3: Vào 'Trạm Camera', bấm 'Thêm trạm' (ví dụ: Camera Cổng Chính), sao chép mã Secret Key cài vào máy biên.\n"
            "Bước 4: Vào 'Quản lý Lớp' phân công GVCN.\n"
            "Bước 5: Cuối tuần vào 'Thi đua' xem xét và bấm 'Phê duyệt bảng điểm'."
        ),
        (
            "3",
            "Giám thị /\nCán bộ Nề nếp\n(Inspector)",
            "Trực tiếp giám sát nề nếp tại hiện trường cổng trường; điều phối các tình huống bất thường; xử lý khiếu nại cấp cao và chấm điểm thi đua nề nếp hàng tuần.",
            "- Màn hình giám sát trực tiếp (Live Feed): Theo dõi luồng điểm danh thời gian thực, xem ảnh chụp đối chiếu tại cổng.\n"
            "- Điểm danh bổ sung hoặc ghi nhận vi phạm thủ công cho trường hợp đặc biệt.\n"
            "- Xử lý khiếu nại Cấp 2: Tiếp nhận đơn do GVCN chuyển lên, xem xét ảnh gốc từ camera để đưa ra phán quyết cuối cùng.\n"
            "- Chấm điểm thi đua nề nếp tuần: Tự động tổng hợp điểm chuyên cần, trừ lỗi đồng phục, cộng điểm phong trào cho từng lớp.\n"
            "- Phát thông báo cảnh báo nề nếp toàn trường.",
            "Bước 1: Đăng nhập tài khoản Giám thị.\n"
            "Bước 2: Mở 'Điểm danh' chế độ 'Giám sát trực tiếp' vào đầu giờ sáng để theo dõi học sinh qua cổng.\n"
            "Bước 3: Nếu phát hiện vi phạm hoặc lỗi nhận diện, bấm vào bản ghi để kiểm tra ảnh phóng to và hiệu chỉnh.\n"
            "Bước 4: Vào 'Khiếu nại', lọc đơn Cấp 2, thẩm định ảnh gốc và chọn 'Chấp thuận' hoặc 'Từ chối'.\n"
            "Bước 5: Cuối tuần vào 'Thi đua', bấm 'Tính điểm tự động' và gửi Ban Giám hiệu duyệt."
        ),
        (
            "4",
            "Giáo viên\nChủ nhiệm\n(Homeroom Teacher)",
            "Quản lý toàn diện học sinh của lớp phụ trách; kiểm soát tính chính xác dữ liệu sinh trắc học đầu vào; phê duyệt đơn xin nghỉ phép và giải quyết khiếu nại nề nếp ban đầu.",
            "- Quản lý hồ sơ học sinh lớp chủ nhiệm và tài khoản liên kết của phụ huynh.\n"
            "- Kiểm duyệt ảnh khuôn mặt mẫu (Biometric Approval): Thẩm định ảnh chân dung học sinh gửi lên trước khi trích xuất vector 128D.\n"
            "- Quản lý đơn xin nghỉ phép: Tiếp nhận đơn trực tuyến của phụ huynh, bấm duyệt để tự động ghi nhận 'Nghỉ có phép'.\n"
            "- Giải quyết khiếu nại Cấp 1: Xem xét phản ánh của học sinh lớp mình, hiệu chỉnh bản ghi hoặc chuyển lên Giám thị.\n"
            "- Theo dõi sĩ số thời gian thực: Xem danh sách học sinh đã vào trường hoặc vắng mặt ngay đầu giờ học.",
            "Bước 1: Đăng nhập tài khoản Giáo viên.\n"
            "Bước 2: Vào 'Học sinh' mục 'Chờ duyệt ảnh', kiểm tra ảnh chân dung học sinh gửi lên; bấm 'Duyệt ảnh' nếu rõ nét.\n"
            "Bước 3: Vào 'Đơn nghỉ phép', đọc đơn của phụ huynh và bấm 'Phê duyệt' để tự động cập nhật sổ điểm danh.\n"
            "Bước 4: Vào 'Khiếu nại', giải quyết đơn của học sinh lớp mình; chọn 'Chấp thuận' hoặc 'Chuyển lên Giám thị'.\n"
            "Bước 5: Đầu giờ vào 'Điểm danh' kiểm tra danh sách vắng mặt của lớp."
        ),
        (
            "5",
            "Phụ huynh\nHọc sinh\n(Parent)",
            "Phối hợp với nhà trường giám sát việc chuyên cần và rèn luyện của con; ký xác nhận thỏa thuận đồng thuận sinh trắc học; nộp đơn xin nghỉ phép trực tuyến.",
            "- Nhận thông báo điểm danh tức thời trên điện thoại ngay khi con qua cổng trường, kèm ảnh chụp thực tế tại hiện trường.\n"
            "- Tra cứu lịch sử chuyên cần, giờ đến trường, trạng thái đồng phục hàng ngày của con.\n"
            "- Nộp đơn xin nghỉ phép trực tuyến kèm lý do chính đáng mà không cần viết đơn giấy.\n"
            "- Quản lý đồng thuận sinh trắc học (Nghị định 13/2023/NĐ-CP): Ký hoặc thu hồi quyền thu thập dữ liệu khuôn mặt của con.\n"
            "- Gửi khiếu nại khi phát hiện kết quả ghi nhận điểm danh có sai sót.",
            "Bước 1: Cài đặt ứng dụng di động, đăng ký bằng số điện thoại đã cung cấp cho trường và liên kết mã học sinh của con.\n"
            "Bước 2: Vào mục hồ sơ, đọc quy định và bấm 'Xác nhận đồng thuận' sinh trắc học.\n"
            "Bước 3: Xem thông báo tự động mỗi sáng kèm ảnh chụp khi con bước qua cổng trường.\n"
            "Bước 4: Khi cần xin nghỉ, vào 'Đơn nghỉ phép', bấm 'Tạo đơn mới', chọn ngày, nhập lý do và bấm 'Gửi đơn'.\n"
            "Bước 5: Theo dõi kết quả phê duyệt của GVCN ngay trên ứng dụng."
        ),
        (
            "6",
            "Học sinh\n(Student)",
            "Tự giác thực hiện điểm danh không chạm khi đến trường; chấp hành nghiêm túc quy định đồng phục; chủ động theo dõi chuyên cần và thẻ QR dự phòng.",
            "- Điểm danh tự động qua camera nhận diện khuôn mặt tại cổng trường (tốc độ 0.2 - 0.5 giây/lượt, quét cùng lúc 2 - 3 bạn).\n"
            "- Sử dụng thẻ mã QR định danh cá nhân trên điện thoại làm phương án điểm danh dự phòng khi cần thiết.\n"
            "- Tự tải ảnh chân dung mẫu qua điện thoại gửi Giáo viên chủ nhiệm kiểm duyệt.\n"
            "- Tra cứu lịch sử điểm danh, điểm nề nếp thi đua cá nhân.\n"
            "- Gửi đơn khiếu nại nề nếp Cấp 1 tới GVCN nếu bị ghi nhận sai thời gian hoặc lỗi đồng phục.",
            "Bước 1: Đăng nhập tài khoản Học sinh trên điện thoại, vào mục hồ sơ tải ảnh chân dung rõ nét gửi GVCN duyệt.\n"
            "Bước 2: Điểm danh hàng ngày: Đi qua cổng trường trong tầm nhìn camera (tốc độ đi bộ bình thường 1 - 2 giây).\n"
            "Bước 3: Dự phòng: Mở mục 'Thẻ QR cá nhân' trên ứng dụng để quét trước camera nếu có sự cố mạng hoặc ánh sáng.\n"
            "Bước 4: Nếu bị chấm muộn do hệ thống, vào 'Khiếu nại nề nếp', chọn bản ghi, ghi giải trình và bấm 'Gửi khiếu nại'."
        )
    ]

    # Tạo bảng
    table = doc.add_table(rows=len(roles_data) + 1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Header row
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

    # Data rows
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

    # Kẻ viền cho bảng
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

    # Lưu file
    download_folder = os.path.expanduser('~/Bản tải về')
    if not os.path.exists(download_folder):
        os.makedirs(download_folder, exist_ok=True)
        
    out_path_1 = os.path.join(download_folder, "BANG_TONG_HOP_CHUC_NANG_VA_VAI_TRO_STEM.docx")
    out_path_2 = "/home/minhphuc/Diem-danh-STEM/docs/reports/BANG_TONG_HOP_CHUC_NANG_VA_VAI_TRO_STEM.docx"

    doc.save(out_path_1)
    doc.save(out_path_2)
    print(f"Tao file docx dang bang thanh cong:\n1. {out_path_1}\n2. {out_path_2}")

if __name__ == "__main__":
    create_table_report()
