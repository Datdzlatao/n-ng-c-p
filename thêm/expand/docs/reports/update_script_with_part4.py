import os

# Đọc file hiện tại
script_path = "/home/minhphuc/Diem-danh-STEM/docs/reports/generate_presentation_docx.py"
with open(script_path, "r", encoding="utf-8") as f:
    content = f.read()

part4_code = '''
    # =========================================================================
    # PHẦN IV: CÁC BƯỚC THỰC HIỆN THỰC TẾ TRONG ĐỜI SỐNG HỌC ĐƯỜNG (A - Z)
    # =========================================================================
    add_sec_title("PHẦN IV. QUY TRÌNH 12 BƯỚC THỰC HIỆN THỰC TẾ HỆ THỐNG TRONG ĐỜI SỐNG HỌC ĐƯỜNG (TỪ KHỞI TẠO ĐẾN VẬN HÀNH)")
    add_p("Để minh họa trực quan và thuyết phục Hội đồng Giám khảo về tính khả thi của dự án, phần này mô tả chi tiết toàn bộ chu trình 12 bước thực hiện thực tế ngoài đời sống trường học, từ khâu khởi tạo tài khoản ban đầu cho đến công tác quản trị, điểm danh mỗi sáng và tổng kết thi đua cuối tuần:")

    # Bảng tổng hợp 12 bước thực hiện
    step_table = doc.add_table(rows=13, cols=5)
    step_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    step_table.autofit = False
    
    col_st = [Cm(1.2), Cm(3.2), Cm(3.0), Cm(3.8), Cm(4.8)]
    headers_st = ["Bước", "Tên bước thực hiện", "Người thực hiện", "Giao diện / Thiết bị", "Kết quả đầu ra thực tế"]
    
    for i, h_txt in enumerate(headers_st):
        c = step_table.rows[0].cells[i]
        c.width = col_st[i]
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(h_txt)
        format_run(r, bold=True, size=11.5)
        tcPr = c._element.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="FFF2CC"/>')
        tcPr.append(shd)
        
    step_data = [
        ("1", "Khởi tạo Trường & Admin", "Hiệu trưởng / Admin", "Web Trang chủ (Landing Page)", "Tạo Server trường riêng & cấp Tenant ID"),
        ("2", "Cài đặt Nội quy & Giờ giấc", "Hiệu trưởng", "Web Dashboard BGH", "Thiết lập mốc giờ trễ & lịch áo theo thứ"),
        ("3", "Tạo Lớp & Cấp Mã GVCN", "Hiệu trưởng / Ban KT", "Web Dashboard BGH", "Danh sách lớp & mã mời GV_NGUYEN_HUE"),
        ("4", "Đăng ký HS & Phụ huynh", "Học sinh & Phụ huynh", "Mobile App / Web", "Tài khoản HS, mã HS1001 & liên kết PH"),
        ("5", "Nộp & Duyệt Khuôn mặt", "HS nộp -> GVCN duyệt", "App Mobile -> Web GVCN", "Vector 128D nạp vào CSDL trạm camera"),
        ("6", "Cấu hình Trạm Camera AI", "Kỹ thuật / Giám thị", "Web BGH -> Raspberry Pi", "Kết nối trạm qua Secret Key & cân màu HSV"),
        ("7", "Mở Điểm danh Buổi Sáng", "Giám thị / Tự động", "Bốt gác cổng trường", "Camera live WebRTC kèm khung xanh/đỏ"),
        ("8", "Học sinh Qua Cổng", "Học sinh & Camera AI", "Cổng trường (Khoảng cách 2m)", "Quét 0.2s: Nhận diện, chống gian lận, soi áo"),
        ("9", "Nhận Báo Cáo Tức Thì", "GVCN & Phụ huynh", "Web Lớp học & App Mobile", "Sĩ số lớp nhảy số; App phụ huynh hiện ảnh con"),
        ("10", "Nộp Đơn Nghỉ Phép Online", "Phụ huynh -> GVCN", "Mobile App -> Web GVCN", "Duyệt nghỉ có phép, không bị trừ điểm"),
        ("11", "Xử lý Khiếu nại 2 Cấp", "HS -> GVCN -> Giám thị", "Mobile App & Web Dashboard", "Đối soát ảnh gốc camera, hoàn +5đ thi đua"),
        ("12", "Tổng kết Thi đua Tuần", "Giám thị -> Hiệu trưởng", "Web Dashboard toàn trường", "Ký duyệt điện tử bảng xếp hạng, xuất Excel/PDF")
    ]
    
    for r_idx, r_val in enumerate(step_data, start=1):
        for c_idx, val in enumerate(r_val):
            c = step_table.rows[r_idx].cells[c_idx]
            c.width = col_st[c_idx]
            p = c.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.2
            if c_idx == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(val)
                format_run(r, size=11)
            elif c_idx == 1:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(val)
                format_run(r, bold=True, size=11)
            elif c_idx == 2:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(val)
                format_run(r, size=11)
            elif c_idx == 3:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(val)
                format_run(r, italic=True, size=11)
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                r = p.add_run(val)
                format_run(r, size=11)
                
    tblPr_st = step_table._element.xpath('w:tblPr')
    if tblPr_st:
        borders = parse_xml(f\'\'\'
            <w:tblBorders {nsdecls("w")}>
                <w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:left w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:right w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:insideH w:val="single" w:sz="4" w:space="0" w:color="D3D3D3"/>
                <w:insideV w:val="single" w:sz="4" w:space="0" w:color="D3D3D3"/>
            </w:tblBorders>
        \'\'\')
        tblPr_st[0].append(borders)
        
    add_p("", indent=False, space_before=4, space_after=4)

    # 3 GIAI ĐOẠN CHI TIẾT
    add_subsec_title("GIAI ĐOẠN I: THIẾT LẬP & KHỞI TẠO NỀN TẢNG (SETUP & ONBOARDING)")

    add_subsubsec_title("Bước 1: Khởi tạo Trường học & Đăng ký Tài khoản Quản trị (Hiệu trưởng)")
    add_bullet_item("Người thực hiện", "Hiệu trưởng hoặc Cán bộ Công nghệ thông tin nhà trường.")
    add_bullet_item("Thao tác thực tế", "Truy cập cổng thông tin hệ thống tại địa chỉ website nhà trường -> Bấm nút 'Khám phá Trường học' -> Chọn 'Tạo Không gian Trường Mới' -> Điền tên trường (ví dụ: Trường THPT Nguyễn Huệ), địa phương, cấp học -> Điền thông tin tài khoản Quản trị viên (Tên đăng nhập: hieutruong, Mật khẩu, Số điện thoại).")
    add_bullet_item("Kết quả đầu ra", "Hệ thống tự động cấp mã định danh trường học (School ID: 1), khởi tạo không gian cơ sở dữ liệu phân vùng độc lập (Tenant) và đưa người dùng vào Bảng điều khiển Quản trị toàn trường.")

    add_subsubsec_title("Bước 2: Cài đặt Nội quy Trường học & Lịch Đồng phục theo Tuần")
    add_bullet_item("Người thực hiện", "Hiệu trưởng / Ban Giám hiệu.")
    add_bullet_item("Thao tác thực tế", "Trên Dashboard, vào mục 'Cài đặt Quy chế & Thời khóa biểu': (1) Cài đặt mốc thời gian: Giờ vào trường chuẩn (06:45), Giờ tính đi trễ (07:00), Giờ đóng cổng (07:15); (2) Cài đặt lịch đồng phục trong tuần: Thứ Hai chọn 'Trang phục truyền thống/dân tộc', Thứ Ba/Năm/Sáu chọn 'Áo sơ mi trắng có cổ', Thứ Sáu chọn 'Áo Đoàn thanh niên', Thứ Tư chọn 'Tự do có cổ'; (3) Cài đặt biểu điểm thi đua: Đi trễ trừ 2 điểm, Sai đồng phục trừ 3 điểm, Không đeo thẻ trừ 1 điểm.")
    add_bullet_item("Kết quả đầu ra", "Bảng quy chế điện tử được lưu vào hệ thống, tự động làm thước đo chuẩn để các trạm camera AI căn cứ đánh giá mỗi buổi sáng.")

    add_subsubsec_title("Bước 3: Tạo Danh sách Lớp học & Cấp phát Mã mời Giáo viên Chủ nhiệm")
    add_bullet_item("Người thực hiện", "Hiệu trưởng / Cán bộ Quản trị.")
    add_bullet_item("Thao tác thực tế", "Vào mục 'Quản lý Lớp học' -> Bấm '+ Thêm lớp mới' để tạo danh sách các lớp (10A1, 10A2...). Tiếp tục vào mục 'Mã Mời Nhân sự' -> Sinh chuỗi mã mời bảo mật dành riêng cho giáo viên (ví dụ: GV_NGUYEN_HUE_2026). Giáo viên truy cập web, bấm 'Đăng ký', chọn vai trò 'Giáo viên' và dán mã mời này vào -> Hiệu trưởng bấm 'Chấp thuận' và phân công làm GVCN lớp tương ứng.")
    add_bullet_item("Kết quả đầu ra", "Giáo viên được phân quyền đúng chức năng quản lý lớp mình, không thể can thiệp vào dữ liệu lớp khác.")

    add_subsubsec_title("Bước 4: Đăng ký Tài khoản Học sinh & Phụ huynh (Liên kết Tài khoản)")
    add_bullet_item("Người thực hiện", "Học sinh và Phụ huynh học sinh.")
    add_bullet_item("Thao tác thực tế", "Học sinh tải ứng dụng di động hoặc mở trình duyệt web -> Bấm 'Đăng ký' -> Chọn vai trò 'Học sinh' -> Nhập Họ tên, chọn Lớp 10A1, nhập SĐT -> Hệ thống tự động cấp mã học sinh (ví dụ: HS1001). Phụ huynh tải ứng dụng -> Chọn vai trò 'Phụ huynh' -> Nhập Số điện thoại và nhập Mã học sinh của con để tạo liên kết bảo mật -> Ký xác nhận điện tử bản thỏa thuận đồng thuận thu thập dữ liệu sinh trắc học theo Nghị định số 13/2023/NĐ-CP.")
    add_bullet_item("Kết quả đầu ra", "Thiết lập thành công luồng liên kết thông tin 1-1 an toàn giữa hồ sơ học sinh và điện thoại phụ huynh.")

    add_subsubsec_title("Bước 5: Nộp Ảnh Chân dung Mẫu & GVCN Duyệt Sinh trắc học FaceID")
    add_bullet_item("Người thực hiện", "Học sinh nộp mẫu -> Giáo viên chủ nhiệm kiểm duyệt.")
    add_bullet_item("Thao tác thực tế", "Học sinh sử dụng camera điện thoại tự chụp 1 bức ảnh chân dung rõ nét (chính diện, đủ sáng, không đeo kính râm hay khẩu trang) và bấm 'Gửi phê duyệt FaceID'. Trên máy tính của GVCN, giao diện 'Kiểm duyệt Khuôn mặt Lớp' lập tức hiển thị ảnh kèm tên học sinh -> GVCN kiểm tra đúng học sinh của lớp mình và bấm nút 'Chấp thuận' màu xanh.")
    add_bullet_item("Kết quả đầu ra", "Hệ thống tự động trích xuất vector đặc trưng 128 chiều từ ảnh và nạp vào cơ sở dữ liệu nhận diện tại các trạm camera cổng trường. Nhà trường hoàn toàn không phải mất công tổ chức chụp ảnh thủ công cho từng em.")

    add_subsubsec_title("Bước 6: Cấu hình & Kích hoạt Trạm Camera AI tại Cổng trường")
    add_bullet_item("Người thực hiện", "Cán bộ Kỹ thuật / Giám thị.")
    add_bullet_item("Thao tác thực tế", "Hiệu trưởng vào Web -> 'Trạm Camera' -> Bấm '+ Thêm Trạm' (đặt tên: 'Trạm Cổng Chính 1') -> Nhận mã khóa bí mật Secret Key. Tại cổng trường, cắm Webcam Full HD vào máy tính mini hoặc Raspberry Pi -> Mở terminal chạy lệnh kết nối: python main.py --school_id 1 --secret_key <SECRET_KEY> --api_url https://tenmien.vn. Cán bộ kỹ thuật mở công cụ hsv_picker.html kéo thanh trượt cân chỉnh màu áo trắng trong 1 phút phù hợp với ánh sáng thực tế cổng trường.")
    add_bullet_item("Kết quả đầu ra", "Trạm camera chuyển sang trạng thái đèn xanh ONLINE, sẵn sàng đón học sinh vào sáng hôm sau.")

    add_subsec_title("GIAI ĐOẠN II: VẬN HÀNH ĐIỂM DANH & GIÁM SÁT NỀ NẾP THƯỜNG NHẬT (DAILY OPERATIONS)")

    add_subsubsec_title("Bước 7: Khởi động Trạm Camera Cổng trường Buổi Sáng")
    add_bullet_item("Người thực hiện", "Cán bộ Giám thị hoặc hệ thống tự khởi động theo lịch hẹn giờ.")
    add_bullet_item("Thao tác thực tế", "Đúng 06:15 sáng, hệ thống camera tự động kích hoạt luồng thu hình ảnh. Màn hình bốt trực hiển thị video trực tiếp với các phím tắt nhanh (nhấn 'S' xem sĩ số tức thì, nhấn 'U' tạm tắt soi đồng phục trong ngày lễ hội, nhấn 'T' hiển thị khung bám vết nhiều người).")
    add_bullet_item("Kết quả đầu ra", "Cổng trường được số hóa hoàn toàn, giám thị không cần cầm sổ tay ghi chép.")

    add_subsubsec_title("Bước 8: Học sinh Qua Cổng & Tự động Phân tích Đa tầng")
    add_bullet_item("Người thực hiện", "Học sinh đi bộ qua cổng trường tự nhiên (Khoảng cách 1.5m - 3.5m).")
    add_bullet_item("Thao tác thực tế", "Học sinh không cần dừng lại quẹt thẻ hay áp mặt sát camera. Khi bước qua cổng: (1) Thuật toán Anti-spoofing kiểm tra vi chuyển động và phản quang da mặt để chặn gian lận ảnh/video; (2) Thuật toán nhận diện so khớp vector 128 chiều xác định chính xác danh tính em Nguyễn Văn A trong 0.2 giây; (3) Thuật toán màu HSV quét vùng thân áo xác nhận áo trắng Hợp lệ; (4) Màn hình phát âm thanh BEEP nhẹ kèm khung viền màu Xanh Lá Cây thân thiện.")
    add_bullet_item("Nếu có vi phạm", "Nếu học sinh đi trễ sau 07:00 hoặc mặc áo màu không đúng quy định, màn hình lập tức nhấp nháy khung Đỏ kèm thông báo vi phạm, tự động kích hoạt tính năng Smart Best-shot chụp 2 bức ảnh bằng chứng (1 ảnh cận mặt + 1 ảnh toàn cảnh có khung đỏ) lưu vào hệ thống.")

    add_subsubsec_title("Bước 9: Tiếp nhận Dữ liệu Realtime (Web Giáo viên & Mobile Phụ huynh)")
    add_bullet_item("Người thực hiện", "Giáo viên chủ nhiệm trên lớp & Phụ huynh ở nhà/nơi làm việc.")
    add_bullet_item("Thao tác thực tế", "Tại lớp học, GVCN mở Web Dashboard: Biểu đồ sĩ số lớp tự động nhảy số theo thời gian thực (ví dụ: 39/40 em đã có mặt, 1 em chưa đến) mà không cần nhấn F5 tải lại trang. Cùng lúc đó, trên điện thoại của phụ huynh rung chuông thông báo đẩy: 'Con Nguyễn Văn A đã vào cổng trường lúc 06:48 - Trang phục: Hợp lệ' kèm theo ảnh chụp của con lúc bước qua cổng trường.")
    add_bullet_item("Kết quả đầu ra", "Phụ huynh hoàn toàn an tâm khi biết con đã đến trường bình an; GVCN không tốn một giây nào để gọi tên điểm danh đầu giờ.")

    add_subsec_title("GIAI ĐOẠN III: XỬ LÝ NGHIỆP VỤ PHÁT SINH, KHIẾU NẠI & THI ĐUA (POST-ATTENDANCE)")

    add_subsubsec_title("Bước 10: Nộp & Phê duyệt Đơn xin Nghỉ phép Trực tuyến")
    add_bullet_item("Người thực hiện", "Phụ huynh gửi đơn -> GVCN phê duyệt.")
    add_bullet_item("Thao tác thực tế", "Nếu học sinh bị ốm, phụ huynh mở ứng dụng di động -> Bấm 'Nộp đơn xin nghỉ phép' -> Chọn ngày nghỉ, đính kèm ảnh đơn viết tay hoặc giấy khám bệnh -> Bấm Gửi. GVCN nhận thông báo trên điện thoại hoặc web, xem lý do và bấm nút 'Chấp thuận'.")
    add_bullet_item("Kết quả đầu ra", "Hệ thống tự động cập nhật trạng thái học sinh thành 'Nghỉ có phép' vào sổ điểm danh điện tử, lớp học không bị trừ điểm chuyên cần thi đua.")

    add_subsubsec_title("Bước 11: Quy trình Khiếu nại Nề nếp 2 Cấp (Minh bạch & Nhân văn)")
    add_bullet_item("Người thực hiện", "Học sinh gửi khiếu nại -> GVCN duyệt Cấp 1 -> Giám thị duyệt Cấp 2.")
    add_bullet_item("Thao tác thực tế", "Trong đợt rét mùa đông, học sinh mặc áo khoác ấm che mất áo sơ mi trắng bên trong và bị camera ghi nhận 'Sai đồng phục'. Học sinh mở ứng dụng bấm 'Khiếu nại' kèm lời giải trình: 'Em mặc áo khoác giữ ấm, bên trong vẫn mặc áo trắng'. GVCN mở Dashboard, xem ảnh gốc độ phân giải cao do camera lưu lại, xác nhận đúng hoàn cảnh rét đậm -> Bấm 'Chấp thuận Cấp 1'.")
    add_bullet_item("Kết quả đầu ra", "Hệ thống tự động xóa lỗi vi phạm, tự động hoàn trả +5 điểm thi đua cho lớp học. Các khiếu nại phức tạp sẽ được chuyển tiếp lên Giám thị trưởng duyệt Cấp 2.")

    add_subsubsec_title("Bước 12: Tổng kết Điểm rèn luyện, Thi đua & Xuất Báo cáo Định kỳ")
    add_bullet_item("Người thực hiện", "Giám thị chấm điểm -> Hiệu trưởng ký duyệt điện tử -> Văn phòng xuất file.")
    add_bullet_item("Thao tác thực tế", "Chiều thứ Sáu hàng tuần, hệ thống tự động tổng hợp toàn bộ dữ liệu điểm danh, đi trễ, vi phạm đồng phục và đơn nghỉ phép thành Bảng Xếp Hạng Thi Đua Nề Nếp toàn trường một cách tuyệt đối khách quan. Giám thị kiểm tra bảng tổng kết -> Trình Ban Giám hiệu -> Hiệu trưởng bấm 'Ký duyệt điện tử'. Văn phòng nhà trường bấm nút 'Xuất Excel / PDF' để gửi cho các khối lớp và thông báo trong lễ chào cờ đầu tuần.")
    add_bullet_item("Kết quả đầu ra", "Toàn bộ quy trình nề nếp học đường được số hóa khép kín 100%, tiết kiệm hàng trăm giờ lao động cho thầy cô và xây dựng môi trường học đường văn minh, kỷ cương, hiện đại.")

    add_speech_box("Lời thoại Chốt Quy trình Thực tế", 
                   "Kính thưa Ban Giám khảo, qua 12 bước vận hành thực tế nêu trên, quý Thầy Cô có thể thấy rõ ràng: Hệ thống Điểm danh STEM của chúng em không chỉ là một thuật toán máy tính đơn lẻ, mà là một quy trình chuyển đổi số khép kín, chạm đến từng chủ thể trong nhà trường: Từ Hiệu trưởng ra quyết định, Thầy cô chủ nhiệm giảm tải áp lực, Phụ huynh an tâm mỗi ngày, cho đến các bạn Học sinh được đối xử công bằng, minh bạch trong thi đua nề nếp.")
'''

# Chèn Phần IV vào trước đoạn footer table
marker = "    # --- PHẦN KẾT VÀ CHỮ KÝ ---"
if marker in content:
    new_content = content.replace(marker, part4_code + "\n" + marker)
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Da cap nhat script generate_presentation_docx.py thanh cong!")
else:
    print("Khong tim thay marker de chen!")
