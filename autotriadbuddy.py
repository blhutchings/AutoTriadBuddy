import time
import cv2
import configparser
import pyautogui
import win32con
from win32 import win32api
from win32 import win32gui

import ff14vision
import ff14vision as vision
import triadbuddyvision as triadbuddy
pyautogui.FAILSAFE = False

# Read in required settings
configParser = configparser.RawConfigParser()
configFilePath = r'config.txt'
configParser.read(configFilePath)

# Config variables
ff14vision.set_tesseract(configParser.get('Required', 'tesseract_path'))
DECK_NAME =  configParser.get('Required', 'deck_name')
DISPLAY_SCALE_FACTOR = float(configParser.get('Required', 'display_scale')) # ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
REQUIRED_WINS = int(configParser.get('Required', 'required_wins'))  # -1 to play forever

# Settings
VISUALIZE = False

# FFXIV Game Window Info
APP_NAME = 'FINAL FANTASY XIV'
APP_CLASS = 'FFXIVGAME'  # win32gui.GetClassName
win_hwnd = win32gui.FindWindow(APP_CLASS, APP_NAME)  # FFXIV Window Handle

# Global variables
PROCESSOR = triadbuddy.AutoTriadBuddy(vision.THEME_DARK, 0.5)  # Class instance to process frames
WINDOW_RECT = []  # Rectangle of windows absolute location
FRAME_RATE = 1

# Statistics
games_played = 0
current_wins = 0
START_TIME = time.time()  # Program Start Time

# Game State
game_state = 0
last_state = 0  # Keeps track of the last state in the loop

#          STATE NAME            ID    DESCRIPTION
STATES = ['Out of Menu',  # 0   Out of Menu - double click NUM 0 - Infinite
          'Talk Menu',  # 1   Talk Menu - "triple Triad Challenge, spam left click until "challenge" - Infinite
          'Match Registration',  # 2   Match Registration - click "challenge" - 30 seconds
          'Deck Selection',  # 3   Deck Selection - click "Optimized" - 30 seconds
          'Playing',  # 4   Playing - playing the game - Max 300 seconds
          'Finish Menu',  # 5   Finish Menu - Record stats, Rematch = 2(Match Registration) or Done = 6
          'Done',  # 6   Program loop has finished and is now exiting
          'Unknown']  # -1  Something went wrong, exit program


def main():
    global win_hwnd
    global PROCESSOR
    global WINDOW_RECT
    global FRAME_RATE

    try:
        # Each Frame
        while True:
            start_time = time.time()
            win_hwnd = win32gui.FindWindow(APP_CLASS, APP_NAME)

            # If window does not exist, attempt to find it
            if win_hwnd == 0:
                print(APP_NAME, " does not exist")
                time.sleep(0.25)
                continue

            # Valid Window - Process
            if not valid_window(win_hwnd):
                print("'FINAL FANTASY XIV' maximized or not focused, click the game window to focus")
                time.sleep(0.25)
                continue

            # Take Screenshot and get screen coordinates
            frame, _ = vision.window_screenshot(win_hwnd)
            WINDOW_RECT = win32gui.GetWindowRect(win_hwnd) # DPI sensitive coordinates
            PROCESSOR.new_frame(frame)

            # region Game State Cases
            if game_state == 1:  # Talk Menu
                if last_state != game_state:
                    print("State: ", STATES[1])
                talk_menu()

            elif game_state == 2:  # Match Registration
                if last_state != game_state:
                    print("State: ", STATES[2])
                match_registration()

            elif game_state == 3:  # Deck Selection
                if last_state != game_state:
                    print("State: ", STATES[3])
                deck_selection()

            elif game_state == 4:  # Playing
                if last_state != game_state:
                    print("State: ", STATES[4])
                playing()

            elif game_state == 5:  # Finished Menu
                print("State: ", STATES[5])
                finished_menu()

            elif game_state == 6:  # Program finished normally
                print("State: ", STATES[6])
                done()

            elif game_state == 0:  # Start
                print("State: ", STATES[0])
                start()

            else:  # Unknown
                print("State: ", STATES[-1])
                print("Exiting program")
                break
            # endregion

            if VISUALIZE:
                canvas_frame = PROCESSOR.get_canvas()
                scaled_canvas_frame = vision.scale_frame(canvas_frame, 0.5)
                cv2.imshow(APP_NAME + " Monitor", scaled_canvas_frame)

            # Calculate Frame Rate
            end_time = time.time()
            FRAME_RATE = FRAME_RATE + int(1 / (end_time - start_time))
            # print("FPS: {:.2f}".format(FRAME_RATE))

            # Display
            #######################################
            if cv2.waitKey(FRAME_RATE) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
            time.sleep(FRAME_RATE / 1000)
            FRAME_RATE = 1
    except KeyboardInterrupt:
        print("KeyboardInterrupt - Exiting")
        cv2.destroyAllWindows()
        done()
        exit(1)

    except Exception as e:
        print(e)


# Game window must be maximized
# returns True if valid window, false if not
def valid_window(hwnd):
    return True

    #tup = win32gui.GetWindowPlacement(hwnd)
    #if tup[1] == win32con.SW_SHOWMAXIMIZED: #and hwnd == win32gui.GetForegroundWindow():
    #    return True
    #else:
    #    return False

def left_click():
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
    time.sleep(.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)


def drag_card(pickup, putdown):
    move_to(pickup[0], pickup[1])
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
    time.sleep(.1)
    move_to(putdown[0], putdown[1])
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

def move_to(x, y):
    true_x, true_y = __screen_point(x, y)
    pyautogui.moveTo(true_x, true_y)

# Converts absolute coordinates from screenshot to virtual coordinates (Aka, the correct spot)
def __screen_point(x, y):
    screen_x = int(x * DISPLAY_SCALE_FACTOR) + WINDOW_RECT[0]
    screen_y = int(y * DISPLAY_SCALE_FACTOR) + WINDOW_RECT[1]
    return screen_x, screen_y

# Message if button location is not found
def button_not_found(name):
    print("'", name, "' not found, trying again")

# Message if button location is found
def button_found(name):
    print("Found '", name, "' button")


# State Functions
def start():  # 0
    global game_state
    global last_state
    game_state = 1
    last_state = 0

    delay = 5 # seconds

    print("Time: ", START_TIME)
    print("Goal: ", REQUIRED_WINS)
    print("Staring in", delay, "seconds")
    for i in range(delay, 0, -1):
        print(i,"!")
        time.sleep(1)
    print("GO!!!")


def talk_menu():  # 1
    global PROCESSOR
    global FRAME_RATE
    global game_state
    global last_state
    last_state = 1

    button = "Triple"

    found = PROCESSOR.find_menutext(0, button, visualize=True)
    coords = found.get(button)
    if not any(coords):
        button_not_found(button)
        FRAME_RATE = FRAME_RATE + 500  # Wait 0.5 seconds
    else:
        button_found(button)
        coords = coords[0]
        move_to(coords[0], coords[1])
        left_click()
        time.sleep(0.50)
        left_click()

        # Continue to next stage on next loop
        game_state = 2


def match_registration():  # 2
    global PROCESSOR
    global FRAME_RATE
    global game_state
    global last_state
    last_state = 2
    button = "Challenge"

    found = PROCESSOR.find_menutext(0, button, visualize=True)
    coords = found.get(button)
    if not any(coords):
        button_not_found(button)
        FRAME_RATE = FRAME_RATE + 500  # Wait 0.5 seconds
    else:
        button_found(button)
        coords = coords[0]
        move_to(coords[0], coords[1])
        left_click()

        # Continue to next stage on next loop
        game_state = 3


def deck_selection():  # 3
    global PROCESSOR
    global FRAME_RATE
    global game_state
    global last_state
    last_state = 3

    found = PROCESSOR.find_menutext(0, DECK_NAME, visualize=True)
    coords = found.get(DECK_NAME)
    if not any(coords):
        button_not_found(DECK_NAME)
        FRAME_RATE = FRAME_RATE + 500  # Wait 0.5 seconds
    else:
        button_found(DECK_NAME)

        coords = coords[0]  # The first word it detected
        move_to(coords[0], coords[1])
        left_click()

        # Continue to next stage on next loop
        game_state = 4


def playing():  # 4
    global PROCESSOR
    global FRAME_RATE
    global games_played
    global current_wins
    global game_state
    global last_state
    last_state = 4

    coords = PROCESSOR.find_card_coords(visualize=True)
    if not coords:
        print("Cards not detected, trying again")

        found = PROCESSOR.find_menutext(0.0, "WIN!", "LOSE...", "DRAW")
        if any(found.get("WIN!")):
            print("Results: Won")
            games_played = games_played + 1
            current_wins = current_wins + 1

            # Continue to next stage on next loop
            game_state = 5
        elif any(found.get("LOSE...")):
            print("Results: Lost")
            games_played = games_played + 1
            # Continue to next stage on next loop
            game_state = 5
        elif any(found.get("DRAW")):
            print("Results: Draw")
            games_played = games_played + 1

            # Continue to next stage on next loop
            game_state = 5
        FRAME_RATE = FRAME_RATE + 500  # 0.5 Seconds
    else:
        print("Moving cards")
        pickup = coords[0]
        putdown = coords[1]
        drag_card(pickup, putdown)


def finished_menu():  # 5
    global PROCESSOR
    global game_state
    global last_state
    last_state = 5
    exit_button = "Quit"
    replay_button = "Rematch"

    print("Game: ", games_played, " | Progress: ", current_wins, "/", REQUIRED_WINS)

    if current_wins == REQUIRED_WINS:
        print("Goal Achieved...")
        found = PROCESSOR.find_menutext(0, exit_button, visualize=True)
        coords = found.get(exit_button)
        if not any(coords):
            button_not_found(exit_button)
        else:
            button_found(exit_button)

            coords = coords[0]  # The first word it detected
            move_to(coords[0], coords[1])
            left_click()

            # Finish
            game_state = 6
    else:
        print("Replaying...")
        found = PROCESSOR.find_menutext(0, replay_button, visualize=True)
        coords = found.get(replay_button)
        if not any(coords):
            button_not_found(replay_button)
        else:
            button_found(replay_button)

            coords = coords[0]  # The first word it detected
            move_to(coords[0], coords[1])
            left_click()

            # Finish
            game_state = 2


def done():  # 6
    print("Statistics")
    print("Games Played: ", games_played)
    print("Games Won: ", current_wins)
    print("Games Lost: ", games_played - current_wins)
    print("Time Elapsed: ", int(time.time() - START_TIME), " seconds")
    print("Now Exiting")


if __name__ == "__main__":
    main()
    exit(1)
