import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def build_section_c_doc():
    doc = Document()

    # 1. Căn lề trang chuẩn theo file mẫu và Nghị định 30/2020/NĐ-CP
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
    caption_style = None
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

    # ================== BẮT ĐẦU NỘI DUNG PHẦN C ==================
    add_sec_title("C. QUY TRÌNH THIẾT KẾ VÀ XÂY DỰNG HỆ THỐNG")

    add_p("Hệ thống điểm danh thông minh được nhóm nghiên cứu thiết kế gồm 04 bộ phận chính hoạt động đồng bộ với nhau:")
    add_p("(1) Trạm camera AI tại cổng trường: Tự động quét mặt học sinh, kiểm tra nề nếp trang phục và hoạt động bình thường kể cả khi mất mạng Internet.")
    add_p("(2) Hệ thống máy chủ trung tâm: Quản lý dữ liệu học sinh, tính toán giờ vào trường và gửi thông báo tức thì.")
    add_p("(3) Trang web quản lý trên đa thiết bị (Máy tính, Máy tính bảng, Điện thoại): Dành cho Ban giám hiệu và thầy cô giáo theo dõi điểm danh, xem camera trực tiếp và xuất báo cáo thống kê mọi lúc mọi nơi.")
    add_p("(4) Ứng dụng trên điện thoại di động: Dành cho phụ huynh nhận thông báo khi con đến cổng trường và nộp đơn xin nghỉ phép trực tuyến.")

    # ---------------- 1.1. TRẠM CAMERA AI ----------------
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

    add_step_title("Bước 04 - Tự động theo dõi học sinh và chống quét lặp: ", 
                   "Tại cổng trường có nhiều bạn đi lại cùng lúc, hệ thống tự động gắn một mã theo dõi tạm thời cho mỗi bạn lọt vào ống kính:")
    add_p("- Học sinh chỉ được tính điểm danh đúng 1 lần khi bước qua cổng, tránh việc đứng lại nói chuyện làm máy quét liên tục nhiều lần.")
    add_p("- Máy tự động chọn khoảnh khắc học sinh nhìn thẳng và rõ nét nhất để lưu ảnh làm bằng chứng.")
    add_p("- Màn hình camera phản hồi ngay bằng màu sắc rất dễ nhìn: Khung viền xanh lá (Điểm danh thành công); Khung viền vàng (Đang đối chiếu dữ liệu); Khung viền đỏ (Người lạ hoặc vi phạm).")
    add_image_placeholder("Hình 04: Camera theo dõi học sinh và thông báo kết quả bằng viền màu sắc trên màn hình", "Màn hình camera hiển thị viền trạng thái")

    add_step_title("Bước 05 - Tự động kiểm tra trang phục theo lịch trong tuần: ", 
                   "Hệ thống tự động phát hiện thân người và chia thành vùng áo và vùng quần để kiểm tra theo đúng lịch nề nếp của nhà trường:")
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

    # ---------------- 1.2. MÁY CHỦ TRUNG TÂM ----------------
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

    # ---------------- 1.3. GIAO DIỆN WEB ĐA THIẾT BỊ ----------------
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

    # Bổ sung thông tin đường dẫn truy cập website thực tế
    add_step_title("Đường dẫn truy cập và trải nghiệm hệ thống web: ",
                   "Ban Giám Khảo và người dùng có thể trực tiếp mở trình duyệt (Chrome, Cốc Cốc, Safari) trên máy tính hoặc điện thoại để trải nghiệm hệ thống qua các đường dẫn sau:")
    add_p("- Địa chỉ trang chủ tìm trường và đăng ký: http://localhost:5173 (hoặc tên miền máy chủ của trường).")
    add_p("- Địa chỉ Bảng điều khiển quản trị (Dashboard): http://localhost:5173/app/index.html?school_id=1")
    add_p("- Tài khoản trải nghiệm thử: Hiệu trưởng (tên đăng nhập: hieutruong / mật khẩu: 123456), Giám thị (giamthi01 / 123456), Giáo viên chủ nhiệm (gvcn10a1 / 123456).")

    # ---------------- 1.4. MOBILE APP ----------------
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

    # Lưu file
    output_path = "/home/minhphuc/Diem-danh-STEM/docs/reports/rewrite bao cao/PHAN_C_QUY_TRINH_THIET_KE_CHUAN_MOI.docx"
    doc.save(output_path)
    print(f"✅ Đã tạo thành công file docx tại: {output_path}")

if __name__ == "__main__":
    build_section_c_doc()
