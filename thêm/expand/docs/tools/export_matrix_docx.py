# -*- coding: utf-8 -*-
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os

def set_cell_background(cell, fill_hex):
    """Set background color of a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set inner margins of a table cell in dxa (1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'''
        <w:tcMar {nsdecls("w")}>
            <w:top w:w="{top}" w:type="dxa"/>
            <w:bottom w:w="{bottom}" w:type="dxa"/>
            <w:left w:w="{left}" w:type="dxa"/>
            <w:right w:w="{right}" w:type="dxa"/>
        </w:tcMar>
    ''')
    tcPr.append(tcMar)

def set_table_borders(table, color="CCCCCC", sz="4", val="single"):
    """Set subtle modern borders on a table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(f'''
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:insideV w:val="none"/>
            <w:left w:val="none"/>
            <w:right w:val="none"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders)

def create_document():
    doc = Document()
    
    # Page setup - Margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)

    # Base Styles
    style_normal = doc.styles['Normal']
    font = style_normal.font
    font.name = 'Arial'
    font.size = Pt(10.5)
    font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # Primary Title
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(4)
    run_sub = title_p.add_run("DỰ ÁN HỆ THỐNG ĐIỂM DANH & QUẢN LÝ NỀ NẾP THÔNG MINH (STEM)\n")
    run_sub.font.size = Pt(11)
    run_sub.font.bold = True
    run_sub.font.color.rgb = RGBColor(0x00, 0x56, 0xB3)

    run_title = title_p.add_run("BẢNG TỔNG HỢP TÍNH NĂNG THEO USER & MA TRẬN PHÂN QUYỀN")
    run_title.font.size = Pt(16)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)

    # Subtitle
    sub_p = doc.add_paragraph()
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_p.paragraph_format.space_after = Pt(14)
    run_desc = sub_p.add_run("Kiến trúc Đa Trường Học (Multi-Tenant) — Phân Quyền Vai Trò & Quy Trình Nghiệp Vụ (Proceed)")
    run_desc.font.size = Pt(10)
    run_desc.font.italic = True
    run_desc.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    # Divider line
    div_p = doc.add_paragraph()
    div_p.paragraph_format.space_after = Pt(12)
    div_run = div_p.add_run("―" * 48)
    div_run.font.color.rgb = RGBColor(0xDD, 0xDD, 0xDD)
    div_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ==============================================================
    # PHẦN 1: TỔNG QUAN KIẾN TRÚC ĐA TẬP THỂ
    # ==============================================================
    h1 = doc.add_heading("I. TỔNG QUAN KIẾN TRÚC ĐA TRƯỜNG HỌC (MULTI-TENANT)", level=1)
    h1.style.font.name = 'Arial'
    h1.style.font.size = Pt(12.5)
    h1.style.font.bold = True
    h1.style.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
    h1.paragraph_format.space_before = Pt(10)
    h1.paragraph_format.space_after = Pt(6)

    p_intro = doc.add_paragraph(
        "Nhằm mở rộng quy mô từ phạm vi 1 lớp học đơn lẻ thành nền tảng quản lý chuyên cần và nề nếp dùng chung cho nhiều trường học, "
        "hệ thống áp dụng mô hình kiến trúc Đa Không Gian (Multi-Tenant Architecture). Mỗi trường học hoạt động độc lập như một 'Server trường' "
        "riêng biệt với cơ sở dữ liệu, quy chế nề nếp, danh sách giáo viên - học sinh và các trạm camera điểm danh riêng biệt."
    )
    p_intro.paragraph_format.line_spacing = 1.2
    p_intro.paragraph_format.space_after = Pt(10)

    # ==============================================================
    # PHẦN 2: CHI TIẾT TÍNH NĂNG & QUY TRÌNH (PROCEED) TỪNG USER
    # ==============================================================
    h2 = doc.add_heading("II. CHI TIẾT CHỨC NĂNG & QUY TRÌNH NGHIỆP VỤ THEO VAI TRÒ", level=1)
    h2.style.font.name = 'Arial'
    h2.style.font.size = Pt(12.5)
    h2.style.font.bold = True
    h2.style.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
    h2.paragraph_format.space_before = Pt(12)
    h2.paragraph_format.space_after = Pt(6)

    roles_data = [
        {
            "role": "1. Hiệu Trưởng / Ban Giám Hiệu (School Super Admin)",
            "desc": "Người nắm quyền cao nhất trong Server trường, sở hữu toàn quyền cấu hình và giám sát vĩ mô.",
            "caps": [
                "Khởi tạo & quản trị Server 'Trường của tôi': Đặt tên trường, mã trường, niên khóa, logo.",
                "Tùy biến Form nhập học động (Dynamic Form): Tự định nghĩa các trường dữ liệu bắt buộc đối với học sinh tham gia (Họ tên, Lớp, Mã định danh/CCCD, SĐT phụ huynh, Ảnh chân dung AI,...).",
                "Thiết lập quy chế nề nếp & khung giờ: Cài đặt giờ vào học, giờ giới nghiêm, quy định trang phục theo ngày (Thứ 2 mặc áo dài/đồng phục, Thứ 7 tự do,...), thang điểm cộng/trừ.",
                "Mời & phân quyền nhân sự: Tạo link/mã mời phân quyền cho Phó Hiệu trưởng, Giám thị, GVCN từng khối/lớp.",
                "Dashboard Thống kê Toàn trường (Executive Analytics): Tỷ lệ chuyên cần trực tiếp, bảng xếp hạng thi đua giữa các lớp, phát hiện xu hướng nề nếp chung.",
                "Xuất báo cáo tổng hợp cấp trường: Xuất báo cáo chuyên cần định dạng Excel/PDF chuẩn gửi Sở/Phòng GD&ĐT.",
                "Quản lý trạm Camera AI: Quản lý thiết bị điểm danh đặt tại Cổng chính, Cổng phụ, Căng tin, Ký túc xá."
            ],
            "proceed": "Đăng ký tài khoản → Khởi tạo Server trường → Cấu hình niên khóa & Form nhập liệu học sinh → Tạo mã/link mời GVCN → Giám sát Dashboard thi đua toàn trường & Xuất báo cáo."
        },
        {
            "role": "2. Giáo Viên Chủ Nhiệm - GVCN (Class Manager)",
            "desc": "Người quản lý trực tiếp không gian lớp học, nề nếp và học sinh trong lớp mình phụ trách.",
            "caps": [
                "Quản lý lớp học: Tiếp nhận lớp được phân công, tạo mã mời/mã QR riêng của lớp để học sinh quét tham gia.",
                "Duyệt & Quản lý danh sách học sinh: Phê duyệt học sinh vào lớp, kiểm tra tính hợp lệ của ảnh nhận diện AI và mã định danh thẻ QR.",
                "Bảng trạng thái & Thống kê nề nếp lớp: Xem điểm số chi tiết từng học sinh theo Hôm nay, Tuần này, Tuần trước, Tháng này, Từ đầu năm đến nay, Cả năm học.",
                "Phân tích xu hướng tăng trưởng / giảm sút: Biểu đồ trực quan phát hiện học sinh tiến bộ hoặc học sinh có nguy cơ vi phạm nhiều.",
                "Xếp hạng & Xuất dữ liệu: Sắp xếp học sinh theo điểm số từ cao xuống thấp theo khoảng thời gian tùy chọn; xuất file Excel/PDF gửi phụ huynh hoặc nộp Ban Thi Đua.",
                "Xử lý ngoại lệ & Đơn phép: Duyệt đơn xin nghỉ học có lý do (để không bị trừ điểm nề nếp); điểm danh bù thủ công khi có sự cố."
            ],
            "proceed": "Nhận lời mời từ Hiệu trưởng → Tiếp nhận Lớp học → Cung cấp mã QR lớp cho học sinh → Duyệt danh sách & kiểm tra ảnh AI → Theo dõi biểu đồ tăng giảm nề nếp hàng ngày → Duyệt đơn xin nghỉ & Xuất báo cáo thi đua."
        },
        {
            "role": "3. Học Sinh (Student)",
            "desc": "Người sử dụng dịch vụ điểm danh thông minh và tự quản lý hồ sơ chuyên cần cá nhân.",
            "caps": [
                "Tham gia Server trường & Lớp học: Nhập mã trường và quét mã lớp của GVCN.",
                "Cung cấp thông tin bắt buộc theo yêu cầu Server: Điền đầy đủ form do Hiệu trưởng đặt ra (Họ tên, Lớp, Mã định danh, chụp/tải ảnh chân dung chuẩn nhận diện AI).",
                "Tự động chuyển vào lớp: Ngay sau khi hoàn tất thông tin, tự động gia nhập lớp và mở khóa Bảng trạng thái cá nhân.",
                "Bảng trạng thái cá nhân (Personal Status Board): Xem điểm nề nếp cá nhân hiện tại, điểm cộng/trừ và lý do chi tiết.",
                "Lịch sử & Bằng chứng điểm danh: Xem nhật ký thời gian quét thẻ/nhận diện mặt mỗi ngày kèm ảnh chụp thực tế tại cổng.",
                "Theo dõi tiến trình bản thân: Xem biểu đồ thi đua cá nhân theo tuần, tháng, học kỳ.",
                "Mã thẻ QR điện tử: Hiển thị mã QR cá nhân trực tiếp trên màn hình điện thoại dùng để quét khi quên thẻ vật lý.",
                "Gửi đơn xin phép & Khiếu nại: Nộp đơn xin nghỉ học kèm lý do; gửi khiếu nại kèm hình ảnh minh chứng nếu bị hệ thống trừ điểm nhầm (ví dụ mặc áo khoác giữ ấm bị báo sai đồng phục)."
            ],
            "proceed": "Đăng ký tài khoản → Nhập mã trường & Quét mã lớp → Cung cấp thông tin & Tải ảnh khuôn mặt AI → Nhận mã QR cá nhân → Điểm danh tại Camera → Theo dõi Bảng trạng thái cá nhân & Khiếu nại khi cần."
        },
        {
            "role": "4. Phụ Huynh Học Sinh (Parent / Guardian) — [Tính năng Mở rộng]",
            "desc": "Kênh liên lạc tức thì giữa gia đình và nhà trường nhằm đảm bảo an toàn cho học sinh.",
            "caps": [
                "Liên kết tài khoản với con em thông qua mã định danh học sinh và mã xác thực an toàn.",
                "Nhận thông báo tức thì (Push Notification / Zalo / App): Báo ngay khoảnh khắc con vừa điểm danh vào trường an toàn (thời gian, cổng vào, trạng thái đồng phục/đúng giờ).",
                "Xem Bảng trạng thái chuyên cần & nề nếp của con xuyên suốt năm học.",
                "Nộp đơn xin nghỉ học trực tuyến cho con gửi thẳng đến GVCN kèm lý do chính đáng."
            ],
            "proceed": "Tải app/web → Liên kết mã học sinh của con → Nhận thông báo điểm danh mỗi sáng → Theo dõi nề nếp & Nộp đơn xin phép khi con ốm."
        },
        {
            "role": "5. Giám Thị / Ban Thi Đua / Đoàn Trường (Disciplinary Board) — [Tính năng Mở rộng]",
            "desc": "Bộ phận giám sát nề nếp chung và xử lý vi phạm toàn trường.",
            "caps": [
                "Theo dõi màn hình camera trực tiếp tại các cổng trường theo thời gian thực.",
                "Nhận cảnh báo vi phạm tức thì (đi trễ, sai đồng phục, cảnh báo gian lận khuôn mặt).",
                "Tiếp nhận và xét duyệt các đơn khiếu nại vi phạm của học sinh toàn trường.",
                "Chấm điểm thi đua tổng hợp giữa các lớp vào cuối tuần/cuối tháng."
            ],
            "proceed": "Giám sát luồng camera cổng trường → Xử lý danh sách vi phạm hàng ngày → Duyệt khiếu nại nề nếp → Tổng kết điểm thi đua các lớp."
        }
    ]

    for item in roles_data:
        h3 = doc.add_heading(item["role"], level=2)
        h3.style.font.name = 'Arial'
        h3.style.font.size = Pt(11.5)
        h3.style.font.bold = True
        h3.style.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
        h3.paragraph_format.space_before = Pt(8)
        h3.paragraph_format.space_after = Pt(3)

        p_desc = doc.add_paragraph()
        p_desc.paragraph_format.space_after = Pt(4)
        run_d = p_desc.add_run(f"• Vai trò: {item['desc']}")
        run_d.font.italic = True
        run_d.font.size = Pt(10)

        p_caps_title = doc.add_paragraph()
        p_caps_title.paragraph_format.space_after = Pt(2)
        r_c = p_caps_title.add_run("Các quyền hạn & tính năng cốt lõi:")
        r_c.font.bold = True
        r_c.font.size = Pt(10)

        for cap in item["caps"]:
            p_cap = doc.add_paragraph(style='List Bullet')
            p_cap.paragraph_format.space_after = Pt(2)
            p_cap.paragraph_format.line_spacing = 1.15
            run_c = p_cap.add_run(cap)
            run_c.font.size = Pt(9.5)

        p_proc = doc.add_paragraph()
        p_proc.paragraph_format.space_before = Pt(3)
        p_proc.paragraph_format.space_after = Pt(10)
        r_p_lbl = p_proc.add_run("Quy trình thực hiện (Proceed): ")
        r_p_lbl.font.bold = True
        r_p_lbl.font.size = Pt(9.5)
        r_p_lbl.font.color.rgb = RGBColor(0x00, 0x56, 0xB3)
        r_p_val = p_proc.add_run(item["proceed"])
        r_p_val.font.size = Pt(9.5)
        r_p_val.font.italic = True

    # ==============================================================
    # PHẦN 3: BẢNG MA TRẬN PHÂN QUYỀN (MATRIX)
    # ==============================================================
    h_matrix = doc.add_heading("III. BẢNG TỔNG HỢP TÍNH NĂNG THEO USER (MA TRẬN PHÂN QUYỀN)", level=1)
    h_matrix.style.font.name = 'Arial'
    h_matrix.style.font.size = Pt(12.5)
    h_matrix.style.font.bold = True
    h_matrix.style.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
    h_matrix.paragraph_format.space_before = Pt(14)
    h_matrix.paragraph_format.space_after = Pt(8)

    p_m_desc = doc.add_paragraph(
        "Bảng ma trận tổng hợp quyền hạn đối với từng tính năng nghiệp vụ trong nền tảng (Ký hiệu: ✔ = Có quyền / Cho phép; ✘ = Không có quyền):"
    )
    p_m_desc.paragraph_format.space_after = Pt(8)

    # Matrix Table Data
    matrix_headers = ["Nhóm Tính Năng / Nghiệp Vụ", "Học Sinh", "Phụ Huynh", "GVCN", "Giám Thị", "Hiệu Trưởng"]
    matrix_rows = [
        # Nhóm 1: Cá nhân & Điểm danh
        ("[CÁ NHÂN] Xem Bảng trạng thái nề nếp cá nhân / của con", "✔", "✔", "✘", "✘", "✘"),
        ("[CÁ NHÂN] Xem mã thẻ QR cá nhân trên App / Web", "✔", "✔", "✘", "✘", "✘"),
        ("[CÁ NHÂN] Xem lịch sử & hình ảnh đối chứng lúc điểm danh", "✔", "✔", "✘", "✘", "✘"),
        ("[CÁ NHÂN] Tải lên / Cập nhật ảnh khuôn mặt nhận diện AI", "✔", "✘", "✔", "✘", "✔"),
        ("[TƯƠNG TÁC] Gửi đơn xin nghỉ phép có lý do", "✔", "✔", "✘", "✘", "✘"),
        ("[TƯƠNG TÁC] Gửi khiếu nại minh chứng khi bị trừ điểm nhầm", "✔", "✔", "✘", "✘", "✘"),
        ("[THÔNG BÁO] Nhận tin nhắn thông báo tức thì khi con vào cổng", "✘", "✔", "✘", "✘", "✘"),

        # Nhóm 2: Quản lý Lớp học
        ("[LỚP HỌC] Quản lý danh sách học sinh & Duyệt vào lớp", "✘", "✘", "✔", "✘", "✔"),
        ("[LỚP HỌC] Tạo mã mời / Mã QR riêng cho lớp học", "✘", "✘", "✔", "✘", "✔"),
        ("[LỚP HỌC] Xem biểu đồ xu hướng tăng/giảm nề nếp của lớp", "✘", "✘", "✔", "✘", "✔"),
        ("[LỚP HỌC] Xếp hạng học sinh theo điểm số (tuần, tháng, năm)", "✘", "✘", "✔", "✔", "✔"),
        ("[LỚP HỌC] Xuất danh sách & điểm nề nếp ra file Excel/PDF", "✘", "✘", "✔", "✔", "✔"),
        ("[LỚP HỌC] Duyệt đơn xin phép nghỉ học & Điểm danh bù", "✘", "✘", "✔", "✔", "✔"),

        # Nhóm 3: Quản trị Trường & Hệ thống
        ("[TOÀN TRƯỜNG] Tạo Server trường & Quản trị niên khóa, lớp", "✘", "✘", "✘", "✘", "✔"),
        ("[TOÀN TRƯỜNG] Tùy biến Form thông tin bắt buộc cho học sinh", "✘", "✘", "✘", "✘", "✔"),
        ("[TOÀN TRƯỜNG] Cấu hình khung giờ, quy định trang phục theo ngày", "✘", "✘", "✘", "✘", "✔"),
        ("[TOÀN TRƯỜNG] Thiết lập thang điểm thi đua (cộng/trừ điểm)", "✘", "✘", "✘", "✘", "✔"),
        ("[TOÀN TRƯỜNG] Mời & Phân quyền GVCN, Giám thị, Ban Giám Hiệu", "✘", "✘", "✘", "✘", "✔"),
        ("[TOÀN TRƯỜNG] Bảng xếp hạng thi đua nề nếp giữa các lớp", "✘", "✘", "✔ (Lớp mình)", "✔", "✔ (Toàn trường)"),
        ("[TOÀN TRƯỜNG] Xuất báo cáo tổng hợp cấp trường nộp Sở/Phòng", "✘", "✘", "✘", "✔", "✔"),
        ("[THIẾT BỊ] Quản lý kết nối các trạm Camera AI ngoài cổng", "✘", "✘", "✘", "✔", "✔"),
        ("[THI THỨC] Giám sát luồng vi phạm và duyệt khiếu nại toàn trường", "✘", "✘", "✘", "✔", "✔"),
    ]

    # Create Table
    table = doc.add_table(rows=len(matrix_rows) + 1, cols=6)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table, color="D0D5DD", sz="4", val="single")

    col_widths = [Inches(3.0), Inches(0.8), Inches(0.8), Inches(0.8), Inches(0.9), Inches(1.1)]

    # Header Row
    hdr_cells = table.rows[0].cells
    for i, h_text in enumerate(matrix_headers):
        hdr_cells[i].text = h_text
        hdr_cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER if i > 0 else WD_ALIGN_PARAGRAPH.LEFT
        hdr_cells[i].paragraphs[0].runs[0].font.bold = True
        hdr_cells[i].paragraphs[0].runs[0].font.size = Pt(9.5)
        hdr_cells[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        set_cell_background(hdr_cells[i], "1B365D")
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=100, right=100)

    # Data Rows
    for r_idx, row_data in enumerate(matrix_rows):
        row_cells = table.rows[r_idx + 1].cells
        bg_color = "F8F9FA" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(row_data):
            row_cells[c_idx].text = val
            p = row_cells[c_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if c_idx > 0 else WD_ALIGN_PARAGRAPH.LEFT
            if len(p.runs) > 0:
                run = p.runs[0]
                run.font.size = Pt(9.0)
                if val == "✔":
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0x28, 0xA7, 0x45) # Green
                elif val == "✘":
                    run.font.color.rgb = RGBColor(0xDC, 0x35, 0x45) # Red
                elif "✔" in val:
                    run.font.color.rgb = RGBColor(0x00, 0x56, 0xB3) # Blue
                else:
                    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
            
            set_cell_background(row_cells[c_idx], bg_color)
            set_cell_margins(row_cells[c_idx], top=80, bottom=80, left=100, right=100)

    # Set column widths
    for row in table.rows:
        for i, w in enumerate(col_widths):
            row.cells[i].width = w

    # ==============================================================
    # PHẦN 4: LỢI THẾ KHI THUYẾT MINH DỰ ÁN STEM
    # ==============================================================
    h4 = doc.add_heading("IV. ĐIỂM SÁNG CÔNG NGHỆ & TÍNH THỰC TIỄN CHO BÁO CÁO STEM", level=1)
    h4.style.font.name = 'Arial'
    h4.style.font.size = Pt(12.5)
    h4.style.font.bold = True
    h4.style.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
    h4.paragraph_format.space_before = Pt(14)
    h4.paragraph_format.space_after = Pt(6)

    advantages = [
        ("Kiến trúc Edge-to-Cloud phân tán:", "Thiết bị camera tại cổng trường xử lý AI tại biên (Edge AI) với YuNet/SFace cực nhanh và offline, sau đó đồng bộ số liệu tự động lên Cloud Server trung tâm."),
        ("Bảo mật dữ liệu học sinh (Data Privacy):", "Chỉ lưu trữ vector đặc trưng khuôn mặt (Face Embeddings 128D/512D) trên máy chủ, mã hóa dữ liệu cá nhân theo tiêu chuẩn an toàn thông tin."),
        ("Tính minh bạch & Giảm áp lực thi đua:", "Học sinh và phụ huynh xem được ảnh chụp đối chứng và điểm số tức thì; cơ chế khiếu nại minh bạch giúp loại bỏ các tranh cãi tiêu cực trong thi đua."),
        ("Khả năng nhân rộng vô hạn (Scalability):", "Một nền tảng có thể phục vụ từ vài chục đến hàng trăm trường học trong toàn tỉnh mà không bị nghẽn dữ liệu.")
    ]

    for title_adv, desc_adv in advantages:
        p_adv = doc.add_paragraph(style='List Bullet')
        p_adv.paragraph_format.space_after = Pt(4)
        p_adv.paragraph_format.line_spacing = 1.15
        r_t = p_adv.add_run(title_adv + " ")
        r_t.font.bold = True
        r_t.font.size = Pt(10)
        r_t.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
        r_d = p_adv.add_run(desc_adv)
        r_d.font.size = Pt(9.5)

    # Footer note
    p_footer = doc.add_paragraph()
    p_footer.paragraph_format.space_before = Pt(16)
    p_footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_foot = p_footer.add_run("Tài liệu đặc tả kiến trúc phần mềm — Dự án STEM v5.0")
    r_foot.font.italic = True
    r_foot.font.size = Pt(8.5)
    r_foot.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    output_path = r"c:\Users\ADMIN\Desktop\Diem danh STEM\BANG_TONG_HOP_TINH_NANG_VA_MA_TRAN_PHAN_QUYEN.docx"
    doc.save(output_path)
    print(f"[OK] Da xuat file docx thanh cong tai: {output_path}")

if __name__ == "__main__":
    create_document()
