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

target = '    # ==================== PHẦN C ===================='

stem_section_code = '''    # ==================== BẢNG PHÂN TÍCH THÀNH TỐ STEM ====================
    add_subsec_title("Bảng phân tích tích hợp các thành tố liên môn STEM trong dự án:")
    add_p("Hệ thống điểm danh thông minh EduSAMS được xây dựng trên nền tảng tích hợp liên môn chặt chẽ của 4 thành tố giáo dục STEM (Science - Technology - Engineering - Mathematics):", indent=True)

    tbl_stem = doc.add_table(rows=5, cols=3)
    tbl_stem_headers = ["Thành tố STEM", "Kiến thức & Nguyên lý khoa học liên môn", "Hiện thực hóa & Ứng dụng cụ thể trong dự án"]
    tbl_stem_data = [
        [
            "S\\n(Science - Khoa học)",
            "- Nguyên lý quang học màu sắc: Không gian màu hình trụ HSV (Hue - Saturation - Value), cơ chế cảm nhận thị giác của mắt người.\\n- Khoa học giải phẫu & Nhân trắc học: Tỷ lệ tương quan kích thước các bộ phận cơ thể người.\\n- Khoa học thần kinh & Nhận thức nhân tạo: Mô phỏng mạng nơ-ron sinh học trong nhận diện mẫu hình ảnh.",
            "- Chuyển đổi không gian màu BGR sang HSV để nhận diện áo trắng và áo đoàn, loại bỏ ảnh hưởng của ánh sáng thay đổi.\\n- Ước lượng vùng thân người từ vị trí khuôn mặt theo tỷ lệ giải phẫu (rộng thân = 1.8x rộng mặt; cao thân = 7x cao mặt) khi bị che khuất.\\n- Áp dụng mạng nơ-ron sâu để học và nhận diện hoa văn trang phục dân tộc phức tạp."
        ],
        [
            "T\\n(Technology - Công nghệ)",
            "- Công nghệ Trí tuệ nhân tạo (AI) & Thị giác máy tính (Computer Vision).\\n- Công nghệ Điện toán biên (Edge Computing) & IoT.\\n- Công nghệ Web & Ứng dụng di động đa nền tảng hiện đại.",
            "- Sử dụng OpenCV, Haar Cascade, mạng dlib trích xuất vector 128-D, thuật toán Anti-Spoofing và mô hình MobileNetV2 TFLite.\\n- Triển khai trạm camera AI xử lý tại cổng trường, tích hợp bộ nhớ đệm SQLite tự đồng bộ dữ liệu khi có mạng trở lại.\\n- Lập trình Backend FastAPI siêu tốc, giao diện Web Dashboard SPA (HTML5/CSS3/JS) và ứng dụng di động Flutter (Android/iOS)."
        ],
        [
            "E\\n(Engineering - Kỹ thuật)",
            "- Quy trình thiết kế kỹ thuật lặp (EDP - Engineering Design Process).\\n- Kỹ thuật gia công, bố trí và lắp đặt phần cứng trạm quan sát.\\n- Kỹ thuật mạng máy tính & An toàn thông tin học đường.",
            "- Trải qua 03 chu trình lặp hoàn thiện: Thử nghiệm Lab -> Thử nghiệm lớp học -> Triển khai cổng trường giờ cao điểm.\\n- Tính toán góc đặt camera trên vòm cổng trường nghiêng 35° - 45° quét từ trên cao xuống, thiết kế còi/chuông phản hồi âm thanh tại chỗ.\\n- Mã hóa mật khẩu PBKDF2, chữ ký số bảo mật JWT, phân quyền vai trò RBAC và truyền thông WebSocket thời gian thực."
        ],
        [
            "M\\n(Mathematics - Toán học)",
            "- Hình học giải tích không gian & Khoảng cách Euclid (Euclidean Distance).\\n- Đại số tuyến tính & Phép tính tích chập ma trận (Matrix Convolution).\\n- Lý thuyết Xác suất & Thống kê ứng dụng.\\n- Công thức giải tích biến đổi hệ tọa độ màu sắc.",
            "- Đo khoảng cách vector 128 chiều d(x, y) = √(∑(xi - yi)²) so khớp khuôn mặt với ngưỡng d ≤ 0.50.\\n- Phép nhân chập Depthwise Separable Convolution giảm 8 - 9 lần phép tính nhân trong xử lý ảnh.\\n- Cân bằng mẫu class_weight, phân bố gradient HOG, thống kê chuyên cần và trực quan hóa biểu đồ (Chart.js).\\n- Công thức toán học chuyển đổi màu: V = max(R,G,B), S = (V - min(R,G,B)) / V."
        ]
    ]
    format_table(tbl_stem, [Cm(3.0), Cm(6.5), Cm(7.0)], tbl_stem_headers, tbl_stem_data)

    add_p("", indent=False, space_before=0, space_after=6)

    # ==================== PHẦN C ===================='''

if target in code:
    code = code.replace(target, stem_section_code)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    print("✅ Đã chèn thành công Bảng phân tích thành tố STEM vào kịch bản tạo báo cáo!")
else:
    print("❌ Không tìm thấy vị trí chèn!")

