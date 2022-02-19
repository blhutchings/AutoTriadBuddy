# AutoTriadBuddy - Fully automated Triple Triad in a closed loop
- Uses FFTriadBuddy to calculate what cards to be played and uses OpenCV image processing to calcuate where to move cards.
- Uses Tesseract OCR to find menu text which allows for a closed loop

### Usage
---
- **Download **
- **Setup config and read requirements and notes**, open FFXIV and find NPC to play with. Navigate to the menu box with "Triple Triad Challenge, Small Talk, Nothing, etc...". You can now start autotriadbuddy.exe

### Notes
---
- This program moves and controls your mouse. Do not move your mouse during menu navigation as it might break. **Moving the mouse while the Triple triad game is playing is OK, otherwise don't.**

### Requirements
---
- **Must use Dark Theme ingame**
- **Game must a decent resolution, tesseract might fail to detect words if too small*
- [FFTriadBuddy] or Dalumud Plugin - Draws outlines around card and optimal location
- [Tesseract 5.0] - Used to detect button text and results of game

### Config Setup
---
**The number of wins before the program halts, -1 never ends**

required_wins = -1

**Path to Tesseract install**

tesseract_path = C:\Program Files\Tesseract-OCR\tesseract.exe

**Deck name that will be automatically selected**

deck_name = Optimized

**Display scale - Leave at 1 if monitors are all the same resoultion, otherwise look at 'Display Scaling for multiple displays'**

display_scale = 1

[FFTriadBuddy]: <https://github.com/MgAl2O4/FFTriadBuddy>
[Tesseract 5.0]: <https://github.com/UB-Mannheim/tesseract/wiki>

### 'Display Scaling' for different resolution multiple displays
---
If you have multiple displays, for example a 1440p (2560 x 1440) main display and 1080p (1080 x 1920) display, you might have set your scaling factor to 125% in display settings in windows for the 1440p monitor while leaving the 1080p scale at 100%.

- If you were to have your FFXIV game window on that 1080p monitor, you will have to set your the scale to 1.25
- If you were to have your FFXIV game window on that 1440p monitor, you will have to set your the scale to 1

If this is not set correctly, the mouse position will be off by some scale factor
