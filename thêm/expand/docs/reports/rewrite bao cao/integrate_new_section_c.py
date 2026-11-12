import docx
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

def create_integrated_doc():
    orig_path = "/home/minhphuc/Diem-danh-STEM/docs/reports/rewrite bao cao/BÁO CÁO DỰ ÁN STEM.docx"
    sec_c_path = "/home/minhphuc/Diem-danh-STEM/docs/reports/rewrite bao cao/PHAN_C_QUY_TRINH_THIET_KE_CHUAN_MOI.docx"
    output_path = "/home/minhphuc/Diem-danh-STEM/docs/reports/rewrite bao cao/BÁO CÁO DỰ ÁN STEM - CẬP NHẬT PHẦN C.docx"

    orig_doc = Document(orig_path)
    c_doc = Document(sec_c_path)

    start_c = None
    end_c = None
    for i, p in enumerate(orig_doc.paragraphs):
        txt = p.text.strip()
        if "C. QUY TRÌNH THIẾT KẾ" in txt and start_c is None:
            start_c = i
        elif start_c is not None and any(txt.startswith(x) for x in ["D. ", "D."]):
            end_c = i
            break

    new_doc = Document()
    for s in new_doc.sections:
        s.top_margin = Cm(2.5)
        s.bottom_margin = Cm(2.5)
        s.left_margin = Cm(3.0)
        s.right_margin = Cm(2.0)
        s.page_width = Cm(21.0)
        s.page_height = Cm(29.7)

    def format_run(r, font_name="Times New Roman", size=14, bold=False, italic=False, color=RGBColor(0,0,0)):
        r.font.name = font_name
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.color.rgb = color

    # 1. Các đoạn trước C
    for i in range(start_c):
        p_orig = orig_doc.paragraphs[i]
        p_new = new_doc.add_paragraph()
        p_new.alignment = p_orig.alignment
        p_new.paragraph_format.first_line_indent = p_orig.paragraph_format.first_line_indent
        p_new.paragraph_format.space_before = p_orig.paragraph_format.space_before
        p_new.paragraph_format.space_after = p_orig.paragraph_format.space_after
        p_new.paragraph_format.line_spacing = p_orig.paragraph_format.line_spacing or 1.35
        for r_orig in p_orig.runs:
            r_new = p_new.add_run(r_orig.text)
            f_size = r_orig.font.size.pt if r_orig.font.size else 14
            format_run(r_new, "Times New Roman", f_size, r_orig.bold, r_orig.italic)

    # 2. Phần C mới
    for child in c_doc.element.body:
        if child.tag.endswith('sectPr'):
            continue
        new_doc.element.body.append(child)

    # 3. Các đoạn từ D trở đi
    for i in range(end_c, len(orig_doc.paragraphs)):
        p_orig = orig_doc.paragraphs[i]
        p_new = new_doc.add_paragraph()
        p_new.alignment = p_orig.alignment
        p_new.paragraph_format.first_line_indent = p_orig.paragraph_format.first_line_indent
        p_new.paragraph_format.space_before = p_orig.paragraph_format.space_before
        p_new.paragraph_format.space_after = p_orig.paragraph_format.space_after
        p_new.paragraph_format.line_spacing = p_orig.paragraph_format.line_spacing or 1.35
        for r_orig in p_orig.runs:
            r_new = p_new.add_run(r_orig.text)
            f_size = r_orig.font.size.pt if r_orig.font.size else 14
            format_run(r_new, "Times New Roman", f_size, r_orig.bold, r_orig.italic)

    new_doc.save(output_path)
    print(f"✅ Đã tạo thành công file báo cáo tích hợp đầy đủ tại: {output_path}")

if __name__ == "__main__":
    create_integrated_doc()
