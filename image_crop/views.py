from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QFileDialog, QLabel, 
                             QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, 
                             QRubberBand, QHBoxLayout, QToolBar, QAction, QProgressBar, QMainWindow, QStatusBar)
from PyQt5.QtCore import QRect, QPoint, Qt, QSize
from PyQt5.QtCore import QThreadPool, QRunnable, pyqtSignal, QObject


class StackGraphicsView(QGraphicsView):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.origin = QPoint()
        self.rubberBandActive = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.origin = event.pos()
            self.rubberBand.setGeometry(QRect(self.origin, QSize()))
            self.rubberBand.show()
            self.rubberBandActive = True

    def mouseMoveEvent(self, event):
        if self.rubberBandActive:
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rubberBandActive:
            self.rubberBand.hide()
            self.rubberBandActive = False
            rect = self.rubberBand.geometry()
            if self.main_window:
                self.main_window.cropImages(self.mapToImageCoordinates(rect))

    def mapToImageCoordinates(self, rect):
        parent = self.main_window
        if not parent or not parent.imagePixmap:
            return QRect()

        pixmap_item = parent.pixmap_item
        pixmap_rect = pixmap_item.boundingRect()
        scene_rect = self.mapToScene(rect).boundingRect()

        scale_x = parent.imagePixmap.width() / pixmap_rect.width()
        scale_y = parent.imagePixmap.height() / pixmap_rect.height()

        mapped_x = int(scene_rect.x() * scale_x)
        mapped_y = int(scene_rect.y() * scale_y)
        mapped_width = int(scene_rect.width() * scale_x)
        mapped_height = int(scene_rect.height() * scale_y)

        return QRect(mapped_x, mapped_y, mapped_width, mapped_height)