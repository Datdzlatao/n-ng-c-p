import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os

def create_short_report():
    doc = Document()

    # Cấu hình lề trang theo Nghị định 30/2020/NĐ-CP
    for s in doc.sections:
        s.top_margin = Cm(2.0)
        s.bottom_margin = Cm(2.0)
        s.left_margin = Cm(3.0)
        s.right_margin = Cm(2.0)
        s.page_width = Cm(21.0)
        s.page_height = Cm(29.7)

    # Cấu hình Normal style: Times New Roman, 14pt
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

    # --- TIÊU NGỮ VÀ TIÊU ĐỀ ---
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
    r = p_l.add_run("Số: 02/BC-STEM")
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
    p_title.paragraph_format.space_before = Pt(14)
    p_title.paragraph_format.space_after = Pt(4)
    r_title = p_title.add_run("BÁO CÁO TỔNG KẾT CÁC TÍNH NĂNG CỐT LÕI VÀ KẾ HOẠCH PHÁT TRIỂN\nHỆ THỐNG ĐIỂM DANH HỌC SINH THÔNG MINH STEM")
    format_run(r_title, bold=True, size=15)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(16)
    r_sub = p_sub.add_run("(Bản báo cáo tóm tắt tập trung vào cơ chế thu thập mẫu khuôn mặt, khả năng quét đồng thời và truyền tin thời gian thực)")
    format_run(r_sub, italic=True, size=13.5)

    # --- MỤC I ---
    add_sec_title("I. ĐẶT VẤN ĐỀ VÀ MỤC ĐÍCH BÁO CÁO")
    add_p("Trong quá trình triển khai ứng dụng công nghệ Trí tuệ nhân tạo (AI) vào công tác điểm danh và quản lý học đường, mục tiêu then chốt là xây dựng một quy trình vận hành nhanh chóng, thuận tiện cho học sinh, giải tỏa áp lực giám sát cho nhà trường và kết nối tức thời với gia đình. Báo cáo này tập trung làm rõ 3 tính năng cốt lõi đã được nghiên cứu, phát triển và ứng dụng thực tiễn trong hệ thống Điểm danh Thông minh STEM, đồng thời chỉ ra các kết quả đã đạt được và phương hướng nâng cấp tiếp theo.")

    # --- MỤC II ---
    add_sec_title("II. BA TÍNH NĂNG CỐT LÕI CỦA HỆ THỐNG")

    add_subsec_title("1. Phân quyền cho học sinh chủ động gửi mẫu khuôn mặt qua điện thoại")
    add_p("Trước đây, việc thu thập dữ liệu sinh trắc học khuôn mặt thường yêu cầu kỹ thuật viên chụp ảnh trực tiếp từng học sinh tại trường, gây mất nhiều ngày công và làm gián đoạn thời gian học tập. Hệ thống hiện tại đã giải quyết triệt để vấn đề này nhờ cơ chế phân quyền tự phục vụ (Self-service Biometric Enrollment) an toàn và chặt chẽ:")
    add_bullet_item("Học sinh tự gửi ảnh", "Học sinh sử dụng điện thoại thông minh cá nhân đăng nhập vào hệ thống, tự chụp hoặc tải lên các ảnh chân dung rõ nét theo hướng dẫn (chụp trực diện, ánh sáng đều, không đeo kính râm, không che mặt).")
    add_bullet_item("Bảo mật phân quyền", "Học sinh chỉ có quyền tải ảnh lên hồ sơ của chính mình. Hệ thống tự động kiểm tra chất lượng ảnh đầu vào sơ bộ và lưu ở trạng thái chờ duyệt, tuyệt đối không cho phép học sinh tự ý can thiệp vào cơ sở dữ liệu nhận diện chung.")
    add_bullet_item("Kiểm duyệt bởi Giáo viên chủ nhiệm", "Giáo viên chủ nhiệm phụ trách lớp sẽ nhận được thông báo và xem xét hình ảnh của từng học sinh. Khi giáo viên xác nhận đúng nhận dạng của học sinh lớp mình và bấm phê duyệt, hệ thống mới tự động trích xuất vector đặc trưng khuôn mặt (128D Face Embeddings) và đồng bộ về các trạm camera biên tại cổng trường.")

    add_subsec_title("2. Khả năng điểm danh đồng thời từ 2 đến 3 học sinh tại cùng một thời điểm")
    add_p("Vào khung giờ cao điểm đầu buổi sáng (từ 06 giờ 45 phút đến 07 giờ 15 phút), lượng học sinh di chuyển qua cổng trường rất đông. Nếu camera bắt buộc học sinh phải đứng lại từng người một sẽ gây ùn tắc giao thông nghiêm trọng trước cổng trường. Hệ thống đã xử lý bài toán này nhờ công nghệ thị giác máy tính đa luồng:")
    add_bullet_item("Xử lý đa đối tượng song song", "Camera trạm biên tích hợp thuật toán phát hiện khuôn mặt đồng thời (Multi-face Detection) kết hợp bộ theo dõi chuyển động (Multi-object Tracking). Khi có từ 2 đến 3 học sinh cùng bước qua cổng trường song song hoặc nối tiếp nhau trong cùng một khung hình, camera tự động tách riêng các khuôn mặt và nhận diện song song.")
    add_bullet_item("Tốc độ phản hồi tức thời", "Thời gian nhận diện và xử lý mỗi lượt chỉ từ 0.2 đến 0.5 giây cho cả nhóm 2 - 3 học sinh, cho phép học sinh đi bộ bình thường qua cổng mà không cần dừng lại xếp hàng đơn lẻ.")
    add_bullet_item("Kiểm tra đồng phục song song", "Bên cạnh nhận diện khuôn mặt, hệ thống đồng thời quét vùng thân trên của từng học sinh trong khung hình để đối chiếu màu sắc trang phục theo đúng quy định của ngày hôm đó (áo trắng, áo Đoàn hoặc áo truyền thống).")

    add_subsec_title("3. Ghi nhận thời gian thực và thông báo tức thời cho Giáo viên và Phụ huynh")
    add_p("Hệ thống xóa bỏ hoàn toàn độ trễ của sổ điểm danh giấy truyền thống, thiết lập kênh thông tin tức thời và minh bạch giữa nhà trường và gia đình:")
    add_bullet_item("Ghi nhận dữ liệu thời gian thực", "Ngay tại giây học sinh bước qua cổng trạm camera, bản ghi điểm danh (bao gồm: thời gian chính xác đến từng giây, trạng thái đúng giờ hoặc đi muộn, kết quả kiểm tra đồng phục và ảnh chụp bằng chứng tại hiện trường) được gửi ngay về máy chủ.")
    add_bullet_item("Báo cáo cho Giáo viên chủ nhiệm", "Trên màn hình làm việc của Giáo viên chủ nhiệm, danh sách lớp tự động cập nhật trạng thái học sinh đã vào trường theo thời gian thực (thông qua kết nối WebSockets) mà không cần tải lại trang. Giáo viên biết chính xác học sinh nào đã đến trường, học sinh nào chưa đến để kịp thời nắm bắt tình hình chuyên cần đầu giờ.")
    add_bullet_item("Thông báo đến Phụ huynh học sinh", "Ứng dụng di động của phụ huynh lập tức nhận được thông báo đẩy kèm theo ảnh chụp thực tế của con tại cổng trường. Phụ huynh hoàn toàn yên tâm khi biết rõ thời điểm con đã đến trường an toàn và chấp hành đúng quy định nề nếp.")

    # --- MỤC III ---
    add_sec_title("III. ĐÁNH GIÁ KẾT QUẢ ĐÃ ĐẠT ĐƯỢC VÀ PHƯƠNG HƯỚNG CẦN PHÁT TRIỂN")

    add_subsec_title("1. Những phần đã làm được")
    add_p("Đến thời điểm hiện tại, hệ thống đã hoàn thiện và vận hành ổn định các nội dung sau:")
    add_bullet_item("Quy trình thu thập ảnh tự phục vụ", "Giao diện trên điện thoại thân thiện, cho phép học sinh dễ dàng tự tải ảnh; phân quyền duyệt ảnh của Giáo viên chủ nhiệm hoạt động chính xác, bảo đảm tính xác thực danh tính.")
    add_bullet_item("Nhận diện đồng thời tại cổng", "Trạm camera AI nhận diện tốt 2 đến 3 học sinh cùng lúc ở khoảng cách từ 1.5 mét đến 3.5 mét trong điều kiện ánh sáng cổng trường thông thường.")
    add_bullet_item("Kênh thông báo tức thời", "Hạ tầng WebSockets và máy chủ thông báo hoạt động ổn định, độ trễ gửi dữ liệu đến màn hình giáo viên và điện thoại phụ huynh dưới 1 giây.")
    add_bullet_item("Bảo vệ dữ liệu khi mất mạng", "Trạm camera có bộ nhớ đệm SQLite tự lưu trữ dữ liệu ngoại tuyến khi mất Internet và tự động gửi bù khi có mạng, bảo đảm không bị mất dữ liệu điểm danh.")

    add_subsec_title("2. Những phần cần tiếp tục phát triển")
    add_p("Để nâng cao hơn nữa hiệu quả vận hành và đáp ứng các tình huống phức tạp trong thực tế, hệ thống định hướng phát triển các điểm trọng tâm sau:")
    add_bullet_item("Mở rộng khả năng quét nhóm đông", "Nâng cấp thuật toán theo dõi chuyển động để xử lý tốt khi học sinh đi thành nhóm đông từ 4 đến 5 người chen chúc hoặc che khuất một phần khuôn mặt nhau trong khung giờ cao điểm sát giờ đóng cổng.")
    add_bullet_item("Hỗ trợ chuẩn hóa ảnh tự động", "Bổ sung tính năng thông minh trên ứng dụng điện thoại: tự động nhận biết góc mặt nghiêng, độ sáng kém hoặc mặt bị che khuất để nhắc nhở học sinh chụp lại ngay trên điện thoại trước khi gửi Giáo viên chủ nhiệm duyệt.")
    add_bullet_item("Đa dạng hóa kênh gửi thông báo", "Bên cạnh thông báo qua ứng dụng di động, tích hợp thêm kênh tin nhắn OTT (Zalo ZNS hoặc SMS Brandname) để những phụ huynh chưa cài ứng dụng hoặc đang tắt kết nối mạng 4G/Wifi vẫn nhận được thông báo con vào trường kịp thời.")
    add_bullet_item("Nâng cấp khả năng xử lý máy chủ", "Chuyển đổi hệ cơ sở dữ liệu sang PostgreSQL để đáp ứng mượt mà khi hàng chục trạm camera tại nhiều cổng trường đồng thời đẩy dữ liệu điểm danh và ảnh chụp về máy chủ trong cùng một phút.")

    # --- MỤC IV ---
    add_sec_title("IV. KẾT LUẬN")
    add_p("Ba tính năng cốt lõi: học sinh tự gửi mẫu khuôn mặt qua điện thoại, camera quét đồng thời 2 đến 3 học sinh tại cổng trường, và thông báo thời gian thực đến Giáo viên chủ nhiệm cùng Phụ huynh đã tạo nên sự khác biệt đột phá của Hệ thống Điểm danh Thông minh STEM. Giải pháp không chỉ hiện đại hóa khâu quản lý nề nếp của nhà trường mà còn mang lại sự tiện lợi, an tâm cho học sinh và gia đình. Nhóm nghiên cứu sẽ tiếp tục hoàn thiện các nội dung cần phát triển để đưa hệ thống vào phục vụ diện rộng trong năm học mới.")

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
        
    out_path_1 = os.path.join(download_folder, "BAO_CAO_RUT_GON_TINH_NANG_DIEM_DANH_STEM.docx")
    out_path_2 = "/home/minhphuc/Diem-danh-STEM/docs/reports/BAO_CAO_RUT_GON_TINH_NANG_DIEM_DANH_STEM.docx"

    doc.save(out_path_1)
    doc.save(out_path_2)
    print(f"Tao file docx rut gon thanh cong:\n1. {out_path_1}\n2. {out_path_2}")

if __name__ == "__main__":
    create_short_report()
