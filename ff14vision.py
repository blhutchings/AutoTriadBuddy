import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from win32 import win32gui
import ctypes
import ctypes.wintypes
from ctypes.wintypes import HWND, RECT, DWORD
from mss import mss
import TreeCoordMerger

# Tesseract 5.0 https://github.com/UB-Mannheim/tesseract/wiki
TESSERACT_PATH = None

# Global Variables
dwmapi = ctypes.WinDLL("dwmapi")

# Minimum size of a menu gui element
MENU_MIN_AREA = 2500  # px

# All coordinates are relative to their parent image
#              H  S  V
THEME_DARK = [[0, 0, 20],
              [180, 10, 60]]

THEME_LIGHT = [[],
               []]

THEME_CLASSIC = [[],
                 []]


def set_tesseract(path):
    global TESSERACT_PATH
    TESSERACT_PATH = path
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Special thanks to 'karlphillip' for helping to find the correct window coordinates
# https://stackoverflow.com/questions/60067002/problems-while-taking-screenshots-of-a-window-and-displaying-it-with-opencv
def window_screenshot(hwnd):
    # If minimized or window does not exist
    if hwnd is None:
        # print("Window handle is None")
        return None, None

    if win32gui.IsIconic(hwnd):
        # print("Window is minimized")
        return None, None

    rect = RECT()
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    dwmapi.DwmGetWindowAttribute(HWND(hwnd), DWORD(DWMWA_EXTENDED_FRAME_BOUNDS), ctypes.byref(rect),
                                 ctypes.sizeof(rect))
    x = rect.left
    y = rect.top
    w = rect.right - x
    h = rect.bottom - y
    rect = [x, y, w, h]

    if w == 0 or h == 0:
        return
    with mss() as sct:
        monitor = {"top": y, "left": x, "width": w, "height": h}
        img_array = np.array(sct.grab(monitor))

    if img_array is None:
        return

    return img_array, rect


def scale_frame(frame, scale):
    width = int(frame.shape[1] * scale)
    height = int(frame.shape[0] * scale)
    dim = (width, height)
    return cv2.resize(frame, dim, interpolation=cv2.INTER_AREA)


# FFXIV Screenshot image processing pipeline
class FF14Vision(object):
    def __init__(self, theme, preprocess_scale=1):
        self.__theme = theme  # UI theme in-game
        self.scale = preprocess_scale  # Scaling percent of frame

        self.coord_tree: TreeCoordMerger = None

        self.__original = None  # Untouched passed frame
        self.__frame = None  # Any image processing will be done with scaled image
        self.__canvas_frame = None  # Original Frame with visualizations

    def new_frame(self, frame):
        self.__original = frame
        self.__frame = scale_frame(frame, self.scale)

        original_height, original_width = self.__original.shape[:2]
        resized_height, resized_width = self.__frame.shape[:2]

        self.coord_tree = TreeCoordMerger.TreeCoordMerger("original", [0, 0, original_width, original_height])
        self.coord_tree.add_scale("scaled", "original", self.scale, [0, 0, resized_width, resized_height])

        self.__canvas_frame = frame.copy()

    def print(self):
        self.coord_tree.print()

    def get_scaled(self):
        return self.__frame

    def get_canvas(self):
        return self.__canvas_frame

    def __slice(self, frame, rect):
        x = rect[0]
        y = rect[1]
        w = rect[2]
        h = rect[3]
        return frame[y:y + h, x:x + w]

    def draw_rect(self, rect, color, thickness):
        x = rect[0]
        y = rect[1]
        w = rect[2]
        h = rect[3]
        self.__canvas_frame = cv2.rectangle(self.__canvas_frame, (x, y), (x + w, y + h), color, thickness)

    def draw_circ(self, coords, radius, color, thickness):
        self.__canvas_frame = cv2.circle(self.__canvas_frame, coords, radius, color, thickness)

    def rect2center(self, rect):
        x1 = rect[0]
        y1 = rect[1]
        x2 = rect[0] + rect[2]
        y2 = rect[1] + rect[3]
        xCenter = int((x1 + x2) / 2)
        yCenter = int((y1 + y2) / 2)
        return [xCenter, yCenter]

    # Detects minimum blob area in binary image
    # Thank you to stateMachine at:
    # https://stackoverflow.com/questions/66287190/how-to-accurately-detect-brown-black-grey-white-on-this-picture-with-opencv/66288066#66288066
    def __area_filter(self, binary_image, min_area):
        # Perform an area filter on the binary blobs:
        componentsNumber, labeledImage, componentStats, componentCentroids = \
            cv2.connectedComponentsWithStats(binary_image, connectivity=4)

        # Get the indices/labels of the remaining components based on the area stat
        # (skip the background component at index 0)
        remainingComponentLabels = [i for i in range(1, componentsNumber) if componentStats[i][4] >= min_area]

        # Filter the labeled pixels based on the remaining labels,
        # assign pixel intensity to 255 (uint8) for the remaining pixels
        filteredImage = np.where(np.isin(labeledImage, remainingComponentLabels) == True, 255, 0).astype('uint8')

        return filteredImage

    # Processes frame to make a mask that only leaves system theme colors
    def __theme_preprocess(self, frame, color_min, color_max, min_area=0):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        blur = cv2.medianBlur(hsv, 3)

        mask = cv2.inRange(blur, np.array(color_min), np.array(color_max))

        # Run a minimum area filter:
        if min_area > 0:
            mask = self.__area_filter(mask, min_area)

        return mask

    def __menus_detect(self, frame):
        mask = self.__theme_preprocess(frame, self.__theme[0], self.__theme[1], min_area=MENU_MIN_AREA)

        contours, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        menus = []
        for contour in contours:
            boundary = cv2.convexHull(contour)

            cv2.fillPoly(mask, [boundary], (255, 255, 255))
            area = cv2.contourArea(boundary)

            # Ignore small areas
            if area < MENU_MIN_AREA: continue

            x, y, w, h = cv2.boundingRect(boundary)

            menus.append([x, y, w, h])

        # List of rectangles of detected menus, biggest to smallest
        return sorted(menus, key=lambda x: int(x[2] * x[3]))

    def __text_detect(self, frame, conf: float, *args):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (1, 1), 0)
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        words = args[0]
        conf = float(conf)

        d = pytesseract.image_to_data(thresh, output_type=Output.DICT)
        n_boxes = len(d['level'])

        match_list = {}
        for i in range(len(words)):
            match_list[words[i]] = []

        for i in range(n_boxes):
            if float(d['conf'][i]) > conf:
                for j in range(len(match_list)):
                    if d['text'][i] == words[j]:
                        match_list.get(words[j]).append([d['left'][i], d['top'][i], d['width'][i], d['height'][i]])
        return match_list

    def find_menutext(self, conf: float, *words, visualize=False):
        # Setup tree and root image
        word_center = {}
        for i in range(len(words)):
            word_center[words[i]] = []

        # Find menu's from scaled image
        for i, menu_rect in enumerate(self.__menus_detect(self.__frame)):
            # Add menu to tree, to draw absolute coordinates
            menu_id = "menu" + str(i)
            self.coord_tree.add_direct(menu_id, "scaled", menu_rect)
            full_menu_rect = self.coord_tree.convert(menu_id)

            # Slice out menu from full frame
            menu = self.__slice(self.__original, full_menu_rect)
            full_menu_id = "full_" + menu_id
            self.coord_tree.add_direct(full_menu_id, "original", full_menu_rect)

            # Draw menu rectangle on canvas
            if visualize:
                self.draw_rect(full_menu_rect, (255, 0, 0), 2)

            # Find Text in menu
            all_text_boxes = self.__text_detect(menu, conf, words)
            # Iterate through all different word detected boxes

            # For each word requested
            for j, word_key in enumerate(all_text_boxes.keys()):
                detected_word_rects = all_text_boxes.get(word_key)
                for h, word_rect in enumerate(detected_word_rects):
                    text_box_id = menu_id + "_" + word_key + "_text_box" + str(h)
                    self.coord_tree.add_direct(text_box_id, full_menu_id, word_rect)
                    full_text_rect = self.coord_tree.convert(text_box_id)
                    center = self.rect2center(full_text_rect)
                    word_center.get(word_key).append(center)

                    if visualize:
                        self.draw_rect(full_text_rect, (0, 255, 0), 2)
                        self.draw_circ(center, 3, (0, 255, 0), 2)
        return word_center
