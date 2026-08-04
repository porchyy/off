import cv2

# บังคับเรียกใช้กล้องผ่านระบบ V4L2 Backend ของ Linux
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

# บังคับโครงสร้างการจัดเรียงพิกเซลเป็น FOURCC ของ RGBP (ย่อมาจาก RGB565 Packed)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'RGB3'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2304)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1296)

ret, frame = cap.read()
if ret:
    print("โครงสร้างไบนารีอาร์เรย์ที่ดึงได้สำเร็จ:", frame.shape)
    # บัฟเฟอร์ข้อมูลในเฟรมนี้จะเป็นคู่บิต แดง-เขียว-น้ำเงิน (16 บิต) ทันที
    
cap.release()
