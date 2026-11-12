import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os

def build_complete_report():
    doc = Document()

    # 1. Căn lề trang chuẩn theo Nghị định 30/2020/NĐ-CP
    for s in doc.sections:
        s.top_margin = Cm(2.5)       # 2.5cm
        s.bottom_margin = Cm(2.5)    # 2.5cm
        s.left_margin = Cm(3.0)      # 3.0cm
        s.right_margin = Cm(2.0)     # 2.0cm
        s.page_width = Cm(21.0)      # Khổ A4
        s.page_height = Cm(29.7)

    # 2. Cấu hình Style mặc định: Times New Roman, 14pt
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(14)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.35
    normal_style.paragraph_format.space_after = Pt(6)
    normal_style.paragraph_format.space_before = Pt(0)

    # Style chú thích (Chư thcihs)
    try:
        caption_style = doc.styles['Chư thcihs']
    except KeyError:
        caption_style = doc.styles.add_style('Chư thcihs', docx.enum.style.WD_STYLE_TYPE.PARAGRAPH)
    caption_style.font.name = 'Times New Roman'
    caption_style.font.size = Pt(12)
    caption_style.font.italic = True
    caption_style.font.color.rgb = RGBColor(40, 40, 40)
    caption_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption_style.paragraph_format.first_line_indent = Cm(0)
    caption_style.paragraph_format.space_before = Pt(4)
    caption_style.paragraph_format.space_after = Pt(10)
    caption_style.paragraph_format.line_spacing = 1.15

    def format_run(r, bold=False, italic=False, size=14, color=RGBColor(0, 0, 0)):
        r.font.name = 'Times New Roman'
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.color.rgb = color

    def add_p(text="", align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=True, bold=False, italic=False, size=14, space_before=0, space_after=6):
        p = doc.add_paragraph()
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
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.line_spacing = 1.35
        r = p.add_run(text)
        format_run(r, bold=True, size=14)
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

    def add_step_title(step_text, desc_text=""):
        p = doc.add_paragraph()
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
        tbl = doc.add_table(rows=1, cols=1)
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

        cap_p = doc.add_paragraph(style='Chư thcihs')
        cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap_p.paragraph_format.first_line_indent = Cm(0)
        cap_p.paragraph_format.space_before = Pt(4)
        cap_p.paragraph_format.space_after = Pt(10)
        r_cap = cap_p.add_run(caption_text)
        format_run(r_cap, italic=True, size=12, color=RGBColor(40, 40, 40))

    def add_real_image(image_path, caption_text, width_cm=16.0):
        if os.path.exists(image_path):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = 1.0
            r = p.add_run()
            r.add_picture(image_path, width=Cm(width_cm))

            cap_p = doc.add_paragraph(style='Chư thcihs')
            cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap_p.paragraph_format.first_line_indent = Cm(0)
            cap_p.paragraph_format.space_before = Pt(4)
            cap_p.paragraph_format.space_after = Pt(10)
            r_cap = cap_p.add_run(caption_text)
            format_run(r_cap, italic=True, size=12, color=RGBColor(40, 40, 40))
        else:
            add_image_placeholder(caption_text, caption_text)

    def format_table(table, col_widths, headers, data):
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr_cells = table.rows[0].cells
        for idx, text in enumerate(headers):
            hdr_cells[idx].text = text
            hdr_cells[idx].width = col_widths[idx]
            tcPr = hdr_cells[idx]._tc.get_or_add_tcPr()
            shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="EDF2F7"/>')
            tcPr.append(shd)
            p = hdr_cells[idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.line_spacing = 1.15
            for run in p.runs:
                format_run(run, bold=True, size=12.5)

        for r_idx, row_data in enumerate(data):
            row_cells = table.rows[r_idx + 1].cells
            for c_idx, cell_value in enumerate(row_data):
                row_cells[c_idx].text = cell_value
                row_cells[c_idx].width = col_widths[c_idx]
                p = row_cells[c_idx].paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if c_idx > 0 else WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(4)
                p.paragraph_format.line_spacing = 1.15
                for run in p.runs:
                    format_run(run, bold=(c_idx==0), size=12)

        for row in table.rows:
            for cell in row.cells:
                tcPr = cell._tc.get_or_add_tcPr()
                borders = parse_xml(f'''
                    <w:tcBorders {nsdecls("w")}>
                        <w:top w:val="single" w:sz="4" w:space="0" w:color="CBD5E0"/>
                        <w:left w:val="single" w:sz="4" w:space="0" w:color="CBD5E0"/>
                        <w:bottom w:val="single" w:sz="4" w:space="0" w:color="CBD5E0"/>
                        <w:right w:val="single" w:sz="4" w:space="0" w:color="CBD5E0"/>
                    </w:tcBorders>
                ''')
                tcPr.append(borders)

    # ==================== TIÊU ĐỀ BÁO CÁO ====================
    add_p("BÁO CÁO DỰ ÁN STEM", align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, bold=True, size=15, space_before=0, space_after=4)
    add_p("“HỆ THỐNG ĐIỂM DANH THÔNG MINH BẰNG QR CODE, NHẬN DIỆN KHUÔN MẶT VÀ KIỂM TRA TRANG PHỤC TỰ ĐỘNG TẠI TRƯỜNG PTDTNT THPT TỈNH LAI CHÂU”",
          align=WD_ALIGN_PARAGRAPH.CENTER, indent=False, bold=True, size=14, space_before=0, space_after=12)

    # ==================== PHẦN A ====================
    add_sec_title("A. THÀNH VIÊN NHÓM")
    add_p("- Học sinh: Vàng Minh Phúc - Lớp 12C1.", indent=True)
    add_p("- Giáo viên hướng dẫn: Bùi Thanh Bình, Nguyễn Thị Thúy Hạnh", indent=True)

    # ==================== PHẦN B ====================
    add_sec_title("B. TÊN DỰ ÁN")
    add_p("“HỆ THỐNG ĐIỂM DANH THÔNG MINH BẰNG QR CODE, NHẬN DIỆN KHUÔN MẶT VÀ KIỂM TRA TRANG PHỤC TỰ ĐỘNG TẠI TRƯỜNG PTDTNT THPT TỈNH LAI CHÂU”", indent=True, bold=True)
    add_p("Dự án là hệ sinh thái phần mềm đa nền tảng (vận hành linh hoạt trên cả Linux, Windows và thiết bị di động), được phát triển từ sự kết hợp giữa các ngôn ngữ Python, JavaScript và Flutter/Dart.", indent=True)
    add_p("Hệ thống kết nối giữa trạm camera AI tại cổng trường, máy chủ trung tâm và ứng dụng di động để tự động thực hiện các chức năng chính:", indent=True)
    add_p("(1) Điểm danh học sinh bằng mã QR Code cá nhân kết hợp xác thực khuôn mặt đa tầng và công nghệ chống gian lận (Anti-Spoofing).", indent=True)
    add_p("(2) Tự động kiểm tra trang phục học sinh theo đúng quy định từng ngày trong tuần (trang phục dân tộc, áo trắng, áo đoàn thanh niên).", indent=True)
    add_p("(3) Quản trị dữ liệu tập trung, phát cảnh báo âm thanh tại chỗ, đồng bộ thời gian thực lên Web Dashboard đa thiết bị và gửi thông báo tức thì về điện thoại phụ huynh.", indent=True)

    # ==================== PHẦN C ====================
    add_sec_title("C. QUY TRÌNH THIẾT KẾ VÀ XÂY DỰNG HỆ THỐNG")
    add_p("Hệ thống điểm danh thông minh được nhóm nghiên cứu thiết kế gồm 04 bộ phận chính hoạt động đồng bộ với nhau:")
    add_p("(1) Trạm camera AI tại cổng trường: Tự động quét mặt học sinh, kiểm tra nề nếp trang phục và hoạt động bình thường kể cả khi mất mạng Internet.", indent=True)
    add_p("(2) Hệ thống máy chủ trung tâm: Quản lý dữ liệu học sinh, tính toán giờ vào trường và gửi thông báo tức thì.", indent=True)
    add_p("(3) Trang web quản lý trên đa thiết bị (Máy tính, Máy tính bảng, Điện thoại): Dành cho Ban giám hiệu và thầy cô giáo theo dõi điểm danh, xem camera trực tiếp và xuất báo cáo thống kê mọi lúc mọi nơi.", indent=True)
    add_p("(4) Ứng dụng trên điện thoại di động: Dành cho phụ huynh nhận thông báo khi con đến cổng trường và nộp đơn xin nghỉ phép trực tuyến.", indent=True)

    # 1.1 TRẠM CAMERA AI
    add_subsec_title("1.1. Xây dựng Trạm camera AI tại cổng trường:")
    add_step_title("Bước 01 - Thu thập dữ liệu và tạo thẻ QR cho học sinh: ", 
                   "Chụp ảnh chân dung học sinh nhìn thẳng trong điều kiện đủ sáng để làm ảnh mẫu lưu trên máy tính. Hệ thống tự động in thẻ học sinh có mã QR riêng biệt cho từng em. Mã QR này chứa thông tin cá nhân được mã hóa, giúp máy nhận diện nhanh và chính xác.")
    add_image_placeholder("Hình 01: Dữ liệu ảnh khuôn mặt học sinh mẫu và Thẻ định danh QR Code cá nhân", "Bộ ảnh học sinh mẫu và Thẻ QR định danh")

    add_step_title("Bước 02 - Nhận diện khuôn mặt nhanh và mượt mà: ", 
                   "Khi học sinh đứng trước camera, hệ thống sẽ tự động tìm vị trí khuôn mặt trước, sau đó mới đối chiếu với ảnh mẫu đã lưu để xác nhận đúng học sinh. Để camera không bị đơ hay giật lag, hệ thống áp dụng cơ chế quét thông minh: cứ cách 5 khung hình máy mới so sánh khuôn mặt một lần và giữ nguyên kết quả hiển thị cho các khung hình xen kẽ. Nhờ cách làm này, video camera chuyển động rất mượt mà (đạt 25 - 30 hình/giây) và hoạt động ổn định trên cả máy tính thông thường lẫn mạch Raspberry Pi nhỏ gọn.")
    add_image_placeholder("Hình 02: Sơ đồ luồng nhận diện khuôn mặt giúp hệ thống vận hành nhanh và mượt mà", "Sơ đồ luồng nhận diện khuôn mặt")

    add_step_title("Bước 03 - Tích hợp tính năng chống điểm danh giả: ", 
                   "Để ngăn học sinh dùng ảnh in trên giấy hoặc giơ điện thoại chụp ảnh bạn để điểm danh hộ, hệ thống được bổ sung thuật toán kiểm tra người thật. Thuật toán này phân tích ánh sáng phản chiếu từ màn hình và độ mịn bề mặt. Nếu phát hiện là ảnh chụp lại, hệ thống lập tức từ chối và ghi lại ảnh vi phạm.")
    add_image_placeholder("Hình 03: Thuật toán phân tích bề mặt phát hiện và ngăn chặn hành vi đưa ảnh điện thoại trước camera", "Hình minh họa chống điểm danh bằng ảnh giả")

    add_step_title("Bước 04 - Tự động theo dõi học sinh và phản hồi đa giác quan (Hình ảnh + Âm thanh): ", 
                   "Tại cổng trường có nhiều bạn đi lại cùng lúc, hệ thống tự động gắn một mã theo dõi tạm thời cho mỗi bạn lọt vào ống kính:")
    add_p("- Học sinh chỉ được tính điểm danh đúng 1 lần khi bước qua cổng, tránh việc đứng lại nói chuyện làm máy quét liên tục nhiều lần.")
    add_p("- Máy tự động chọn khoảnh khắc học sinh nhìn thẳng và rõ nét nhất để lưu ảnh làm bằng chứng.")
    add_p("- Phản hồi bằng màu sắc trên màn hình: Khung viền xanh lá (Điểm danh thành công); Khung viền vàng (Đang đối chiếu dữ liệu); Khung viền đỏ (Người lạ hoặc vi phạm).")
    add_p("- Tích hợp cảnh báo âm thanh (Chuông báo / Loa) tại cổng trường và khu vực phòng học: Vì màn hình máy chủ đặt trong phòng điều hành, hệ thống trang bị thêm chuông báo tại chỗ. Khi điểm danh thành công, máy phát 01 tiếng 'Beep' ngắn vui tai để học sinh yên tâm bước tiếp mà không cần ngoái nhìn màn hình; khi có người lạ hoặc vi phạm (khung đỏ), chuông cảnh báo 'Tít - tít - tít' kéo dài lập tức reo lên để bảo vệ can thiệp kịp thời và gửi tín hiệu về phòng học.")
    add_image_placeholder("Hình 04: Camera theo dõi học sinh và thông báo kết quả bằng viền màu sắc kết hợp chuông báo âm thanh", "Màn hình camera hiển thị viền trạng thái và chuông báo")

    add_step_title("Bước 05 - Tự động kiểm tra trang phục theo lịch trong tuần: ", 
                   "Hệ thống phát hiện thân người và phân vùng áo - quần để kiểm tra theo đúng lịch nề nếp của nhà trường:")
    add_p("- Thứ Hai (Trang phục dân tộc/truyền thống): Sử dụng mô hình trí tuệ nhân tạo (MobileNetV2 rút gọn) đã được học từ hàng trăm bức ảnh để nhận diện hoa văn dân tộc.")
    add_p("- Thứ Ba, Thứ Năm, Thứ Sáu (Áo trắng, Áo đoàn thanh niên): Không cần dùng trí tuệ nhân tạo nặng máy, mà dùng cách lọc dải màu (không gian màu HSV) để kiểm tra màu trắng hoặc xanh dương. Cách này nhận diện màu áo rất chính xác kể cả khi trời nắng hay râm mát.")
    add_p("- Thứ Tư, Thứ Bảy (Trang phục tự do): Hệ thống tự động bỏ qua, không kiểm tra.")
    add_p("- Lợi ích: Việc kết hợp linh hoạt này giúp máy tính không phải chạy trí tuệ nhân tạo liên tục, giảm 60% đến 70% tải xử lý, giúp máy chạy êm và mát suốt cả ngày.")
    add_image_placeholder("Hình 05: Quy trình kiểm tra trang phục thông minh kết hợp giữa nhận diện hoa văn và lọc màu theo lịch tuần", "Sơ đồ kiểm tra trang phục theo lịch tuần")

    add_step_title("Bước 06 - Cơ chế hoạt động bình thường khi mất mạng Internet: ", 
                   "Mạng Internet tại cổng trường đôi khi không ổn định. Nhóm đã thiết kế chế độ lưu trữ an toàn tại chỗ:")
    add_p("- Khi mất mạng: Toàn bộ lượt quét mặt và ảnh học sinh được lưu tạm thời vào ổ cứng máy tính tại cổng. Việc điểm danh của học sinh diễn ra bình thường, không bị dừng lại.")
    add_p("- Khi có mạng trở lại: Phần mềm tự động gửi toàn bộ dữ liệu lưu tạm lên máy chủ mà không làm mất bất kỳ lượt điểm danh nào.")
    add_image_placeholder("Hình 06: Cơ chế tự động lưu tạm tại máy khi mất mạng và đồng bộ lên máy chủ khi có mạng trở lại", "Sơ đồ lưu trữ và đồng bộ dữ liệu khi mất mạng")

    # 1.2 MÁY CHỦ TRUNG TÂM
    add_subsec_title("1.2. Xây dựng Hệ thống máy chủ trung tâm (Backend):")
    add_step_title("Bước 01 - Thiết kế cơ sở dữ liệu ngăn nắp, khoa học: ", 
                   "Thay vì lưu dữ liệu vào các bảng tính rời rạc dễ bị lỗi, nhóm xây dựng cơ sở dữ liệu chuyên nghiệp gồm các bảng liên kết chặt chẽ:")
    add_p("- Bảng danh sách học sinh: Lưu họ tên, lớp, mã số, ảnh thẻ.")
    add_p("- Bảng nhật ký điểm danh: Lưu giờ vào trường, cổng ra vào, đi đúng giờ hay đi muộn.")
    add_p("- Bảng vi phạm nề nếp: Lưu lại lỗi mặc sai trang phục kèm ảnh chụp đối chiếu.")
    add_p("- Bảng đơn nghỉ phép: Quản lý các đơn xin phép của phụ huynh.")
    add_image_placeholder("Hình 07: Sơ đồ liên kết các bảng dữ liệu quản lý học sinh và lịch sử điểm danh", "Sơ đồ cấu trúc cơ sở dữ liệu")

    add_step_title("Bước 02 - Lập trình cầu nối dữ liệu siêu tốc bằng Python: ", 
                   "Sử dụng công cụ FastAPI (ngôn ngữ Python) để làm cầu nối giữa camera, trang web và ứng dụng điện thoại. Cầu nối này xử lý yêu cầu cực nhanh (chưa tới 0,02 giây), giúp camera gửi dữ liệu về máy chủ tức thì mà không bị tắc nghẽn.")
    add_image_placeholder("Hình 08: Giao diện kiểm tra các cổng kết nối dữ liệu tự động của máy chủ", "Giao diện quản trị kết nối máy chủ")

    add_step_title("Bước 03 - Bảo vệ an toàn thông tin học sinh: ", 
                   "Hệ thống đặt yếu tố bảo mật lên hàng đầu:")
    add_p("- Toàn bộ mật khẩu của thầy cô và học sinh đều được mã hóa bằng thuật toán hiện đại, tuyệt đối không lưu mật khẩu thô.")
    add_p("- Phân quyền rõ ràng: Thầy cô trường nào chỉ xem được học sinh trường đó, giáo viên chủ nhiệm lớp nào chỉ quản lý học sinh lớp đó, tránh nhầm lẫn hoặc lộ lọt thông tin.")

    add_step_title("Bước 04 - Truyền dữ liệu trực tiếp trong tích tắc (Thời gian thực): ", 
                   "Máy chủ kết nối trực tiếp với màn hình máy tính của phòng giám thị qua đường truyền tức thời. Ngay khi học sinh vừa bước qua cổng, thông tin và ảnh chụp lập tức hiện lên màn hình giám sát trong vòng chưa đầy 1 giây.")
    add_image_placeholder("Hình 09: Luồng truyền thông tin điểm danh tức thì từ cổng trường về màn hình giám sát", "Sơ đồ truyền dữ liệu thời gian thực")

    # 1.3 WEB DASHBOARD
    add_subsec_title("1.3. Xây dựng Trang web quản lý hoạt động trên đa thiết bị (Máy tính, Máy tính bảng và Điện thoại):")
    add_step_title("Bước 01 - Tương thích mượt mà trên mọi thiết bị (Responsive Web): ", 
                   "Trang web được thiết kế thông minh, tự động co giãn vừa vặn với mọi kích thước màn hình mà không cần cài đặt phần mềm phức tạp:")
    add_p("- Trên máy tính (PC/Laptop): Giao diện hiển thị rộng rãi, đầy đủ bảng số liệu lớn, thuận tiện cho Ban giám hiệu và Giám thị làm việc hàng ngày.")
    add_p("- Trên máy tính bảng và điện thoại di động: Các nút bấm, bảng biểu tự động sắp xếp gọn gàng theo chiều dọc, chữ to rõ ràng, giúp thầy cô giáo có thể cầm điện thoại đi lại trong sân trường hoặc lớp học để kiểm tra sĩ số rất tiện lợi.")

    add_step_title("Bước 02 - Phân chia màn hình làm việc riêng cho từng người dùng: ", 
                   "Tùy theo tài khoản đăng nhập, trang web sẽ tự động mở đúng chức năng cần thiết, giúp người dùng thao tác nhanh và không bị rối mắt:")
    add_p("- Tài khoản Hiệu trưởng: Xem tỷ lệ chuyên cần toàn trường, cấu hình khung giờ vào học và quy định đồng phục của từng thứ trong tuần.")
    add_p("- Tài khoản Giám thị: Xem hình ảnh trực tiếp từ camera cổng trường, theo dõi danh sách học sinh vi phạm đồng phục theo thời gian thực và giải quyết các khiếu nại điểm danh.")
    add_p("- Tài khoản Giáo viên chủ nhiệm: Quản lý riêng sĩ số lớp mình, xem giờ học sinh đến trường, duyệt đơn xin nghỉ phép của phụ huynh và phê duyệt ảnh khuôn mặt học sinh mới đăng ký.")
    add_p("- Tài khoản Học sinh & Phụ huynh: Tra cứu lịch sử chuyên cần cá nhân và lấy mã thẻ QR dự phòng.")
    add_image_placeholder("Hình 10: Giao diện trang web quản lý tự động co giãn trên cả màn hình máy tính và điện thoại", "Giao diện Web Dashboard đa thiết bị")

    add_step_title("Bước 03 - Vẽ biểu đồ tự động và xuất báo cáo Excel: ", 
                   "Hệ thống tự động gom số liệu và vẽ thành các biểu đồ trực quan:")
    add_p("- Biểu đồ tròn: Thể hiện nhanh số học sinh đi học đúng giờ, đi muộn và vắng mặt trong ngày.")
    add_p("- Biểu đồ cột: Thống kê khung giờ học sinh đến cổng đông nhất để nhà trường chủ động bố trí mở cổng và phân luồng giao thông.")
    add_p("- Xuất dữ liệu ra file bảng tính Excel (.xlsx) chỉ với một cú nhấp chuột, phục vụ công tác báo cáo và xếp loại thi đua hàng tuần của nhà trường.")
    add_image_placeholder("Hình 11: Biểu đồ thống kê chuyên cần trực quan và tính năng xuất file Excel báo cáo", "Biểu đồ thống kê trên giao diện web")

    add_step_title("Đường dẫn truy cập và trải nghiệm hệ thống web: ",
                   "Ban Giám Khảo và người dùng có thể trực tiếp mở trình duyệt (Chrome, Cốc Cốc, Safari) trên máy tính hoặc điện thoại để trải nghiệm hệ thống qua các đường dẫn sau:")
    add_p("- Địa chỉ trang chủ tìm trường và đăng ký: http://localhost:5173 (hoặc tên miền máy chủ của trường).")
    add_p("- Địa chỉ Bảng điều khiển quản trị (Dashboard): http://localhost:5173/app/index.html?school_id=1")
    add_p("- Tài khoản trải nghiệm thử: Hiệu trưởng (tên đăng nhập: hieutruong / mật khẩu: 123456), Giám thị (giamthi01 / 123456), Giáo viên chủ nhiệm (gvcn10a1 / 123456).")

    # 1.4 MOBILE APP
    add_subsec_title("1.4. Xây dựng Ứng dụng trên điện thoại di động (Mobile App):")
    add_step_title("Bước 01 - Lập trình ứng dụng dùng chung cho cả Android và iPhone: ", 
                   "Sử dụng nền tảng Flutter và ngôn ngữ Dart để tạo ra một ứng dụng di động hoàn chỉnh cài đặt được trên cả điện thoại Android (Samsung, Xiaomi, Oppo...) và iOS (iPhone). Giao diện được thiết kế đơn giản, chữ to rõ ràng, các bậc phụ huynh lớn tuổi cũng thao tác dễ dàng.")

    add_step_title("Bước 02 - Tích hợp Thẻ học sinh điện tử trên điện thoại: ", 
                   "Mỗi học sinh có một thẻ điện tử trên app điện thoại hiển thị rõ họ tên, lớp và mã QR cá nhân. Nếu hôm nào quên mang thẻ giấy, học sinh chỉ cần mở app giơ mã QR trước camera tại cổng trường là điểm danh được ngay.")

    add_step_title("Bước 03 - Gửi thông báo ngay lập tức về điện thoại cha mẹ: ", 
                   "Ngay khi con vừa quét mặt ở cổng trường, điện thoại của phụ huynh sẽ nhận được thông báo tức thì: con đã vào trường lúc mấy giờ, mặc trang phục đúng hay sai, kèm ảnh chụp thực tế lúc qua cổng. Nhờ đó, bố mẹ hoàn toàn an tâm biết con đã đến trường an toàn.")
    add_image_placeholder("Hình 12: Màn hình ứng dụng điện thoại và tin nhắn thông báo tức thì gửi cho phụ huynh", "Màn hình ứng dụng điện thoại thông minh")

    add_step_title("Bước 04 - Nộp và duyệt đơn xin nghỉ phép trực tuyến: ", 
                   "Thay thế hoàn toàn việc viết đơn xin phép bằng giấy truyền thống:")
    add_p("- Phụ huynh mở app trên điện thoại, chọn ngày xin nghỉ, lý do và gửi cho thầy cô.")
    add_p("- Giáo viên chủ nhiệm nhận được tin nhắn thông báo, xem lý do và bấm nút 'Duyệt'.")
    add_p("- Hệ thống tự động ghi nhận học sinh đó 'Nghỉ có phép' vào sổ điểm danh toàn trường, giúp tiết kiệm thời gian và quản lý minh bạch.")
    add_image_placeholder("Hình 13: Quy trình phụ huynh gửi đơn xin nghỉ phép trên điện thoại và giáo viên duyệt trực tuyến", "Quy trình xin nghỉ phép trên ứng dụng")

    # ==================== PHẦN D HOÀN CHỈNH: LOGIC, MODULE, HƯỚNG DẪN & TRẢI NGHIỆM THỰC TẾ ====================
    add_sec_title("D. LOGIC HOẠT ĐỘNG, MÔ TẢ CÁC MODULE VÀ HƯỚNG DẪN SỬ DỤNG HỆ THỐNG")

    # D.1 LOGIC HOẠT ĐỘNG
    add_subsec_title("1. Sơ đồ Logic hoạt động liên hoàn của toàn bộ hệ thống:")
    add_p("Hệ thống điểm danh thông minh STEM không hoạt động đơn lẻ mà là một chuỗi xử lý tự động, tức thời kết nối chặt chẽ giữa 4 phân hệ chức năng:")
    add_p("- Bước 1 (Tại cổng trường): Học sinh bước đến trạm camera, đưa khuôn mặt hoặc Thẻ định danh QR cá nhân trước ống kính.")
    add_p("- Bước 2 (Tại trạm camera AI): Camera tự động thực hiện quét mã QR, trích xuất đặc trưng khuôn mặt (so khớp vector 128-D), kiểm tra chống giả mạo Anti-Spoofing và kiểm tra trang phục theo lịch tuần. Dữ liệu lập tức được ghi vào bộ đệm ngoại tuyến SQLite và phản hồi tại chỗ bằng viền khung màu sắc kết hợp chuông 'Beep' thành công hoặc còi báo vi phạm.")
    add_p("- Bước 3 (Tại máy chủ trung tâm): Tiếp nhận kết quả qua API siêu tốc (dưới 0.02 giây), phân loại bảo mật JWT, lưu trữ vào cơ sở dữ liệu và đồng thời phát tín hiệu theo 2 hướng thời gian thực.")
    add_p("- Bước 4 (Tại ứng dụng di động): Điện thoại của phụ huynh rung lên và nhận thông báo con đã vào cổng kèm hình ảnh camera chụp thực tế.")
    add_p("- Bước 5 (Tại Web Dashboard): Màn hình của Hiệu trưởng, Giám thị và Giáo viên chủ nhiệm cập nhật tức thời số liệu chuyên cần và hình ảnh trực tiếp từ cổng trường.")

    # Chèn ảnh sơ đồ AI đã tạo
    diagram_img = "/home/minhphuc/Diem-danh-STEM/docs/reports/rewrite bao cao/so_do_nguyen_ly_he_thong.jpg"
    add_real_image(diagram_img, "Hình 14: Sơ đồ luồng logic hoạt động khép kín của toàn bộ hệ sinh thái Điểm danh STEM")

    # D.2 MÔ TẢ CHI TIẾT CÁC MODULE VÀ HÌNH ẢNH GIAO DIỆN
    add_subsec_title("2. Mô tả chi tiết các Module chức năng và Hình ảnh giao diện thực tế:")
    add_p("Hệ thống được thiết kế theo mô hình phân quyền chặt chẽ. Mỗi người dùng khi đăng nhập sẽ được đưa đến không gian làm việc chuyên biệt:")

    add_p("2.1. Module Trạm Camera AI tại cổng trường:", bold=True)
    add_p("Chức năng: Tự động bắt nét khuôn mặt, quét mã QR, kiểm tra trang phục và phát tín hiệu cảnh báo.")
    add_p("Màn hình hiển thị tại cổng trường gồm 3 khu vực trực quan:")
    add_p("- Khung hình camera trung tâm: Hiển thị luồng video mượt mà 30 FPS kèm khung viền nhận diện (Xanh lá: Đúng học sinh & Đúng trang phục; Đỏ: Người lạ hoặc vi phạm).")
    add_p("- Thẻ thông tin tức thời (Góc phải trên): Hiện rõ Họ tên, Lớp, Mã học sinh và Kết quả kiểm tra trang phục (OK / SAI / UNCLEAR).")
    add_p("- Hệ thống loa/chuông cảnh báo âm thanh: Phát tiếng 'Beep' ngắn khi thành công hoặc còi 'Tít - tít - tít' khi phát hiện vi phạm.")
    add_image_placeholder("Hình 15: Giao diện màn hình Trạm Camera AI hoạt động thực tế tại cổng trường", "Giao diện màn hình Trạm Camera AI")

    add_p("2.2. Module Bảng điều khiển Web Dashboard (Dành cho Máy tính & Điện thoại):", bold=True)
    add_p("Trang web tự động co giãn theo kích thước màn hình (Responsive Web), bao gồm các phân hệ chính:")

    add_p("a) Không gian làm việc của Hiệu trưởng (Quản trị toàn trường):", bold=True)
    add_p("- Bảng số liệu tổng quan (Overview Cards): Hiển thị tổng sĩ số toàn trường, số học sinh đã vào trường đúng giờ, số học sinh đi muộn, số vắng mặt và số trường hợp vi phạm trang phục trong ngày.")
    add_p("- Cấu hình quy định trường học: Cho phép thay đổi khung giờ vào lớp (ví dụ: sau 7h00 tính là đi trễ), cấu hình lịch đồng phục cho từng thứ trong tuần mà không cần sửa code.")
    add_p("- Quản lý danh sách trạm camera: Xem trạng thái hoạt động (Online/Offline) của từng trạm camera tại các cổng và cấp khóa bảo mật kết nối.")
    add_image_placeholder("Hình 16: Giao diện Bảng điều khiển Web dành cho Hiệu trưởng trên máy tính", "Giao diện Web của Hiệu trưởng")

    add_p("b) Không gian làm việc của Giám thị (Giám sát nề nếp & An ninh):", bold=True)
    add_p("- Màn hình Camera trực tiếp: Xem hình ảnh truyền trực tiếp từ các cổng trường theo thời gian thực.")
    add_p("- Bảng danh sách vi phạm trực tiếp (Live Violations): Khi có học sinh vi phạm trang phục hoặc người lạ, hệ thống lập tức đẩy dòng cảnh báo kèm ảnh chụp cận cảnh lên đầu danh sách để giám thị kiểm tra.")
    add_p("- Xử lý khiếu nại Cấp 2: Tiếp nhận và giải quyết các khiếu nại điểm danh từ học sinh khi có sai lệch.")
    add_image_placeholder("Hình 17: Giao diện giám sát camera trực tiếp và danh sách vi phạm của Giám thị", "Giao diện Giám thị giám sát nề nếp")

    add_p("c) Không gian làm việc của Giáo viên chủ nhiệm (Quản lý lớp học):", bold=True)
    add_p("- Sổ điểm danh điện tử của lớp: Chỉ hiển thị danh sách học sinh của đúng lớp mình phụ trách. Cập nhật trạng thái tự động: Có mặt, Đi trễ, Vắng có phép, Vắng không phép.")
    add_p("- Phân hệ Duyệt ảnh khuôn mặt AI mới: Khi có học sinh chuyển trường đến hoặc cập nhật ảnh chân dung mới, giáo viên bấm xem ảnh và duyệt để hệ thống cập nhật vào bộ nhận diện camera.")
    add_p("- Phân hệ Phê duyệt đơn xin nghỉ phép: Tiếp nhận đơn xin nghỉ do phụ huynh gửi từ ứng dụng di động; giáo viên xem lý do và chỉ cần bấm nút 'Duyệt' hoặc 'Từ chối'.")
    add_image_placeholder("Hình 18: Giao diện Giáo viên chủ nhiệm điểm danh lớp và duyệt đơn nghỉ phép trực tuyến", "Giao diện Giáo viên chủ nhiệm")

    add_p("2.3. Module Ứng dụng di động Flutter (Dành cho Phụ huynh và Học sinh):", bold=True)
    add_p("- Thẻ học sinh điện tử (Digital ID): Hiển thị ảnh thẻ, họ tên, lớp và mã QR động trên màn hình điện thoại giúp học sinh quét mặt tại cổng khi quên thẻ cứng.")
    add_p("- Nhật ký chuyên cần & Thông báo con vào cổng: Lưu trữ chi tiết lịch sử ra/vào trường từng ngày, hiển thị rõ thời gian chính xác đến từng giây kèm hình ảnh camera chụp thực tế lúc con qua cổng.")
    add_p("- Nộp đơn xin nghỉ phép trực tuyến: Giao diện chọn ngày, chọn buổi (sáng/chiều/cả ngày), nhập lý do và đính kèm ảnh giấy khám bệnh/giấy lý do gửi thẳng cho GVCN.")
    add_image_placeholder("Hình 19: Giao diện Ứng dụng di động Flutter trên điện thoại của Phụ huynh và Học sinh", "Giao diện Mobile App")

    # D.3 HƯỚNG DẪN SỬ DỤNG
    add_subsec_title("3. Hướng dẫn sử dụng hệ thống chi tiết cho từng vai trò:")

    add_p("3.1. Hướng dẫn dành cho Ban Giám Hiệu / Hiệu Trưởng:", bold=True)
    add_p("- Đăng nhập: Mở trình duyệt web (máy tính hoặc điện thoại), truy cập http://localhost:5173/app/index.html?school_id=1, nhập tài khoản hieutruong / mật khẩu 123456.")
    add_p("- Theo dõi chuyên cần toàn trường: Màn hình trang chủ hiển thị ngay biểu đồ tỷ lệ đi học và các chỉ số tổng quan hôm nay.")
    add_p("- Cài đặt quy định: Vào mục Cài đặt trường -> Thiết lập giờ giới nghiêm vào lớp và tích chọn quy định đồng phục của từng ngày trong tuần -> Bấm Lưu cấu hình.")

    add_p("3.2. Hướng dẫn dành cho Giám Thị:", bold=True)
    add_p("- Đăng nhập: Đăng nhập tài khoản giamthi01 / mật khẩu 123456.")
    add_p("- Giám sát cổng trường: Mở tab Camera trực tiếp để theo dõi học sinh đi qua cổng. Khi có tiếng còi cảnh báo hoặc khung đỏ xuất hiện, nhìn vào bảng Vi phạm nề nếp để xem tên học sinh, lớp và lỗi vi phạm cụ thể để xử lý tại chỗ.")

    add_p("3.3. Hướng dẫn dành cho Giáo Viên Chủ Nhiệm:", bold=True)
    add_p("- Đăng nhập: Đăng nhập tài khoản lớp phụ trách (ví dụ: gvcn10a1 / mật khẩu 123456).")
    add_p("- Kiểm tra sĩ số lớp: Vào tab Điểm danh lớp, xem danh sách học sinh hôm nay: ai đã đến trường, ai đi trễ, ai chưa có mặt.")
    add_p("- Duyệt đơn xin phép: Khi có chấm đỏ thông báo tại mục Đơn nghỉ phép, giáo viên nhấp vào xem lý do của phụ huynh và bấm nút xanh [Phê duyệt]. Hệ thống sẽ tự động đổi trạng thái học sinh thành 'Vắng có phép'.")

    add_p("3.4. Hướng dẫn dành cho Phụ Huynh & Học Sinh:", bold=True)
    add_p("- Trên điện thoại di động: Mở ứng dụng Điểm danh STEM, đăng nhập bằng số điện thoại đã đăng ký.")
    add_p("- Nhận thông báo: Khi con đi qua cổng trường, điện thoại tự động rung và nhận thông báo: 'Em Vàng Minh Phúc đã vào trường lúc 06:45:12. Trang phục: Hợp lệ (Áo trắng).'")
    add_p("- Xin nghỉ phép: Chọn mục Nộp đơn xin phép -> Chọn ngày nghỉ -> Nhập lý do -> Nhấn [Gửi đơn]. Khi giáo viên duyệt, ứng dụng sẽ có thông báo xác nhận.")

    add_p("Bảng 01: Các phím tắt điều khiển nhanh trạm camera khi cần thao tác trực tiếp:", bold=True, indent=False)
    tbl_shortcuts = doc.add_table(rows=5, cols=2)
    tbl_shortcuts_headers = ["Phím bấm", "Chức năng thao tác nhanh"]
    tbl_shortcuts_data = [
        ["Q hoặc ESC", "Thoát chương trình trạm camera và tự động lưu chốt dữ liệu cuối ngày."],
        ["R", "Tải lại danh sách học sinh và bộ ảnh mẫu mới nhất từ máy chủ."],
        ["C", "Bật/Tắt chế độ cân chỉnh màu sắc HSV trực tiếp trên màn hình."],
        ["SPACE (Phím cách)", "Chụp nhanh một ảnh thủ công để kiểm tra độ nét của ống kính."]
    ]
    format_table(tbl_shortcuts, [Cm(4.0), Cm(11.5)], tbl_shortcuts_headers, tbl_shortcuts_data)
    # D.4 TRẢI NGHIỆM THỰC TẾ
    add_subsec_title("4. Ghi nhận trải nghiệm thực tế và Đánh giá từ người dùng tại trường học:")
    add_p("Hệ thống đã được triển khai chạy thử nghiệm thực tế tại cổng trường PTDTNT THPT Tỉnh Lai Châu trong đợt cao điểm đầu buổi học và nhận được phản hồi rất tích cực từ các bên liên quan:")
    add_p("- Trải nghiệm của học sinh: Học sinh rất hào hứng và tự giác. Khi bước qua cổng, học sinh chỉ cần hướng thẻ/khuôn mặt về camera trong vòng 1 giây, nghe tiếng chuông 'Beep' là biết mình đã được điểm danh thành công mà không phải đứng chờ đợi lâu như trước.")
    add_p("- Trải nghiệm của Giáo viên chủ nhiệm: Thầy cô không còn phải mất 5 đến 10 phút đầu mỗi tiết học để cầm sổ gọi tên từng học sinh. Vừa mở máy tính ở phòng chờ giáo viên là đã nắm trọn danh sách học sinh vắng của lớp mình.")
    add_p("- Trải nghiệm của Phụ huynh học sinh: Phụ huynh (đặc biệt là các phụ huynh nhà ở xa trường nội trú) bày tỏ sự an tâm tuyệt đối khi nhận được thông báo kèm ảnh con mình đã vào trường an toàn mỗi buổi sáng.")

    add_image_placeholder("Hình 20: Học sinh điểm danh bằng nhận diện khuôn mặt kết hợp thẻ QR tại cổng trường (Ảnh thực tế)", "Ảnh học sinh điểm danh tại cổng trường")
    add_image_placeholder("Hình 21: Màn hình điện thoại phụ huynh nhận thông báo tức thời khi con vào trường (Ảnh thực tế)", "Ảnh điện thoại phụ huynh nhận thông báo")
    add_image_placeholder("Hình 22: Giáo viên chủ nhiệm theo dõi sổ điểm danh điện tử và phê duyệt đơn nghỉ phép (Ảnh thực tế)", "Ảnh giáo viên chủ nhiệm sử dụng hệ thống")

    # ==================== PHẦN E ====================
    add_sec_title("E. THỬ NGHIỆM VÀ CÁC BIỆN PHÁP KHẮC PHỤC")
    add_p("Để đảm bảo hệ thống vận hành bền bỉ và chính xác trong môi trường học đường thực tế, nhóm nghiên cứu đã áp dụng quy trình thiết kế kỹ thuật lặp (Engineering Design Process - EDP), trải qua 03 giai đoạn thử nghiệm và cải tiến toàn diện:")

    add_subsec_title("1. Thử nghiệm lần 01: Nhận diện khuôn mặt và quét QR cơ bản (Môi trường phòng thí nghiệm):")
    add_p("- Mục tiêu: Đánh giá khả năng quét mã QR và so khớp khuôn mặt học sinh trên máy tính cá nhân.")
    add_p("- Vấn đề phát sinh: Khi học sinh di chuyển, camera bị giật lag (chỉ đạt 10 - 12 khung hình/giây); máy bị đơ nếu nhiều người đứng trước ống kính; học sinh đứng lâu bị quét lặp gửi liên tục hàng chục lần; có thể dùng ảnh điện thoại để điểm danh hộ.")
    add_p("- Biện pháp khắc phục: Tách quy trình nhận diện làm 2 khâu (chỉ so khớp sâu sau mỗi 5 khung hình); lập trình bộ theo dõi Tracker gán mã tạm thời để chỉ điểm danh đúng 1 lần duy nhất; bổ sung thuật toán Anti-Spoofing kiểm tra độ phản chiếu màn hình để ngăn chặn dùng ảnh giả.")
    add_p("- Kết quả thu được: Tốc độ khung hình tăng vọt lên 28 - 30 khung hình/giây (mượt mà); loại bỏ hoàn toàn hiện tượng quét lặp; ngăn chặn thành công các hành vi đưa ảnh điện thoại trước camera.")

    add_subsec_title("2. Thử nghiệm lần 02: Kiểm tra trang phục tự động bằng AI và lọc màu (Điều kiện ánh sáng lớp học):")
    add_p("- Mục tiêu: Thử nghiệm nhận diện trang phục dân tộc bằng mô hình AI MobileNetV2 và kiểm tra áo trắng, áo đoàn bằng lọc màu sắc.")
    add_p("- Vấn đề phát sinh: Dữ liệu ảnh trang phục dân tộc ban đầu quá ít (168 ảnh gốc) khiến AI nhận diện sai; khi trời đổi từ nắng sang râm mát thì màu áo trắng bị nhận nhầm; chạy mô hình AI liên tục khiến CPU máy tính bị nóng (85°C - 90°C).")
    add_p("- Biện pháp khắc phục: Áp dụng kỹ thuật tăng cường dữ liệu (nhân bản lên 832 ảnh) và gán trọng số phạt class_weight khi huấn luyện; chuyển sang không gian màu HSV và tạo công cụ kéo thanh trượt chỉnh màu theo phòng; sáng tạo bộ định tuyến Hybrid AI (chỉ chạy mô hình AI vào Thứ Hai, các ngày khác dùng lọc màu HSV siêu nhẹ).")
    add_p("- Kết quả thu được: Độ chính xác nhận diện trang phục dân tộc đạt trên 92%; nhận diện màu áo trắng/áo đoàn ổn định dưới mọi thời tiết; giảm tới 65% tải CPU, máy vận hành mát mẻ cả ngày.")

    add_subsec_title("3. Thử nghiệm lần 03: Triển khai thực tế tại cổng trường học (Giờ cao điểm vào lớp 6h30 - 7h00):")
    add_p("- Mục tiêu: Lắp đặt trạm camera thực tế tại cổng trường THPT, thử nghiệm trong giờ cao điểm học sinh đến trường đông đúc.")
    add_p("- Vấn đề phát sinh: Mạng Internet tại cổng trường chập chờn làm gián đoạn việc gửi dữ liệu; học sinh và bác bảo vệ không biết máy đã nhận diện chưa vì màn hình máy chủ đặt trong phòng điều hành; phụ huynh ở nhà không nắm được giờ con vào trường.")
    add_p("- Biện pháp khắc phục: Xây dựng bộ nhớ đệm ngoại tuyến (Offline Buffer SQLite), tự động lưu tạm tại máy khi mất mạng và tự động đồng bộ khi có mạng; gắn thêm còi chuông âm thanh 'Beep' tại cổng trường để học sinh nghe thấy là đi tiếp; phát triển Web Dashboard theo dõi trực tiếp và Ứng dụng điện thoại gửi thông báo tức thì cho phụ huynh.")
    add_p("- Kết quả thu được: 100% dữ liệu không bị thất lạc khi mất kết nối mạng; giải tỏa triệt để tình trạng ùn ứ tại cổng trường; phụ huynh nhận được thông báo kèm ảnh chỉ sau 1 - 2 giây.")

    add_p("Bảng 02: Bảng tổng hợp 3 chu trình thử nghiệm, phát hiện lỗi và các giải pháp kỹ thuật khắc phục:", bold=True, indent=False)
    tbl_tests = doc.add_table(rows=4, cols=4)
    tbl_tests_headers = ["Đợt thử nghiệm", "Điều kiện thử nghiệm", "Vấn đề phát sinh", "Giải pháp kỹ thuật khắc phục"]
    tbl_tests_data = [
        ["Lần 01", "Phòng thí nghiệm (Máy tính đơn lẻ)", "Giật lag (10 FPS), quét lặp nhiều lần, bị qua mặt bởi ảnh điện thoại.", "Tách 2 khâu nhận diện (cách 5 frame), thêm Tracker gán ID và thuật toán Anti-Spoofing."],
        ["Lần 02", "Phòng học (Ánh sáng thay đổi)", "Dữ liệu AI ít gây đoán sai, màu áo bị nhầm khi trời râm, CPU quá nóng.", "Tăng cường 832 ảnh, dùng class_weight, chuyển sang hệ màu HSV và định tuyến Hybrid."],
        ["Lần 03", "Cổng trường THPT (Giờ cao điểm)", "Mạng Internet chập chờn, học sinh ùn ứ do không biết đã quét xong chưa.", "Xây dựng đệm ngoại tuyến Offline Buffer, gắn chuông báo âm thanh Beep và làm Mobile App."]
    ]
    format_table(tbl_tests, [Cm(2.0), Cm(4.0), Cm(4.5), Cm(5.0)], tbl_tests_headers, tbl_tests_data)

    # ==================== PHẦN F ====================
    add_sec_title("F. ĐÁNH GIÁ HIỆU QUẢ DỰ ÁN")
    add_subsec_title("1. Hiệu quả về kinh tế:")
    add_p("- Chi phí đầu tư siêu tiết kiệm: Các giải pháp camera AI thương mại trên thị trường hiện nay có giá từ 20.000.000 đến 45.000.000 VNĐ cho một trạm điểm danh, kèm chi phí bản quyền phần mềm hàng năm rất đắt đỏ. Trong khi đó, hệ thống của nhóm tận dụng phần cứng phổ thông sẵn có (máy tính cũ của trường, webcam hoặc mạch Raspberry Pi) với tổng chi phí lắp đặt chỉ từ 3.000.000 đến 4.500.000 VNĐ/trạm. Toàn bộ phần mềm do nhóm tự xây dựng, hoàn toàn miễn phí bản quyền.")
    add_p("- Tiết kiệm chi phí vận hành: Loại bỏ hoàn toàn việc in ấn sổ sách điểm danh bằng giấy, phiếu phép và thẻ giấy hàng năm, giúp nhà trường tiết kiệm hàng triệu đồng ngân sách văn phòng phẩm mỗi học kỳ.")

    add_subsec_title("2. Hiệu quả về kỹ thuật và xã hội:")
    add_p("- Tốc độ xử lý siêu tốc: Thời gian nhận diện và kiểm tra trang phục chỉ mất dưới 1.5 giây/học sinh, nhanh gấp hàng chục lần so với việc điểm danh thủ công truyền thống (thường mất từ 3 đến 5 phút cho mỗi lớp học).")
    add_p("- Độ chính xác và độ tin cậy cao: Đạt trên 96% đối với nhận diện khuôn mặt và trên 92% đối với phân loại trang phục học đường theo lịch tuần. Cơ chế Offline Buffer đảm bảo 100% dữ liệu không bị thất lạc kể cả khi trường bị mất kết nối Internet.")
    add_p("- Giải phóng sức lao động cho giáo viên: Tiết kiệm từ 15 đến 25 giờ giảng dạy mỗi năm cho mỗi lớp học, giúp thầy cô giáo tập trung tối đa thời gian vào công tác chuyên môn và giảng dạy.")
    add_p("- Nâng cao ý thức nề nếp và tính tự giác của học sinh: Giúp học sinh hình thành thói quen đúng giờ, tự giác mặc đúng trang phục truyền thống dân tộc và đồng phục học đường mà không cần giám thị nhắc nhở nặng nề.")
    add_p("- Kết nối minh bạch giữa nhà trường và gia đình: Giúp phụ huynh nắm bắt tức thời thời gian con đến trường và tình hình nề nếp thông qua ứng dụng điện thoại, mang lại sự an tâm tuyệt đối cho gia đình.")

    add_p("Bảng 03: So sánh quy trình điểm danh và kiểm tra nề nếp trước và sau khi áp dụng sản phẩm:", bold=True, indent=False)
    tbl_compare = doc.add_table(rows=6, cols=3)
    tbl_compare_headers = ["Tiêu chí so sánh", "Phương pháp thủ công trước đây", "Hệ thống điểm danh STEM mới"]
    tbl_compare_data = [
        ["Thời gian điểm danh", "Mất 3 - 5 phút/lớp/tiết (chiếm 10% giờ học).", "Chỉ mất dưới 1.5 giây/học sinh tại cổng trường."],
        ["Kiểm tra trang phục", "Giám thị đứng nhìn bằng mắt, dễ sót, cảm tính.", "Camera AI và bộ lọc màu tự động phân tích 100%."],
        ["Lưu trữ & Thống kê", "Ghi sổ tay, cộng trừ thủ công, dễ thất lạc.", "Cơ sở dữ liệu tự động lưu trữ, xuất Excel trong 1 giây."],
        ["Thông báo cho cha mẹ", "Chỉ biết khi con về nhà hoặc giáo viên gọi điện.", "Nhận thông báo tức thì trên điện thoại kèm ảnh chụp."],
        ["Khả năng hoạt động", "Phụ thuộc hoàn toàn vào con người.", "Vận hành tự động, hoạt động tốt kể cả khi mất mạng."]
    ]
    format_table(tbl_compare, [Cm(3.5), Cm(6.0), Cm(6.0)], tbl_compare_headers, tbl_compare_data)

    output_path = "/home/minhphuc/Diem-danh-STEM/docs/reports/rewrite bao cao/BÁO CÁO DỰ ÁN STEM.docx"
    doc.save(output_path)
    print(f"✅ Đã tạo thành công BÁO CÁO DỰ ÁN STEM hoàn chỉnh tại: {output_path}")

if __name__ == "__main__":
    build_complete_report()
