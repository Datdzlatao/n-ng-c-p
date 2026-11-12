import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

path = "/home/minhphuc/Diem-danh-STEM/docs/reports/rewrite bao cao/build_new_role_based_report.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# Tìm đoạn sau phần B và trước Bảng phân tích thành tố STEM
old_section_b_end = '    # ==================== BẢNG PHÂN TÍCH THÀNH TỐ STEM ===================='

new_content = '''    # ==================== LÝ DO CHỌN ĐỀ TÀI & TÍNH CẤP THIẾT ====================
    add_subsec_title("1. Lý do chọn đề tài và tính cấp thiết:")
    add_p("Trường Phổ thông Dân tộc Nội trú THPT Tỉnh Lai Châu có đặc thù là môi trường giáo dục nội trú với đông đảo học sinh thuộc nhiều đồng bào dân tộc thiểu số khác nhau trên địa bàn tỉnh. Trong công tác quản lý học đường hàng ngày, hai hoạt động quan trọng vào đầu mỗi buổi học hiện nay vẫn phần lớn được thực hiện theo phương thức thủ công:", indent=True)
    add_p("- Điểm danh truyền thống: Giáo viên chủ nhiệm hoặc cán bộ lớp phải gọi tên và kiểm đếm sĩ số trực tiếp đầu mỗi tiết học. Quy trình này chiếm mất từ 3 đến 5 phút mỗi tiết (tương đương 15 đến 25 giờ giảng dạy bị lãng phí mỗi năm học cho một lớp), đồng thời dễ xảy ra sai sót hoặc điểm danh hộ.", indent=True)
    add_p("- Kiểm tra nề nếp trang phục: Nhà trường có quy định nề nếp trang phục rất rõ ràng nhằm giữ gìn bản sắc văn hóa và kỷ cương học đường (mặc trang phục truyền thống dân tộc vào Thứ Hai chào cờ, áo trắng vào Thứ Ba và Thứ Năm, áo Đoàn thanh niên vào Thứ Sáu). Việc kiểm tra hoàn toàn phụ thuộc vào việc giám thị đứng quan sát bằng mắt tại cổng trường, dễ bị bỏ sót trong giờ cao điểm, mang tính cảm tính và không có hình ảnh bằng chứng lưu trữ khi cần đối chiếu.", indent=True)
    add_p("- Nhu cầu kết nối của gia đình: Phần lớn phụ huynh học sinh sinh sống tại các thôn bản vùng sâu, vùng xa, điều kiện đi lại khó khăn nên việc gửi con học nội trú luôn kèm theo nỗi lo lắng về giờ giấc và sự an toàn của con em mình.", indent=True)
    add_p("Trong khi đó, các giải pháp máy chấm công vân tay hoặc camera AI thương mại trên thị trường hiện nay có chi phí đầu tư rất đắt đỏ (từ 20 đến 45 triệu đồng/trạm), đòi hỏi phí duy trì hàng năm cao và đặc biệt là không có tính năng tự động kiểm tra nề nếp trang phục theo lịch tuần phù hợp với đặc thù trường nội trú.", indent=True)
    add_p("Xuất phát từ thực tiễn trên, nhóm nghiên cứu đã vận dụng các kiến thức liên môn STEM để nghiên cứu và chế tạo thành công: 'HỆ THỐNG ĐIỂM DANH THÔNG MINH BẰNG QR CODE, NHẬN DIỆN KHUÔN MẶT VÀ KIỂM TRA TRANG PHỤC TỰ ĐỘNG'. Dự án hướng tới mục tiêu tự động hóa hoàn toàn công tác điểm danh và giám sát nề nếp, tiết kiệm ngân sách nhà trường, giải phóng thời gian cho giáo viên và kết nối thông tin tức thời, minh bạch tới từng phụ huynh học sinh.", indent=True)

    # ==================== BẢNG PHÂN TÍCH THÀNH TỐ STEM ====================
    add_subsec_title("2. Bảng phân tích tích hợp các thành tố liên môn STEM trong dự án:")'''

if old_section_b_end in code:
    code = code.replace(old_section_b_end + '\n    add_subsec_title("Bảng phân tích tích hợp các thành tố liên môn STEM trong dự án:")', new_content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    print("✅ Đã chèn thành công Mục Lý do chọn đề tài trước Bảng STEM vào script!")
else:
    print("❌ Không tìm thấy vị trí chèn!")

