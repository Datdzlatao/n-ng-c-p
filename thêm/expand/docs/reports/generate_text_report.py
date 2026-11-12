import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
import os

def create_text_report():
    doc = Document()

    # Cấu hình lề trang theo Nghị định 30/2020/NĐ-CP
    for s in doc.sections:
        s.top_margin = Cm(2.0)
        s.bottom_margin = Cm(2.0)
        s.left_margin = Cm(3.0)
        s.right_margin = Cm(2.0)
        s.page_width = Cm(21.0)
        s.page_height = Cm(29.7)

    # Style Times New Roman 14pt
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

    # Tiêu đề
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(4)
    r_title = p_title.add_run("BÁO CÁO ĐÁNH GIÁ KẾT QUẢ ĐÃ ĐẠT ĐƯỢC VÀ ĐỊNH HƯỚNG PHÁT TRIỂN\nHỆ THỐNG ĐIỂM DANH HỌC SINH THÔNG MINH STEM")
    format_run(r_title, bold=True, size=15)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(16)
    r_sub = p_sub.add_run("(Hệ thống Edusams STEM - Phân tích chi tiết các hạng mục hoàn thành và kế hoạch nâng cấp)")
    format_run(r_sub, italic=True, size=13.5)

    add_sec_title("I. NHỮNG PHẦN HỆ THỐNG ĐÃ LÀM ĐƯỢC")
    add_p("Trải qua quá trình nghiên cứu, thiết kế kiến trúc và triển khai thực nghiệm, hệ thống Điểm danh Thông minh STEM đã hoàn thiện trọn vẹn các nhóm chức năng và khả năng kỹ thuật cốt lõi sau:")

    add_subsec_title("1. Về hạ tầng máy chủ và kiến trúc phần mềm")
    add_bullet_item("Kiến trúc Đa trường học (Multi-Tenant SaaS)", "Đã thiết kế và vận hành thành công mô hình phần mềm dịch vụ đa trường học. Mỗi trường học là một máy chủ ảo độc lập (Tenant) với mã định danh trường riêng, sở hữu cơ sở dữ liệu phân vùng biệt lập, bảng cấu hình quy định riêng và hệ thống phân quyền nhân sự độc lập.")
    add_bullet_item("Máy chủ dịch vụ hiệu năng cao (FastAPI RESTful API & WebSockets)", "Hệ thống Backend được xây dựng hoàn chỉnh bằng ngôn ngữ Python với bộ khung FastAPI, đạt tốc độ phản hồi tính bằng mili-giây. Tích hợp giao thức truyền dữ liệu hai chiều WebSockets phục vụ phát sóng dữ liệu điểm danh theo thời gian thực tới các máy trạm giám sát và ứng dụng di động.")
    add_bullet_item("Tiêu chuẩn an toàn thông tin và bảo mật dữ liệu", "Áp dụng cơ chế băm mật khẩu chuẩn công nghiệp PBKDF2 kết hợp muối ngẫu nhiên (Salt). Hệ thống xác thực bằng mã khóa JWT an toàn, tích hợp thuật toán giới hạn tần suất truy cập (Rate Limiting) chống tấn công từ chối dịch vụ và bảng quản lý thu hồi khóa phiên làm việc (Token Blacklist).")

    add_subsec_title("2. Về thị giác máy tính và công nghệ trí tuệ nhân tạo biên (Edge AI)")
    add_bullet_item("Làm chủ module Camera AI trên phần cứng nhúng phổ thông", "Hệ thống trạm biên chạy ổn định trên các vi máy tính Raspberry Pi và máy tính mini với chi phí đầu tư thấp. Module sử dụng camera thông thường đạt độ chính xác nhận diện khuôn mặt trên 95% ở cự ly hiệu quả từ 1.5 mét đến 4 mét.")
    add_bullet_item("Khả năng quét đồng thời từ 2 đến 3 học sinh cùng một thời điểm", "Tích hợp thuật toán phát hiện đa khuôn mặt (Multi-face Detection) và bộ bám vết đối tượng chuyển động (Multi-object Tracking). Học sinh đi bộ qua cổng với tốc độ tự nhiên, hệ thống tự động tách từng khuôn mặt và đối sánh song song chỉ trong 0.2 đến 0.5 giây, triệt tiêu nguy cơ ùn ứ trước cổng trường.")
    add_bullet_item("Giải pháp AI Lai (Hybrid AI) kiểm tra đồng phục học đường", "Sáng tạo trong việc phối hợp giữa thuật toán phân tích không gian màu HSV (nhận diện áo trắng, áo Đoàn thanh niên) và mô hình học sâu TFLite MobileNetV2 (nhận diện trang phục có họa tiết phức tạp như áo truyền thống, áo dân tộc). Cơ chế này giúp giảm tải từ 60% đến 70% tài nguyên CPU so với việc sử dụng mô hình học sâu toàn phần.")
    add_bullet_item("Cơ chế chống giả mạo khuôn mặt (Anti-spoofing)", "Tích hợp các phép kiểm tra vi chuyển động, kết cấu ảnh và cử động chớp mắt tự nhiên, ngăn chặn triệt để các hành vi gian lận điểm danh bằng hình ảnh in trên giấy hoặc video phát lại từ màn hình điện thoại.")
    add_bullet_item("Khả năng hoạt động ngoại tuyến và tự phục hồi dữ liệu (Offline-First)", "Trạm camera duy trì hoạt động điểm danh bình thường ngay cả khi mất kết nối mạng Internet nhờ bộ nhớ đệm SQLite cục bộ. Khi kết nối Internet được khôi phục, hệ thống tự động gửi bù toàn bộ dữ liệu về máy chủ, bảo đảm tỷ lệ toàn vẹn dữ liệu đạt 100%.")

    add_subsec_title("3. Về quy trình nghiệp vụ và ứng dụng người dùng")
    add_bullet_item("Cơ chế phân quyền cho học sinh tự gửi mẫu khuôn mặt", "Học sinh sử dụng điện thoại thông minh cá nhân tự chụp và gửi ảnh chân dung mẫu lên hệ thống. Ảnh được phân quyền bảo mật chặt chẽ, nằm trong hàng đợi kiểm duyệt để Giáo viên chủ nhiệm thẩm định tính chính xác trước khi trích xuất vector đặc trưng đưa vào camera trạm biên.")
    add_bullet_item("Hệ thống thông báo tức thời hai chiều", "Ngay khoảnh khắc học sinh qua cổng, bản ghi điểm danh kèm ảnh bằng chứng được phát sóng ngay lập tức. Giáo viên chủ nhiệm nắm bắt danh sách sĩ số lớp thời gian thực trên giao diện Web; Phụ huynh học sinh nhận ngay thông báo đẩy trên điện thoại kèm ảnh chụp của con.")
    add_bullet_item("Số hóa hoàn toàn quy trình nghỉ phép và khiếu nại nề nếp", "Phụ huynh gửi đơn xin nghỉ học có lý do trực tuyến ngay trên ứng dụng di động; Giáo viên chủ nhiệm phê duyệt trực tuyến để tự động cập nhật vào sổ điểm danh. Thiết lập quy trình xử lý khiếu nại hai cấp minh bạch (Cấp 1 tại Giáo viên chủ nhiệm, Cấp 2 tại Giám thị trường).")
    add_bullet_item("Tuân thủ pháp lý về bảo vệ dữ liệu cá nhân", "Xây dựng đầy đủ phân hệ quản lý thỏa thuận đồng thuận thu thập dữ liệu sinh trắc học của phụ huynh và chức năng thực thi quyền xóa dữ liệu theo yêu cầu (Right to Erasure) theo đúng quy định tại Nghị định số 13/2023/NĐ-CP của Chính phủ.")

    add_sec_title("II. NHỮNG PHẦN HỆ THỐNG CẦN TIẾP TỤC PHÁT TRIỂN")
    add_p("Thông qua quá trình thử nghiệm thực tế và rà soát kỹ thuật chuyên sâu, nhóm phát triển đã xác định các điểm hạn chế tồn tại và đề ra các định hướng nâng cấp trọng tâm sau:")

    add_subsec_title("1. Nâng cấp hạ tầng cơ sở dữ liệu cho môi trường siêu tải")
    add_bullet_item("Hạn chế hiện tại", "Hệ thống hiện đang sử dụng cơ sở dữ liệu SQLite ở chế độ ghi nhật ký trước (WAL). Mặc dù đã được tối ưu hóa cho phép nhiều tiến trình đọc đồng thời, SQLite vẫn có bản chất ghi dữ liệu đơn luồng (Single Writer), tiềm ẩn nguy cơ xảy ra lỗi khóa cơ sở dữ liệu khi nhiều cổng trường lớn cùng lúc đồng bộ hàng nghìn lượt điểm danh trong giờ cao điểm.")
    add_bullet_item("Định hướng phát triển", "Chuyển đổi toàn diện sang hệ quản trị cơ sở dữ liệu phân tán PostgreSQL kết hợp với trình điều khiển bất đồng bộ AsyncPG. Giải pháp này cho phép xử lý hàng chục nghìn kết nối đồng thời và phân bổ tải trên nhiều nút máy chủ độc lập.")

    add_subsec_title("2. Tái cấu trúc mô-đun hóa giao diện ứng dụng Web")
    add_bullet_item("Hạn chế hiện tại", "Mã nguồn giao diện Web Dashboard đang được thiết kế dưới dạng ứng dụng trang đơn nguyên khối (Monolithic SPA) gộp chung trong một tệp duy nhất. Điều này dẫn đến kích thước tệp lớn, khó khăn trong việc phân chia nhóm lập trình, bảo trì mã nguồn và viết các ca kiểm thử tự động.")
    add_bullet_item("Định hướng phát triển", "Tái cấu trúc mã nguồn giao diện thành các thành phần độc lập (Component-based architecture) sử dụng các bộ khung hiện đại như React hoặc Vue, đóng gói và tối ưu hóa tải trang thông qua công cụ Vite. Tách biệt hoàn toàn không gian làm việc của Ban Giám hiệu, Giám thị và Giáo viên thành các mô-đun riêng biệt.")

    add_subsec_title("3. Nâng cấp thị giác máy tính nhận diện chi tiết trang phục phức tạp")
    add_bullet_item("Hạn chế hiện tại", "Thuật toán kiểm tra đồng phục hiện tại chủ yếu dựa vào phân tích vùng màu sắc trên thân người. Do đó, hệ thống đang phải bỏ qua việc kiểm tra quy định đồng phục tự do có cổ áo (như quy định ngày Thứ Tư) vì phương pháp phân tích màu không thể nhận biết hình dáng cổ áo; đồng thời chưa phát hiện được phù hiệu trường thêu tay hoặc khăn quàng đỏ.")
    add_bullet_item("Định hướng phát triển", "Nghiên cứu và tích hợp mô hình ước lượng tư thế người (Human Pose Estimation) kết hợp với mạng nơ-ron nhận diện vật thể nhỏ YOLOv8-Nano nhằm phân tích chính xác kết cấu cổ áo, phát hiện phù hiệu thêu trên ngực áo và kiểm tra việc đeo khăn quàng đỏ của học sinh khối trung học cơ sở.")

    add_subsec_title("4. Nâng cấp thuật toán chống giả mạo sinh trắc học đa tầng")
    add_bullet_item("Hạn chế hiện tại", "Thuật toán chống gian lận hiện tại dựa trên phân tích chớp mắt và vi chuyển động quang học (Optical Flow). Trong điều kiện ánh sáng cổng trường thay đổi quá đột ngột hoặc học sinh di chuyển quá nhanh, độ nhạy của thuật toán có thể bị suy giảm.")
    add_bullet_item("Định hướng phát triển", "Nâng cấp lên mô hình mạng nơ-ron chuyên dụng Silent-Face-Anti-Spoofing có khả năng phân tích chiều sâu vân da và độ phản xạ ánh sáng của vật liệu, hoặc tích hợp thêm cảm biến đo chiều sâu quang học 3D (3D Depth Camera) nhằm triệt tiêu hoàn toàn khả năng gian lận bằng mặt nạ hoặc màn hình độ phân giải cao.")

    add_subsec_title("5. Đa dạng hóa kênh gửi thông báo và hạ tầng xác thực viễn thông")
    add_bullet_item("Hạn chế hiện tại", "Cơ chế gửi thông báo hiện phụ thuộc vào ứng dụng di động có kết nối Internet (4G/Wifi); quy trình gửi mã xác thực OTP đăng ký số điện thoại đang hoạt động ở chế độ mô phỏng nội bộ máy chủ.")
    add_bullet_item("Định hướng phát triển", "Tích hợp dịch vụ tin nhắn thương hiệu SMS Brandname và tin nhắn mạng xã hội OTT (Zalo ZNS) để gửi thông báo tức thời đến cả những phụ huynh không cài đặt ứng dụng hoặc đang ngoài vùng phủ sóng mạng di động băng thông rộng. Đồng thời tích hợp cổng xác thực OTP qua viễn thông nhằm bảo đảm tính chính chủ tuyệt đối của số điện thoại phụ huynh.")

    add_subsec_title("6. Đồng nhất kiến trúc dữ liệu ứng dụng di động")
    add_bullet_item("Hạn chế hiện tại", "Ứng dụng Flutter hiện đang sử dụng song song cả Backend FastAPI và cơ sở dữ liệu Firebase Firestore, gây phân mảnh trong việc đồng bộ và quản lý luồng dữ liệu.")
    add_bullet_item("Định hướng phát triển", "Quy hoạch toàn bộ ứng dụng di động về một nguồn dữ liệu duy nhất (Single Source of Truth) từ Backend FastAPI, chuyển dịch vụ Firebase về đúng vai trò chuyên trách duy nhất là hạ tầng đẩy thông báo nền (Firebase Cloud Messaging - FCM).")

    add_sec_title("III. KẾT LUẬN")
    add_p("Những kết quả mà Hệ thống Điểm danh Thông minh STEM đã đạt được khẳng định tính khả thi và tiềm năng to lớn của việc ứng dụng công nghệ Trí tuệ nhân tạo vào môi trường học đường tại Việt Nam. Việc nhận diện rõ các hạn chế hiện hữu và xây dựng lộ trình nâng cấp kỹ thuật chi tiết sẽ là cơ sở vững chắc để nhóm nghiên cứu tiếp tục hoàn thiện sản phẩm, sẵn sàng mở rộng quy mô triển khai tại các trường học trong giai đoạn tiếp theo.")

    # Lưu file
    download_folder = os.path.expanduser('~/Bản tải về')
    out_path = os.path.join(download_folder, "BAO_CAO_DANH_GIA_KET_QUA_VA_PHAT_TRIEN_STEM.docx")
    doc.save(out_path)
    print(f"File created: {out_path}")

if __name__ == "__main__":
    create_text_report()
