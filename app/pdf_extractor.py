from PyPDF2 import PdfReader
from pdfminer.high_level import extract_text,extract_pages
from pdfminer.layout import LTImage, LTContainer
from pdfminer.image import ImageWriter
import cv2

def get_image(layout_object):
    if isinstance(layout_object, LTImage):
        return layout_object
    if isinstance(layout_object, LTContainer):
        for child in layout_object:
            return get_image(child)
    else:
        return None

def get_pdf_info(path):
    pages = list(extract_pages(path))
    full_text = ""
    for i in range(len(pages)):
        image = get_image(pages[i])
        if image == None:
            reader = PdfReader(path)
            page_pdf = reader.pages[i].extract_text()
            full_text += page_pdf
    return full_text
