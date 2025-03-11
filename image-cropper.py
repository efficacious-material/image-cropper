import sys
import cv2
import numpy as np
import glob
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QFileDialog, QLabel, 
    QVBoxLayout, QGraphicsScene, QGraphicsPixmapItem, 
    QHBoxLayout, QToolBar, QAction, QProgressBar, QMainWindow, QStatusBar
)

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QThreadPool
from image_crop.views import StackGraphicsView
from image_crop.workers import ImageLoaderWorker, ImageSaveWorker


class ImageCropperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.rotation_angle = 0
        self.original_image = None
        self.pixmap_item = None
        self.imagePixmap = None
        self.folderPath = None
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.original_image_paths = []
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(14)
        self.images_processed = []
        self.scales_x = []
        self.scales_y = []
        self.initUI()

    def initUI(self):
        central_widget = QWidget(self)
        main_layout = QVBoxLayout()

        self.toolbar = QToolBar()
        rotate_left_action = QAction("Rotate Left", self)
        rotate_left_action.triggered.connect(lambda: self.rotateImage(-90))
        rotate_right_action = QAction("Rotate Right", self)
        rotate_right_action.triggered.connect(lambda: self.rotateImage(90))
        self.toolbar.addAction(rotate_left_action)
        self.toolbar.addAction(rotate_right_action)
        main_layout.addWidget(self.toolbar)

        self.label = QLabel("Select a folder containing images")
        main_layout.addWidget(self.label)

        self.btnSelectFolder = QPushButton("Select Folder")
        self.btnSelectFolder.clicked.connect(self.selectFolder)
        main_layout.addWidget(self.btnSelectFolder)

        #self.btnProcess = QPushButton("Process Images")
        #self.btnProcess.clicked.connect(self.processImages)
        #self.btnProcess.setEnabled(False)
        #main_layout.addWidget(self.btnProcess)

        self.graphicsView = StackGraphicsView(self)
        self.scene = QGraphicsScene()
        self.graphicsView.setScene(self.scene)
        main_layout.addWidget(self.graphicsView)

        self.statusBar = QStatusBar(self)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setFormat("%p% complete")
        self.statusBar.addPermanentWidget(self.progress_bar)
        self.statusBar.showMessage("Ready")
        self.setStatusBar(self.statusBar)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.setWindowTitle("Image Cropper")
        self.setGeometry(300, 300, 800, 600)

    def resize_image(self, image, max_dim=1000):
        height, width = image.shape[:2]
        if max(height, width) > max_dim:
            scaling_factor = max_dim / float(max(height, width))
            resized = cv2.resize(image, None, fx=scaling_factor, fy=scaling_factor, interpolation=cv2.INTER_AREA)
            return resized, scaling_factor, scaling_factor
        return image, 1.0, 1.0

    def selectFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folderPath = folder
            self.label.setText(f"Selected Folder: {self.folderPath}")
            #self.btnProcess.setEnabled(True)
            self.processImages()

    def processImages(self):
        if not self.folderPath:
            return

        image_paths = glob.glob(os.path.join(self.folderPath, "*.JPG"))
        self.original_image_paths = image_paths
        self.total_images = len(image_paths)

        self.images_processed.clear()
        self.scales_x.clear()
        self.scales_y.clear()

        if not image_paths:
            self.label.setText("No valid images found!")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(self.total_images)
        self.statusBar.showMessage(f"Processing {self.total_images} images...")

        for path in image_paths:
            print(path)
            worker = ImageLoaderWorker(path, self.resize_image)
            worker.signals.finished.connect(self.collectImageResult)
            self.threadpool.start(worker)

    def collectImageResult(self, image, sx, sy):
        self.images_processed.append(image)
        self.scales_x.append(sx)
        self.scales_y.append(sy)
        processed_count = len(self.images_processed)
        self.progress_bar.setValue(processed_count)
        self.statusBar.showMessage(f"Processed {processed_count}/{self.total_images} images...")
        if len(self.images_processed) == self.total_images:
            self.finalizeProcessing()

    def finalizeProcessing(self):
        if not self.images_processed:
            self.label.setText("No valid images found!")
            return

        self.scale_x = np.mean(self.scales_x) if self.scales_x else 1.0
        self.scale_y = np.mean(self.scales_y) if self.scales_y else 1.0

        overlay = np.mean(np.stack(self.images_processed, axis=0), axis=0).astype(np.uint8)
        self.original_image = overlay
        self.progress_bar.setVisible(False)
        self.statusBar.showMessage(f"{self.total_images} images loaded.")
        self.updateImageDisplay()

    def updateSaveProgress(self, saved_path):
        self.saved_images_count += 1
        self.progress_bar.setValue(self.saved_images_count)
        self.statusBar.showMessage(f"Saved {self.saved_images_count}/{self.total_images} images...")

        if self.saved_images_count == self.total_images:
            self.progress_bar.setVisible(False)
            self.statusBar.showMessage(f"All cropped images saved to 'cropped' folder.")
            self.label.setText(f"Cropped images saved to {os.path.abspath('cropped')}")

    def onImagesProcessed(self, images, scales_x, scales_y):
        if not images:
            self.label.setText("No valid images found!")
            return

        # Compute mean scaling if needed
        self.scale_x = np.mean(scales_x) if scales_x else 1.0
        self.scale_y = np.mean(scales_y) if scales_y else 1.0

        overlay = np.mean(np.stack(images, axis=0), axis=0).astype(np.uint8)
        self.original_image = overlay
        self.updateImageDisplay()

    def updateImageDisplay(self):
        if self.original_image is not None:
            height, width, channel = self.original_image.shape
            bytes_per_line = 3 * width
            q_image = QImage(self.original_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
            self.imagePixmap = QPixmap.fromImage(q_image)

            self.scene.clear()
            self.pixmap_item = QGraphicsPixmapItem(self.imagePixmap)
            self.scene.addItem(self.pixmap_item)
            self.pixmap_item.setTransformOriginPoint(self.imagePixmap.width() / 2, self.imagePixmap.height() / 2)
            self.pixmap_item.setRotation(self.rotation_angle)

            self.graphicsView.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    def resizeEvent(self, event):
        self.updateImageDisplay()
        super().resizeEvent(event)

    def rotateImage(self, angle):
        self.rotation_angle = (self.rotation_angle + angle) % 360
        if self.pixmap_item:
            self.pixmap_item.setRotation(self.rotation_angle)

    def cropImages(self, rect):
        if not self.folderPath or rect.isNull():
            return

        save_folder = os.path.join(f"cropped/{self.folderPath.split('/')[-1]}")
        os.makedirs(save_folder, exist_ok=True)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(self.original_image_paths))
        self.statusBar.showMessage("Saving cropped images...")

        self.saved_images_count = 0

        # Start workers for parallel processing & saving
        for path in self.original_image_paths:
            worker = ImageSaveWorker(
                path=path,
                save_folder=save_folder,
                rect=rect,
                scale_x=self.scale_x,
                scale_y=self.scale_y,
                rotation_angle=self.rotation_angle
            )
            worker.signals.saved.connect(self.updateSaveProgress)
            self.threadpool.start(worker)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageCropperApp()   
    window.show()
    sys.exit(app.exec_())
