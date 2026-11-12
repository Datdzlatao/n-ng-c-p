# -*- coding: utf-8 -*-
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import shutil

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

def set_table_borders(table, color="D0D5DD", sz="4", val="single"):
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

def add_heading_styled(doc, text, level, space_before=12, space_after=5):
    h = doc.add_heading(text, level=level)
    h.style.font.name = 'Arial'
    if level == 1:
        h.style.font.size = Pt(13)
        h.style.font.bold = True
        h.style.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D) # Navy
    elif level == 2:
        h.style.font.size = Pt(11.5)
        h.style.font.bold = True
        h.style.font.color.rgb = RGBColor(0x00, 0x56, 0xB3) # Blue
    elif level == 3:
        h.style.font.size = Pt(10.5)
        h.style.font.bold = True
        h.style.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    h.paragraph_format.space_before = Pt(space_before)
    h.paragraph_format.space_after = Pt(space_after)
    return h

def add_callout_box(doc, text, title="GHI CHÚ QUAN TRỌNG", fill_hex="F0F4F8", border_hex="0056B3"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.rows[0].cells[0]
    cell.width = Inches(6.8)
    set_cell_background(cell, fill_hex)
    set_cell_margins(cell, top=120, bottom=120, left=180, right=180)
    
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(f'''
        <w:tcBorders {nsdecls("w")}>
            <w:top w:val="none"/>
            <w:bottom w:val="none"/>
            <w:right w:val="none"/>
            <w:left w:val="single" w:sz="24" w:space="0" w:color="{border_hex}"/>
        </w:tcBorders>
    ''')
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    r_title = p.add_run(f"📌 {title}\n")
    r_title.font.bold = True
    r_title.font.size = Pt(10)
    r_title.font.color.rgb = RGBColor(0x00, 0x40, 0x85)
    
    r_text = p.add_run(text)
    r_text.font.size = Pt(9.5)
    r_text.font.italic = False
    
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def add_prompt_box(doc, prompt_title, role_text, goal_text, steps_list, output_text):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.rows[0].cells[0]
    cell.width = Inches(6.8)
    set_cell_background(cell, "F9FAFB")
    set_cell_margins(cell, top=140, bottom=140, left=180, right=180)
    
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(f'''
        <w:tcBorders {nsdecls("w")}>
            <w:top w:val="single" w:sz="6" w:space="0" w:color="E2E8F0"/>
            <w:bottom w:val="single" w:sz="6" w:space="0" w:color="E2E8F0"/>
            <w:right w:val="single" w:sz="6" w:space="0" w:color="E2E8F0"/>
            <w:left w:val="single" w:sz="24" w:space="0" w:color="10B981"/>
        </w:tcBorders>
    ''')
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(4)
    r_h = p.add_run(f"💻 PROMPT MẪU: {prompt_title}\n")
    r_h.font.bold = True
    r_h.font.size = Pt(10.5)
    r_h.font.color.rgb = RGBColor(0x04, 0x78, 0x57)
    
    r_role_lbl = p.add_run("• Vai trò (Role): ")
    r_role_lbl.font.bold = True
    r_role_lbl.font.size = Pt(9.5)
    p.add_run(f"{role_text}\n").font.size = Pt(9.5)
    
    r_goal_lbl = p.add_run("• Mục tiêu (Goal): ")
    r_goal_lbl.font.bold = True
    r_goal_lbl.font.size = Pt(9.5)
    p.add_run(f"{goal_text}\n\n").font.size = Pt(9.5)
    
    r_steps_lbl = p.add_run("• Các bước triển khai chi tiết (Actionable Steps):\n")
    r_steps_lbl.font.bold = True
    r_steps_lbl.font.size = Pt(9.5)
    
    for idx, step in enumerate(steps_list, 1):
        p_step = cell.add_paragraph()
        p_step.paragraph_format.space_after = Pt(2)
        p_step.paragraph_format.line_spacing = 1.15
        r_num = p_step.add_run(f"  {idx}. ")
        r_num.font.bold = True
        r_num.font.size = Pt(9.0)
        r_s = p_step.add_run(step)
        r_s.font.size = Pt(9.0)
        
    p_out = cell.add_paragraph()
    p_out.paragraph_format.space_before = Pt(4)
    p_out.paragraph_format.space_after = Pt(2)
    r_out_lbl = p_out.add_run("• Yêu cầu đầu ra (Deliverable Output): ")
    r_out_lbl.font.bold = True
    r_out_lbl.font.size = Pt(9.5)
    p_out.add_run(f"{output_text}\n").font.size = Pt(9.0)
    
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

def generate_full_document():
    doc = Document()
    
    # Margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.85)
        section.right_margin = Inches(0.85)

    style_normal = doc.styles['Normal']
    font = style_normal.font
    font.name = 'Arial'
    font.size = Pt(10)
    font.color.rgb = RGBColor(0x33, 0x33, 0x33)

    # Title
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(4)
    run_sub = title_p.add_run("DỰ ÁN HỆ THỐNG ĐIỂM DANH & QUẢN LÝ NỀ NẾP THÔNG MINH STEM\n")
    run_sub.font.size = Pt(11)
    run_sub.font.bold = True
    run_sub.font.color.rgb = RGBColor(0x00, 0x56, 0xB3)

    run_title = title_p.add_run("ĐẶC TẢ LOGIC HIỆU CHỈNH (UPDATE v5.1)\nCHU TRÌNH TRIỂN KHAI & THIẾT KẾ UI/UX THÂN THIỆN NGƯỜI LỚN TUỔI")
    run_title.font.size = Pt(14.5)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)

    sub_p = doc.add_paragraph()
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_p.paragraph_format.space_after = Pt(12)
    run_desc = sub_p.add_run("Kiến trúc Đa Trường — Chu trình Phụ Huynh 1-Chạm — Giao diện Desktop Icon Web & Cuộn Dọc Mobile — Bộ Prompt Thi Công")
    run_desc.font.size = Pt(9.5)
    run_desc.font.italic = True
    run_desc.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    div_p = doc.add_paragraph()
    div_p.paragraph_format.space_after = Pt(10)
    div_run = div_p.add_run("―" * 52)
    div_run.font.color.rgb = RGBColor(0xDD, 0xDD, 0xDD)
    div_p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ==============================================================
    # PHẦN 1: BẢN CHẤT CỦA BẢN HIỆU CHỈNH UPDATE v5.1
    # ==============================================================
    add_heading_styled(doc, "I. BẢN CHẤT VÀ NGUYÊN TẮC CỐT LÕI CỦA BẢN HIỆU CHỈNH (UPDATE v5.1)", 1)
    
    p1 = doc.add_paragraph(
        "Bản hiệu chỉnh v5.1 khắc phục 8 điểm bất cập, thiếu khả thi và chồng chéo quyền lực trong thiết kế cũ, "
        "đồng thời tích hợp tư duy thiết kế lấy người dùng làm trung tâm (User-Centered Design) cho môi trường học đường Việt Nam."
    )
    p1.paragraph_format.line_spacing = 1.2
    p1.paragraph_format.space_after = Pt(8)

    add_callout_box(
        doc,
        "1. Nguyên tắc Đặc quyền tối thiểu (Least Privilege): Vai trò chỉ được cấp quyền đúng phạm vi cần thiết.\n"
        "2. Nguyên tắc Tách bạch trách nhiệm (Separation of Duties): Hiệu trưởng cấu hình hệ thống/camera nhưng không can thiệp duyệt ảnh sinh trắc học học sinh hay duyệt phép hàng ngày; Giám thị chỉ xem luồng video giám sát.\n"
        "3. Nguyên tắc Thiết kế Thân thiện Người lớn tuổi (Age-Friendly & Low-Tech Accessibility): Phụ huynh và Giáo viên không cần rành công nghệ vẫn sử dụng dễ dàng qua giao diện trực quan, không dùng thuật ngữ kỹ thuật phức tạp.",
        title="3 NGUYÊN TẮC THIẾT KẾ CỐT LÕI"
    )

    add_heading_styled(doc, "Bảng Phân Tích Chi Tiết 8 Điểm Thay Đổi Logic Nghiệp Vụ:", 2)

    table_changes = [
        ("1. Bảo vệ dữ liệu khuôn mặt AI (Data Privacy)", "Hiệu Trưởng có quyền tải/sửa ảnh khuôn mặt học sinh.", "BỎ quyền Hiệu trưởng can thiệp ảnh. Học sinh/Phụ huynh tự nạp ảnh, GVCN duyệt ảnh lớp mình.", "Bảo mật dữ liệu sinh trắc học cá nhân theo nguyên tắc Least Privilege."),
        ("2. Quy trình khiếu nại 2 cấp (Dispute Resolution)", "Gộp chung 1 dòng quyền mơ hồ 'Duyệt đơn/khiếu nại'.", "Tách thành 2 cấp: Cấp 1 (GVCN lớp mình xử lý trước) → Cấp 2 (Giám Thị toàn trường nếu leo thang).", "Giải quyết nhanh 90% khiếu nại tại lớp, tránh quá tải cấp trường."),
        ("3. Tách biệt Quản trị Camera và Giám sát", "Giám Thị cùng chia sẻ quyền 'Quản lý camera'.", "Chỉ Hiệu Trưởng thêm/xóa trạm Camera; Giám Thị CHỈ xem luồng video trực tiếp & nhận cảnh báo.", "Tách bạch quản lý thiết bị và giám sát vận hành; tránh cấu hình sai."),
        ("4. Xóa bỏ chồng chéo duyệt đơn xin nghỉ phép", "Giám Thị có thể duyệt đơn xin nghỉ học của học sinh.", "CHỈ GVCN có quyền duyệt đơn xin nghỉ học của lớp mình.", "Đúng thẩm quyền sư phạm; Giám thị không nắm rõ hoàn cảnh từng em."),
        ("5. Tách biệt Xem xếp hạng & Chấm điểm thi đua", "Gộp chung xem xếp hạng và chấm điểm thi đua.", "Tách riêng: Xem xếp hạng (tất cả các bên) vs Chấm thi đua (Giám thị chấm, Hiệu trưởng duyệt cuối).", "Phân định rõ giữa theo dõi thông tin và quyền hạn chốt điểm thi đua."),
        ("6. Phân cấp Chủ tài khoản gốc & Ban Giám Hiệu", "Mọi tài khoản admin có quyền lực như nhau.", "Phó Hiệu Trưởng kế thừa quyền BGH nhưng KHÔNG ĐƯỢC: (1) Xóa server trường, (2) Phân quyền BGH.", "Ngăn chặn leo thang đặc quyền và bảo vệ Server trường."),
        ("7. Cung cấp bằng chứng ảnh cho người xử lý khiếu nại", "Chỉ học sinh xem được ảnh chụp đối chứng của mình.", "Cấp quyền xem ảnh đối chứng cho GVCN (lớp mình) và Giám Thị (toàn trường) khi giải quyết khiếu nại.", "Cung cấp đầy đủ chứng cứ đối chiếu (ví dụ: mặc áo khoác giữ ấm)."),
        ("8. Bổ sung Live Stream & Real-time Alert", "Chưa có trong ma trận phân quyền dù có ở mô tả.", "Bổ sung chính thức: Xem luồng camera trực tiếp (Giám thị, BGH) và Nhận cảnh báo vi phạm tức thì.", "Đồng bộ hóa 100% tài liệu với tính năng thực tế.")
    ]

    tbl_c = doc.add_table(rows=len(table_changes) + 1, cols=4)
    tbl_c.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl_c)

    headers_c = ["Hạng mục điều chỉnh", "Thiết kế cũ (v5.0)", "Logic mới (v5.1)", "Lợi ích thực tiễn"]
    for i, h_text in enumerate(headers_c):
        cell = tbl_c.rows[0].cells[i]
        cell.text = h_text
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.runs[0].font.bold = True
        p.runs[0].font.size = Pt(9)
        p.runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        set_cell_background(cell, "1B365D")
        set_cell_margins(cell, top=100, bottom=100, left=80, right=80)

    for r_idx, (col1, col2, col3, col4) in enumerate(table_changes):
        row_cells = tbl_c.rows[r_idx + 1].cells
        bg = "F8F9FA" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, text in enumerate([col1, col2, col3, col4]):
            row_cells[c_idx].text = text
            p = row_cells[c_idx].paragraphs[0]
            if len(p.runs) > 0:
                p.runs[0].font.size = Pt(8.5)
                if c_idx == 0:
                    p.runs[0].font.bold = True
                    p.runs[0].font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
            set_cell_background(row_cells[c_idx], bg)
            set_cell_margins(row_cells[c_idx], top=80, bottom=80, left=80, right=80)

    col_widths_c = [Inches(1.8), Inches(1.5), Inches(2.0), Inches(1.5)]
    for row in tbl_c.rows:
        for i, w in enumerate(col_widths_c):
            row.cells[i].width = w

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # ==============================================================
    # PHẦN 2: THIẾT KẾ UI/UX CHUẨN GIÁO DỤC CHO NGƯỜI LỚN TUỔI (LOW-TECH)
    # ==============================================================
    add_heading_styled(doc, "II. ĐẶC TẢ THIẾT KẾ UI/UX DÀNH CHO NGƯỜI LỚN TUỔI & MÔI TRƯỜNG GIÁO DỤC", 1)

    p_ux_intro = doc.add_paragraph(
        "Nhằm xóa bỏ rào cản công nghệ cho các thầy cô lớn tuổi và các bậc phụ huynh ít tiếp xúc phần mềm phức tạp, "
        "giao diện trên Web và App được định hình theo hai triết lý hiển thị khác nhau nhưng đồng nhất về sự thân thiện:"
    )
    p_ux_intro.paragraph_format.space_after = Pt(6)

    add_heading_styled(doc, "1. Giao Diện Web (Desktop/Laptop): Phong Cách 'Desktop Launchpad Icons Grid'", 2)
    p_web_ui = doc.add_paragraph(
        "Thay vì dùng các menu đa cấp phức tạp hay sidebar chữ nhỏ khó nhìn, giao diện chính trên Web sẽ hiển thị dưới dạng "
        "các 'Ô Icon Lớn giống màn hình Desktop' (Desktop Icon Grid / Launchpad)."
    )
    p_web_ui.paragraph_format.space_after = Pt(4)

    web_ui_points = [
        "Biểu tượng to bản (64x64 px đến 80x80 px): Mỗi chức năng chính là một biểu tượng đồ họa rõ nghĩa, màu sắc trang nhã (Xanh giáo dục, Xanh lá, Cam ấm).",
        "Tiêu đề tiếng Việt không dấu/có dấu rõ ràng (Font 14-16px): Ví dụ: 'ĐIỂM DANH LỚP', 'DANH SÁCH HỌC SINH', 'CAMERA CỔNG TRƯỜNG', 'BẢNG THI ĐUA', 'XUẤT BÁO CÁO'.",
        "Thẻ tóm tắt số liệu trực tiếp trên icon: Ví dụ icon 'Duyệt Học Sinh' có huy hiệu số đỏ '(3 em chờ duyệt)', icon 'Khiếu nại' có số '(1 đơn mới)'.",
        "Bấm 1 chạm vào thẳng việc: Nhấp vào icon là mở ngay màn hình làm việc tương ứng, có nút '← Về Màn Hình Chính' luôn hiển thị ở góc trên bên trái."
    ]
    for pt in web_ui_points:
        p_pt = doc.add_paragraph(style='List Bullet')
        p_pt.paragraph_format.space_after = Pt(2)
        p_pt.paragraph_format.line_spacing = 1.15
        p_pt.add_run(pt).font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    add_heading_styled(doc, "2. Giao Diện Mobile App: Phong Cách 'Danh Sách Thẻ Cuộn Dọc' (Vertical Card Feed)", 2)
    p_app_ui = doc.add_paragraph(
        "Trên điện thoại, người lớn tuổi thường gặp khó khăn với các nút bấm nhỏ hoặc menu vuốt cạnh. "
        "Ứng dụng Mobile chuyển toàn bộ thành 'Dạng Thẻ Dọc (Vertical Cards List)', người dùng chỉ cần dùng ngón cái lướt kéo lên / kéo xuống:"
    )
    p_app_ui.paragraph_format.space_after = Pt(4)

    app_ui_points = [
        "Thiết kế thẻ to bản (Touch target lớn ≥ 52px): Các thẻ tính năng nằm dọc từ trên xuống dưới, khoảng cách rộng rãi, bấm vào vị trí nào trên thẻ cũng mở được chức năng.",
        "Màu sắc phản xạ trạng thái trực quan: Màu Xanh lá cây (Hợp lệ / Đúng giờ / Đã duyệt), Màu Đỏ cam (Chưa điểm danh / Đi trễ / Có vi phạm), Màu Xanh dương (Thông tin / Báo cáo).",
        "Chữ to, độ tương phản cao (High Contrast WCAG AAA): Cỡ chữ chính 16-18px, phụ chú 13-14px, sử dụng phông chữ dễ đọc, không dùng phông mảnh hay nghệ thuật rườm rà.",
        "Thao tác kéo thả thân thuộc (Pull to Refresh): Vuốt nhẹ màn hình từ trên xuống để cập nhật ngay trạng thái con vừa vào cổng trường."
    ]
    for pt in app_ui_points:
        p_pt = doc.add_paragraph(style='List Bullet')
        p_pt.paragraph_format.space_after = Pt(2)
        p_pt.paragraph_format.line_spacing = 1.15
        p_pt.add_run(pt).font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ==============================================================
    # PHẦN 3: CHU TRÌNH PHỤ HUYNH '1-CHẠM' TÌM CON & LIÊN KẾT (LOW-TECH)
    # ==============================================================
    add_heading_styled(doc, "III. CHU TRÌNH PHỤ HUYNH TÌM CON & LIÊN KẾT TÀI KHOẢN (LOW-TECH ONBOARDING)", 1)

    p_parent_flow_intro = doc.add_paragraph(
        "Để phụ huynh không cần nhập mã học sinh phức tạp, không cần quét mã QR hay thao tác tài khoản cầu kỳ, "
        "hệ thống áp dụng Quy trình Tìm kiếm & Kết nối 4 bước cực kỳ trực quan:"
    )
    p_parent_flow_intro.paragraph_format.space_after = Pt(6)

    parent_steps = [
        ("Bước 1: Đăng nhập Server trường & Thấy ngay Thanh Tìm Kiếm To Bản", 
         "Khi Phụ huynh mở App hoặc Web của trường, đập vào mắt ngay là một Thanh tìm kiếm to rõ (Search Bar): '🔍 Nhập tên con của bạn hoặc chọn lớp...' kèm thanh trượt chọn Lớp (Dropdown to bản: Khối 10, Khối 11, Lớp 10A1, 10A2,...)."),
        ("Bước 2: Tìm kiếm & Hiển thị Danh sách Học sinh Trực quan", 
         "Phụ huynh chỉ cần gõ tên con (ví dụ 'Nguyễn Minh An') hoặc kéo chọn 'Lớp 10A1'. Danh sách học sinh hiện ra dưới dạng các Thẻ có: Họ tên con, Ảnh thẻ đại diện, Ngày sinh để phụ huynh đối chiếu chính xác, không sợ nhầm tên trùng."),
        ("Bước 3: Chạm/Bấm Vào Thẻ Của Con", 
         "Phụ huynh chỉ cần chạm 1 lần vào thẻ của con mình. Một cửa sổ Popup lớn, đơn giản xuất hiện yêu cầu nhập đúng 2 thông tin cơ bản: \n  • Họ và tên Phụ huynh (Ví dụ: Nguyễn Văn Ba - Bố của em An)\n  • Số điện thoại Phụ huynh (Ví dụ: 0912.345.678)"),
        ("Bước 4: Xác thực Tự Động & Mở Khóa Bảng Trạng Thái Con Ngay Lập Tức", 
         "Hệ thống tự động đối chiếu số điện thoại với danh bạ học sinh nhà trường đã cung cấp (hoặc gửi mã OTP 4 số dễ bấm / gửi thông báo duyệt 1-chạm cho GVCN). \nNgay lập tức, Phụ huynh được chuyển thẳng vào Bảng Trạng Thái Của Con: Xem giờ đến trường, trạng thái đồng phục, ảnh camera chụp lúc vào cổng và nhận thông báo mỗi sáng.")
    ]

    for title_s, desc_s in parent_steps:
        p_st = doc.add_paragraph(style='List Bullet')
        p_st.paragraph_format.space_after = Pt(4)
        r_title_s = p_st.add_run(title_s + "\n")
        r_title_s.font.bold = True
        r_title_s.font.size = Pt(10)
        r_title_s.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
        r_desc_s = p_st.add_run(desc_s)
        r_desc_s.font.size = Pt(9.0)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ==============================================================
    # PHẦN 4: 5 CHU TRÌNH VẬN HÀNH LIÊN HOÀN TOÀN HỆ THỐNG
    # ==============================================================
    add_heading_styled(doc, "IV. CHU TRÌNH VẬN HÀNH LIÊN HOÀN TOÀN HỆ THỐNG (5 END-TO-END WORKFLOWS)", 1)

    workflows = [
        {
            "num": "1",
            "name": "Chu Trình Khởi Tạo & Thiết Lập Trường Học (School Onboarding)",
            "actors": "Hiệu Trưởng Gốc → Ban Giám Hiệu → GVCN",
            "steps": [
                "Bước 1.1: Hiệu Trưởng đăng ký tài khoản Master, chọn 'Khởi tạo Server Trường mới', nhập Tên trường, Mã trường, Niên khóa, Logo.",
                "Bước 1.2: Thiết lập Form nhập liệu động: Chọn các trường thông tin bắt buộc đối với học sinh (Họ tên, Lớp, Số CCCD, SĐT Phụ huynh, Ảnh khuôn mặt AI).",
                "Bước 1.3: Cài đặt Quy chế Nề nếp & Giờ giấc: Khung giờ vào học (sau 07:00 tính đi trễ), quy định trang phục theo thứ (Thứ 2: Áo dài/Đồng phục; Thứ 3-6: Đồng phục chuẩn; Thứ 7: Áo Đoàn/Tự do), điểm cộng/trừ vi phạm.",
                "Bước 1.4: Tạo Mã mời (Invite Code/Link) phân quyền gửi cho Phó Hiệu Trưởng, Giám Thị và các GVCN.",
                "Bước 1.5: Thêm các Trạm Camera AI ngoài cổng trường (gán Trạm #1 Cổng chính, Trạm #2 Ký túc xá) và sinh Secret Key để trạm AI đồng bộ dữ liệu."
            ]
        },
        {
            "num": "2",
            "name": "Chu Trình Tiếp Nhận Lớp & Thu Thập Dữ Liệu Học Sinh (Class & AI Enrollment)",
            "actors": "GVCN → Học Sinh / Phụ Huynh",
            "steps": [
                "Bước 2.1: GVCN đăng nhập qua icon Desktop Web, nhận lớp học được phân công (ví dụ: Lớp 10A1), hệ thống tự sinh Mã QR lớp và Danh sách lớp.",
                "Bước 2.2: Học sinh (hoặc Phụ huynh đối với học sinh nhỏ tuổi) mở App/Web, tìm kiếm tên mình hoặc chọn lớp của GVCN.",
                "Bước 2.3: Học sinh điền thông tin và thực hiện chụp ảnh chân dung trực tiếp trên App theo hướng dẫn căn khung của AI.",
                "Bước 2.4: Yêu cầu gia nhập chuyển đến màn hình duyệt của GVCN. GVCN kiểm tra thông tin và duyệt ảnh khuôn mặt hợp lệ.",
                "Bước 2.5: Ngay sau khi được duyệt, hệ thống tạo vector đặc trưng khuôn mặt (Face Embedding), cấp Mã thẻ QR số cho học sinh và đồng bộ vector khuôn mặt xuống các Trạm Camera AI tại cổng trường."
            ]
        },
        {
            "num": "3",
            "name": "Chu Trình Điểm Danh Thực Tế & Bắn Cảnh Báo Thời Gian Thực (Real-time Attendance)",
            "actors": "Học Sinh → Camera Edge AI → Cloud Server → Phụ Huynh, GVCN, Giám Thị",
            "steps": [
                "Bước 3.1: Học sinh bước qua cổng trường, Camera AI nhận diện danh tính và kiểm tra trang phục trong 0.2 giây.",
                "Bước 3.2: Camera Edge AI gửi gói tin log (Mã HS, thời gian, trạng thái đúng giờ/đi trễ, kết quả đồng phục, ảnh crop đối chứng) lên Cloud Server.",
                "Bước 3.3: Cloud Server tự động gửi thông báo đẩy (Push Notification / Zalo) về điện thoại Phụ Huynh: 'Con bạn đã vào trường lúc 06:45 - Trạng thái: Hợp lệ'.",
                "Bước 3.4: Nếu phát hiện vi phạm (Đi trễ, sai đồng phục, nghi vấn giả mạo), hệ thống đánh dấu cờ vi phạm, trừ điểm nề nếp và gửi cảnh báo đỏ lên Web Dashboard của Giám Thị và GVCN của lớp đó."
            ]
        },
        {
            "num": "4",
            "name": "Chu Trình Xử Lý Khiếu Nại & Đối Soát Minh Chứng 2 Cấp (Two-tier Dispute Resolution)",
            "actors": "Học Sinh / Phụ Huynh → GVCN (Cấp 1) → Giám Thị (Cấp 2)",
            "steps": [
                "Bước 4.1 (Gửi khiếu nại): Học sinh/Phụ huynh mở App, thấy bị trừ điểm vi phạm (ví dụ mặc áo khoác ấm bị báo sai đồng phục). Bấm 'Khiếu nại', nhập lý do giải trình và đính kèm ảnh minh chứng.",
                "Bước 4.2 (Xử lý Cấp 1 - GVCN): GVCN nhận thông báo khiếu nại, mở giao diện đối soát, xem ảnh gốc lúc Camera AI chụp đối chiếu với giải trình của học sinh. Nếu hợp lệ, GVCN bấm 'Chấp thuận khiếu nại' → Hệ thống tự động hoàn lại điểm nề nếp.",
                "Bước 4.3 (Leo thang Cấp 2 - Giám Thị): Nếu khiếu nại mang tính phức tạp, GVCN chuyển tiếp lên Giám Thị. Giám Thị xem xét hồ sơ toàn trường và đưa ra phán quyết cuối cùng."
            ]
        },
        {
            "num": "5",
            "name": "Chu Trình Chấm Điểm Thi Đua, Phân Tích Xu Hướng & Xuất Báo Cáo Định Kỳ",
            "actors": "GVCN → Giám Thị → Hiệu Trưởng",
            "steps": [
                "Bước 5.1: Hệ thống tự động tổng hợp điểm nề nếp hàng ngày, vẽ biểu đồ xu hướng chuyên cần của từng lớp.",
                "Bước 5.2: Cuối tuần/cuối tháng, Giám Thị mở màn hình 'Tổng hợp Thi đua', rà soát bảng xếp hạng các lớp, ghi nhận điểm cộng phong trào và bấm 'Trình duyệt Bảng thi đua'.",
                "Bước 5.3: Hiệu Trưởng kiểm tra bảng tổng hợp thi đua toàn trường, ký duyệt điện tử và công bố kết quả.",
                "Bước 5.4: GVCN và Hiệu Trưởng bấm 'Xuất Báo Cáo' để tự động tạo file Excel/PDF bảng điểm danh, bảng xếp hạng theo mẫu chuẩn Sở/Phòng GD&ĐT."
            ]
        }
    ]

    for wf in workflows:
        add_heading_styled(doc, f"{wf['num']}. {wf['name']}", 2)
        p_act = doc.add_paragraph()
        p_act.paragraph_format.space_after = Pt(3)
        r_a_lbl = p_act.add_run("• Chủ thể tham gia: ")
        r_a_lbl.font.bold = True
        r_a_lbl.font.size = Pt(9.5)
        p_act.add_run(wf["actors"]).font.size = Pt(9.5)

        for step in wf["steps"]:
            p_s = doc.add_paragraph(style='List Bullet')
            p_s.paragraph_format.space_after = Pt(2)
            p_s.paragraph_format.line_spacing = 1.15
            r_st = p_s.add_run(step)
            r_st.font.size = Pt(9.0)
        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # ==============================================================
    # PHẦN 5: BỘ PROMPT CHUẨN ĐỂ THI CÔNG TRIỂN KHAI (6 BƯỚC)
    # ==============================================================
    add_heading_styled(doc, "V. BỘ PROMPT THI CÔNG CHI TIẾT THEO TỪNG BƯỚC (ACTIONABLE PROMPTS)", 1)

    # Prompt 1
    add_prompt_box(
        doc,
        prompt_title="Bước 1: Thiết Kế Database Multi-Tenant & Phân Quyền Hỗ Trợ Tìm Kiếm Phụ Huynh",
        role_text="Senior Backend Database Architect (PostgreSQL / Supabase / FastAPI)",
        goal_text="Thiết kế Schema cơ sở dữ liệu hỗ trợ Đa trường học (Multi-tenant) với 5 vai trò phân quyền và bảng phụ huynh liên kết học sinh qua SĐT.",
        steps_list=[
            "Tạo bảng 'schools' (id, name, school_code, logo_url, academic_year, rules_config, form_config, owner_id).",
            "Tạo bảng 'users' (id, school_id, email, phone, full_name, role [HEADMASTER, VICE_HEADMASTER, TEACHER, INSPECTOR, STUDENT, PARENT], status, avatar_url).",
            "Tạo bảng 'classes' (id, school_id, name, grade_level, homeroom_teacher_id, invite_code, qr_code_url).",
            "Tạo bảng 'students' (id, user_id, class_id, student_code, full_name, dob, parent_phone, parent_name, face_embedding_128d, qr_token, current_points, is_active).",
            "Tạo bảng 'parent_student_links' (id, parent_user_id, student_id, relation_name, verified_status [PENDING, VERIFIED], verified_at).",
            "Tạo bảng 'attendance_logs' (id, student_id, camera_station_id, timestamp, status [ON_TIME, LATE, ABSENT], uniform_status, spoof_status, proof_image_url).",
            "Tạo bảng 'disputes' (id, attendance_log_id, student_id, level [LEVEL_1_TEACHER, LEVEL_2_INSPECTOR], reason, proof_image_url, status [PENDING, APPROVED, REJECTED], resolver_id, resolution_note).",
            "Tạo bảng 'leave_requests' (id, student_id, parent_id, start_date, end_date, reason, status [PENDING, APPROVED, REJECTED], approved_by_teacher_id).",
            "Thiết lập Row Level Security (RLS) để đảm bảo dữ liệu trường nào chỉ tài khoản trường đó truy cập được."
        ],
        output_text="File migration SQL hoàn chỉnh (PostgreSQL) kèm sơ đồ quan hệ ERD và script kiểm thử dữ liệu mẫu."
    )

    # Prompt 2
    add_prompt_box(
        doc,
        prompt_title="Bước 2: Xây Dựng Bộ REST API Tìm Kiếm Phụ Huynh, Điểm Danh & WebSocket Cảnh Báo",
        role_text="Fullstack Backend Engineer (Python FastAPI / Node.js Express)",
        goal_text="Xây dựng API hỗ trợ tìm kiếm học sinh cho phụ huynh, API điểm danh camera edge và WebSocket cảnh báo vi phạm.",
        steps_list=[
            "Viết API Search Students for Parents: Endpoint `/api/schools/{school_id}/search-students` cho phép tìm kiếm theo tên hoặc lọc theo Lớp/Khối, trả về danh sách học sinh (tên, lớp, ảnh thẻ, ngày sinh).",
            "Viết API Link Parent: Endpoint `/api/parents/link-student` nhận Tên phụ huynh + SĐT, tự động liên kết hoặc gửi OTP xác thực.",
            "Viết nhóm API Dynamic Registration Form: Cho phép Hiệu trưởng cấu hình form và học sinh/phụ huynh submit thông tin.",
            "Viết nhóm API Điểm danh Edge Sync: Endpoint nhận gói log điểm danh từ Camera trạm AI tại cổng, kiểm tra token và lưu DB.",
            "Viết WebSocket Server (/ws/alerts): Phát thông báo vi phạm thời gian thực tới Web Dashboard của Giám thị và GVCN.",
            "Viết nhóm API Khiếu nại 2 cấp: Tạo khiếu nại (Học sinh/Phụ huynh), Duyệt cấp 1 (GVCN), Chuyển tiếp & Duyệt cấp 2 (Giám thị).",
            "Viết Service Notification: Gửi tin nhắn thông báo tức thì qua Firebase Cloud Messaging (FCM) hoặc Zalo ZNS tới điện thoại phụ huynh."
        ],
        output_text="Bộ mã nguồn API hoàn chỉnh kèm tài liệu Swagger/OpenAPI docs (/docs) và tài liệu hướng dẫn test Postman."
    )

    # Prompt 3
    add_prompt_box(
        doc,
        prompt_title="Bước 3: Phát Triển Web Desktop Launchpad UI Cho Hiệu Trưởng, Giám Thị & GVCN",
        role_text="Senior Frontend Engineer (React.js / Next.js / TailwindCSS / Shadcn UI)",
        goal_text="Xây dựng giao diện Web theo phong cách Desktop Launchpad Icons to bản, thân thiện với người lớn tuổi và giáo viên.",
        steps_list=[
            "Xây dựng Layout Màn Hình Chính Desktop Launchpad: Bố trí các ô icon vuông lớn (kích thước 80x80px kèm nhãn chữ 16px to rõ), có huy hiệu số đếm thông báo vi phạm/đơn chờ duyệt.",
            "Xây dựng Màn hình Quản Lý Lớp & Duyệt Học Sinh (GVCN): Màn hình danh sách học sinh dạng thẻ ảnh lớn, popup duyệt ảnh AI 1 chạm, nút xuất báo cáo Excel theo chuẩn Bộ GD&ĐT.",
            "Xây dựng Màn hình Live Camera & Báo Động Đỏ (Giám Thị): Hiển thị lưới video camera cổng trường kết nối WebSocket nhận cảnh báo vi phạm trực tiếp kèm âm thanh nhẹ nhàng.",
            "Xây dựng Màn hình Đối Soát Khiếu Nại 2 Cột (GVCN & Giám Thị): Chia đôi màn hình đối chiếu ảnh camera chụp vs ảnh giải trình của học sinh.",
            "Xây dựng Màn hình Thi Đua Toàn Trường (BGH): Bảng xếp hạng các lớp với màu sắc trực quan, nút ký duyệt thi đua và xuất báo cáo PDF/Excel."
        ],
        output_text="Mã nguồn Frontend Next.js hoàn chỉnh, chuẩn UI Desktop Launchpad, đã tích hợp API và WebSocket."
    )

    # Prompt 4
    add_prompt_box(
        doc,
        prompt_title="Bước 4: Phát Triển Mobile App Cuộn Dọc & Tìm Con 1-Chạm Cho Phụ Huynh & Học Sinh",
        role_text="Mobile App Developer (Flutter / React Native / PWA)",
        goal_text="Xây dựng ứng dụng di động dạng Danh sách thẻ cuộn dọc, tối ưu cho người lớn tuổi và phụ huynh low-tech.",
        steps_list=[
            "Xây dựng Màn hình Tìm Con Cho Phụ Huynh: Thanh Search Bar to bản trên đầu trang, thanh trượt chọn Lớp học (Khối 10, 11, 12, 10A1,...), danh sách học sinh dạng Thẻ to có ảnh và ngày sinh.",
            "Xây dựng Popup Nhập Tên & SĐT Phụ Huynh: Form đơn giản 2 ô nhập liệu to bản, tự động kết nối sau khi bấm 'Xác nhận liên kết'.",
            "Xây dựng Màn hình Bảng Trạng Thái Con (Vertical Cards): Thẻ lớn hiển thị trạng thái hôm nay (Xanh lá = Đã vào trường lúc 06:45), hiển thị ảnh chụp camera cổng, số ngày chuyên cần trong tháng.",
            "Xây dựng Module Chụp Ảnh AI Cho Học Sinh: Khung căn chỉnh khuôn mặt Oval to rõ, thanh hướng dẫn sáng/tối dễ hiểu, hỗ trợ phụ huynh chụp cho con.",
            "Xây dựng Module Gửi Khiếu Nại & Đơn Xin Phép 1-Chạm: Nút bấm to ở chân trang, form viết đơn xin nghỉ học đơn giản gửi thẳng tới GVCN."
        ],
        output_text="Mã nguồn Flutter/React Native hoàn chỉnh, tương thích màn hình iOS và Android, trải nghiệm vuốt dọc mượt mà."
    )

    # Prompt 5
    add_prompt_box(
        doc,
        prompt_title="Bước 5: Nâng Cấp Engine Camera Trạm AI (Edge-to-Cloud Sync & Anti-Spoofing Chuẩn)",
        role_text="Computer Vision & Edge AI Engineer (Python / OpenCV / ONNX)",
        goal_text="Nâng cấp phần mềm camera điểm danh trạm để đồng bộ danh sách học sinh từ Server và khắc phục lỗi giả mạo.",
        steps_list=[
            "Tích hợp API Sync Khởi động: Tải danh sách Face Embeddings mới nhất của trường về bộ nhớ RAM cục bộ để nhận diện Offline 100% khi mất mạng.",
            "Khắc phục triệt để lỗi giả mạo sai do tủ đồ/phông nền: Bỏ thuật toán HoughLines; tích hợp mô hình MiniFASNet ONNX hoặc thuật toán đo chớp mắt (Blink EAR) sinh trắc học.",
            "Đóng gói log điểm danh: Gửi gói tin gồm Mã HS, thời gian, trạng thái đúng giờ, kết quả trang phục và ảnh crop bằng chứng lên Cloud API qua Background Thread.",
            "Xử lý chế độ Mất Mạng (Offline Queue): Lưu log vào SQLite cục bộ khi mất mạng và tự động gửi bù khi có Internet trở lại."
        ],
        output_text="Module Python cập nhật (`sync_manager.py`, `face_engine.py`, `anti_spoofing.py`, `main.py`) hoạt động ổn định 24/7."
    )

    # Footer
    p_footer = doc.add_paragraph()
    p_footer.paragraph_format.space_before = Pt(16)
    p_footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_foot = p_footer.add_run("Tài liệu đặc tả logic & UI/UX Low-Tech — Dự án STEM v5.1")
    r_foot.font.italic = True
    r_foot.font.size = Pt(8.5)
    r_foot.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    output_path = r"c:\Users\ADMIN\Desktop\Diem danh STEM\DACTAL_LOGIC_CAP_NHAT_VA_CHU_TRINH_TRIEN_KHAI_APP_WEB_v5.2.docx"
    doc.save(output_path)
    try:
        shutil.copy(output_path, r"C:\Users\ADMIN\Downloads\DACTAL_LOGIC_CAP_NHAT_VA_CHU_TRINH_TRIEN_KHAI_APP_WEB_v5.2.docx")
    except Exception as e:
        print(f"[WARN] Khong the copy vao Downloads vi file dang mo: {e}")
    print(f"[OK] Da cap nhat tai lieu thanh cong!")

if __name__ == "__main__":
    generate_full_document()
