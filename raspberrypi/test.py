from picamera2 import Picamera2

picam2 = Picamera2()

# Create configuration and strictly define the format as RGB565 (RGBP)
config = picam2.create_still_configuration(main={"size": (1920, 1080), "format": "RGB565"})
picam2.configure(config)

picam2.start()

# Capture the image array directly in RGB565 format
rgbp_frame = picam2.capture_array()
print("Captured frame shape:", rgbp_frame.shape)

picam2.stop()
