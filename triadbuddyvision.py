import ff14vision
import numpy as np
import cv2


class AutoTriadBuddy(ff14vision.FF14Vision):
    RED_BORDER = [[-175, 220, 200], [10, 255, 255]]
    YELLOW_BORDER = [[25, 220, 200], [40, 255, 255]]
    GREEN_BORDER = [[45, 220, 200], [70, 255, 255]]

    BLUE_BORDER = [[100, 220, 200], [120, 255, 255]]

    def __init__(self, theme, preprocess_scale=1):
        ff14vision.FF14Vision.__init__(self, theme, preprocess_scale)

    def __pickup_card_mask(self, frame, hsv_frame):
        # Create Red Mask
        red_min = np.array(AutoTriadBuddy.RED_BORDER[0])
        red_max = np.array(AutoTriadBuddy.RED_BORDER[1])
        maskR = cv2.inRange(hsv_frame, red_min, red_max)

        # Create Yellow Mask
        yellow_min = np.array(AutoTriadBuddy.YELLOW_BORDER[0])
        yellow_max = np.array(AutoTriadBuddy.YELLOW_BORDER[1])
        maskY = cv2.inRange(hsv_frame, yellow_min, yellow_max)

        # Create Green Mask
        green_min = np.array(AutoTriadBuddy.GREEN_BORDER[0])
        green_max = np.array(AutoTriadBuddy.GREEN_BORDER[1])
        maskG = cv2.inRange(hsv_frame, green_min, green_max)

        # Merge masks
        maskRY = cv2.bitwise_or(maskR, maskY)
        maskRYG = cv2.bitwise_or(maskRY, maskG)
        return cv2.bitwise_and(frame, frame, mask=maskRYG)

    def __putdown_card_mask(self, frame, hsv_frame):
        # Create Blue Mask
        blue_min = np.array(AutoTriadBuddy.BLUE_BORDER[0])
        blue_max = np.array(AutoTriadBuddy.BLUE_BORDER[1])
        mask = cv2.inRange(hsv_frame, blue_min, blue_max)
        return cv2.bitwise_and(frame, frame, mask=mask)

    def __card_detect(self, mask):
        # Detect Contours
        img_gray = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        contours, hierarchy = cv2.findContours(img_gray, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) > 0:
            # Sort contours by area
            contour = max(contours, key=cv2.contourArea)

            # If the area is greater then 400px, that's the card. Pretty big error if equates to true but is not the card
            if cv2.contourArea(contour) > 400:
                # Draw an approximation of the card outline
                approx = cv2.approxPolyDP(contour, 0.01 * cv2.arcLength(contour, True), True)
                x, y, w, h = cv2.boundingRect(approx)

                # Return center of contour if card exists
                return [x, y, w, h]

        # Return -1 -1 if there is no contour
        return []

    def find_card_coords(self, visualize=False):
        # HSV Color Space
        hsv = cv2.cvtColor(self.get_scaled(), cv2.COLOR_BGR2HSV)

        # Get masks
        pickup_mask = self.__pickup_card_mask(self.get_scaled(), hsv)
        putdown_mask = self.__putdown_card_mask(self.get_scaled(), hsv)

        pickup_rect = self.__card_detect(pickup_mask)
        putdown_rect = self.__card_detect(putdown_mask)

        if pickup_rect and putdown_rect:
            self.coord_tree.add_direct("pickup_rect", "scaled", pickup_rect)
            self.coord_tree.add_direct("putdown_rect", "scaled", putdown_rect)

            full_pickup_rect = self.coord_tree.convert("pickup_rect")
            full_putdown_rect = self.coord_tree.convert("putdown_rect")

            pickup_center = self.rect2center(full_pickup_rect)
            putdown_center = self.rect2center(full_putdown_rect)

            if visualize:
                self.draw_rect(full_pickup_rect, (0, 0, 0), 10)
                self.draw_rect(full_putdown_rect, (0, 0, 0), 10)
                self.draw_circ(pickup_center, 2, (0, 255, 0, 2), 2)
                self.draw_circ(putdown_center, 2, (0, 255, 0), 2)

        # Return coords of pickup and putdown card locations
            return [pickup_center, putdown_center]
        else:
            return []
