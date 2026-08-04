import sys
import types

from client.capture import _camera_indices, _open_opencv


def test_camera_indices_accepts_explicit_number():
    assert _camera_indices(2) == [2]
    assert _camera_indices("3") == [3]


def test_camera_indices_accepts_list_and_csv():
    assert _camera_indices([0, "2"]) == [0, 2]
    assert _camera_indices("0, 4") == [0, 4]


def test_opencv_camera_keeps_flip_on_wrapper(monkeypatch):
    class VideoCapture:
        __slots__ = ("index", "backend", "released")

        def __init__(self, index, backend):
            self.index = index
            self.backend = backend
            self.released = False

        def set(self, *_args):
            return True

        def isOpened(self):
            return True

        def read(self):
            return True, "frame"

        def release(self):
            self.released = True

    fake_cv2 = types.SimpleNamespace(
        VideoCapture=VideoCapture,
        CAP_V4L2=200,
        CAP_PROP_FRAME_WIDTH=3,
        CAP_PROP_FRAME_HEIGHT=4,
    )
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)

    camera = _open_opencv(0, 640, 480, flip=1)

    assert camera.backend == "opencv"
    assert camera.flip == 1
    assert camera.read() == (True, "frame")
    camera.release()
    assert camera.device.released is True
