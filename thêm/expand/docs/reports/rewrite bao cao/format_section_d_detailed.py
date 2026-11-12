import docx
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os

# Cập nhật lại build_full_report_docx.py để có phần D chi tiết từng gạch đầu dòng chuẩn xác
path = "/home/minhphuc/Diem-danh-STEM/docs/reports/rewrite bao cao/build_full_report_docx.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# Thay thế đoạn tạo Section D mục 2 & 3 bằng các gạch đầu dòng rõ ràng, mạch lạc
old_d2_start = '    # D.2 MÔ TẢ CHI TIẾT CÁC MODULE VÀ HÌNH ẢNH GIAO DIỆN'
old_d3_end = '    # D.4 TRẢI NGHIỆM THỰC TẾ'

new_d2_d3_code = '''    # D.2 MÔ TẢ CHI TIẾT CÁC MODULE VÀ HÌNH ẢNH GIAO DIỆN
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
'''

start_idx = code.find(old_d2_start)
end_idx = code.find(old_d3_end)

if start_idx != -1 and end_idx != -1:
    new_code = code[:start_idx] + new_d2_d3_code + code[end_idx:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_code)
    print("✅ Đã cập nhật mã nguồn tạo Section D chuẩn xác từng gạch đầu dòng!")
else:
    print("❌ Không tìm thấy vị trí thay thế!")
