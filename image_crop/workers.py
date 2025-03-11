import os
import cv2

from PyQt5.QtCore import QRect
from PyQt5.QtCore import QRunnable, pyqtSignal, QObject, pyqtSlot


class WorkerSignals(QObject):
    finished = pyqtSignal(object, float, float)  # image, scale_x, scale_y
    all_done = pyqtSignal()  # Emitted when all images are processed
    saved = pyqtSignal(str)  # Emits saved file path


class ImageLoaderWorker(QRunnable):
    def __init__(self, path, resize_func):
        super().__init__()
        self.path = path
        self.resize_func = resize_func
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        img = cv2.imread(self.path)
        if img is not None:
            resized_img, sx, sy = self.resize_func(img)
            self.signals.finished.emit(resized_img, sx, sy)


class ImageSaveWorker(QRunnable):
    def __init__(self, path, save_folder, rect, scale_x, scale_y, rotation_angle):
        super().__init__()
        self.path = path
        self.save_folder = save_folder
        self.rect = rect
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.rotation_angle = rotation_angle
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        img = cv2.imread(self.path)
        if img is not None:
            scaled_rect = QRect(
                int(self.rect.x() / self.scale_x),
                int(self.rect.y() / self.scale_y),
                int(self.rect.width() / self.scale_x),
                int(self.rect.height() / self.scale_y)
            )

            (h, w) = img.shape[:2]
            center = (w // 2, h // 2)
            matrix = cv2.getRotationMatrix2D(center, -self.rotation_angle, 1.0)
            rotated_img = cv2.warpAffine(img, matrix, (w, h))

            cropped_img = rotated_img[
                scaled_rect.y():scaled_rect.y() + scaled_rect.height(),
                scaled_rect.x():scaled_rect.x() + scaled_rect.width()
            ]

            base_name = os.path.splitext(os.path.basename(self.path))[0]
            ext = os.path.splitext(self.path)[1]
            new_name = f"{base_name}_cropped{ext}"
            save_path = os.path.join(self.save_folder, new_name)
            success = cv2.imwrite(save_path, cropped_img)

            if success:
                self.signals.saved.emit(save_path)