import pymupdf

#   读取txt文件内容
def load_txt(file_path):
    with open(file_path, "r", encoding = "utf-8") as f:
        txt_text = {"text":f.read(),
                "page":None
        }
    return [txt_text]

#   读取pdf文件内容
def load_pdf(file_path):
    pages = []

    pdf = pymupdf.open(file_path)

    for i in range(len(pdf)):
        pdf_page = pdf[i]
        pdf_text = pdf_page.get_text()
        pages.append({
            "text": pdf_text,
            "page": i+1
        })
    pdf.close()
    return pages

#   判断文件读取类型
def load_document(file_path):
    if file_path.endswith(".txt"):
        return load_txt(file_path)
    elif file_path.endswith(".pdf"):
        return load_pdf(file_path)
    else:
        return []
    
