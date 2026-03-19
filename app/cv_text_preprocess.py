import cv2
import numpy as np

def cv_preprecess(img_path):
    img = cv2.imread(img_path)

    kernel = np.ones((3, 3), np.uint8)

    # Preprocessing
    # Loading and removing noise

    img = cv2.bilateralFilter(img,25,70,70)


    # Increasing sharpness
    blurred = cv2.GaussianBlur(img, (5,5), 5.0)
    img = cv2.addWeighted(img, 1.0 + 1.5, blurred, -1.5, 0)

    # Binarization
    img = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    ret3,img = cv2.threshold(img,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)

    cv2.imwrite("DocRes/restored/current_check.jpg",img)