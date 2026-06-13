"""
Type or Die - Auto-typing Bot
================================
Purely local DB — no AI, no API keys needed.

Setup:
    pip install mss pillow pytesseract pyautogui keyboard opencv-python pyperclip

    Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki

Hotkeys:  F6 = Start/Pause   F8 = Stop   F5 = Calibrate question region
"""

import pickle
import time
import threading
import re
import sys
import os
import difflib

try:
    import mss
    import cv2
    import numpy as np
    from PIL import Image
    import pytesseract
    import pyautogui
    import keyboard
    import pyperclip
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e}")
    print("Run: pip install mss pillow pytesseract pyautogui keyboard opencv-python pyperclip")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────

def get_tesseract_path():
    """Return path to tesseract.exe – works when frozen by PyInstaller."""
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    candidate = os.path.join(base_dir, "tesseract.exe")
    if os.path.exists(candidate):
        return candidate
    
    default = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default):
        return default
    
    raise FileNotFoundError("tesseract.exe not found. Place it next to the executable.")

TESSERACT_PATH = get_tesseract_path()
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

QUESTION_REGION_PCT = (0.25, 0.00, 0.75, 0.11)

SCAN_INTERVAL    = 0.3
ANSWER_DELAY     = 0.2
MIN_QUESTION_LEN = 6

HOTKEY_TOGGLE = "f6"
HOTKEY_STOP   = "f8"

# ── Answer Database ───────────────────────────────────────────────────────────

ANSWERS_DB = {
    "name a disney princess": "VANELLOPE VON SCHWEETZ",
    "name a breakfast drink": "AVOCADO SMOOTHIE",
    "name a country": "THE FEDERATED STATES OF MICRONESIA",
    "name something that has roots": "MEDIUM DENSITY FIBREBOARD",
    "name a type of cheese": "PARMIGIANOREGGIANO",
    "name a minecraft monster": "BABY ZOMBIE VILLAGER",
    "name a social media platform": "FACEBOOK MESSENGER",
    "name one of the four seasons": "AUTUMN",
    "name a standard unit of measurement": "CENTIMETER",
    "name a word that rhymes with horse": "REINFORCE",
    "name a famous war": "SIERRA LEONE CIVIL WAR",
    "name a planet in our solar system": "MERCURY",
    "name a summer olympic sport": "ONE HUNDRED METER SPRINT",
    "name a popular dessert (food)": "CHOCOLATECHIPCOOKIEDOUGH",
    "name an animal that is usually a pet": "BEARDED DRAGON",
    "name a common color": "BRIGHT YELLOW",
    "name something in a taco": "SIRACHA SAUCE",
    "name a character you would see at disneyworld": "ALICE IN WONDERLAND",
    "name a type of snake": "WESTERN DIAMOND BLACK RATTLESNAKE",
    "name something you would find in outer space": "INTERNATIONAL SPACE STATION",
    "name a common superpower": "SUPERSTRENGTH",
    "name a religion": "BUSHONGOMYTHOLOGY",
    "name a popular swimming stroke": "BREASTSTROKE",
    "name a puncuation symbol": "EXCLAMATION MARK",
    "name a diary of a wimpy kid book": "DIARYOFAWIIMPYKIDDOITYOURSELFBOOK",
    "name a character from spongebob squarepants": "SPONGEBOBSQUAREPANTS",
    "name a character from adventure time": "ANCIENT PSYCHIC TANDEM WAR ELEPHANT",
    "name a girls name that starts with a": "ADDISONRAE",
    "name something a dog would do": "ABSOLUTELYNOTHING",
    "name a position in soccer": "ATTACKING MIDFIELDER",
    "name an object you fill with air": "HOT AIR BALLOON",
    "name one of andy-s toys from toy story": "BARREL OF MONKEYS",
    "name an m&m color": "YELLOW",
    "name a girls name that starts with m": "MADDISONBEER",
    "name an airline": "ATLANTIC SOUTHEAST AIRLINES",
    "name an edible meat": "GROUND BEEF",
    "name a type of flower": "ACAMPTOPAPPUSSPHAERO",
    "name a character from diary of a wimpy kid": "ROWLEYJEFFERSON",
    "name a character from super mario": "BABYPRINCESSROSALINA",
    "name a month with 31 days": "DECEMBER",
    "name a character from finding nemo": "PHILLIPSHERMAN",
    "name a music genre": "ALTERNATIVE HIPHOP",
    "name something you would find in a bathroom": "HAIR STRAIGHTENER",
    "name a programming language": "EUSLISP ROBOT PROGRAMMING LANGUAGE",
    "name an item you would put on a christmas tree": "CHRISTMAS LIGHTS",
    "name a type of currency": "UNITED STATES DOLLAR",
    "name a dinosaur": "MICROPACHYCEPHALOSAURUS",
    "name a popular breakfast cereal": "FRUIT FIBRE DATES WALNUTS AND OATS",
    "name a star wars character": "WRICKET WYSTRI WARRICK",
    "name an ice cream topping": "CHOCOLATE SPRINKLES",
    "name a vegetable": "BRUSSELSPROUT",
    "name something you charge regularly": "NINTENDOSWITCH",
    "name a type of wood": "MEDIUM DENSITY FIBREBOARD",
    "name a type of light": "CHRISTMAS LIGHTS",
    "name an animal in antartica": "EMPEROR PENGUIN",
    "name an american emergency service": "EMERGENCY MEDICAL SERVICES",
    "name an animal that has a horn": "scimitar horned oryx",
    "name something you would eat at a movie theater": "BERTIE BOTTS EVERY FLAVOUR BEANS",
    "name a type of tree": "MEDIUM DENSITY FIBREBOARD",
    "name a sport that is played by teams": "AMERICAN FOOTBALL",
    "name a superhero": "CAPTAIN UNDERPANTS",
    "name a movie streaming platform": "DISNEYPLUS",
    "name a food that is usually eaten on thanksgiving": "SWEET POTATO CASSEROLE",
    "name one of the top 100 christmas movies": "NATIONAL LAMPOON’S CHRISTMAS VACATION",
    "name something you would find in a kitchen": "GARBAGE DISPOSAL",
    "name a human organ": "LARGE INTESTINE",
    "name something in a salad": "ITALIAN DRESSING",
    "name a character from charlie brown": "LITTLEREDHAIREDIGIRL",
    "name a type of shark": "JAPANESEBULLHEADSHARK",
}

KEYWORDS = [
    "scooby doo", "harry potter", "star wars", "family guy", "adventure time",
    "finding nemo", "toy story", "phineas and ferb", "plants vs zombies",
    "sonic the hedgehog", "diary of a wimpy kid", "amazing world of gumball",
    "spongebob squarepants", "ice cream", "fast food", "christmas song",
    "christmas movie", "christmas tree", "board game", "video game",
    "game console", "social media", "martial art", "musical instrument",
    "natural disaster", "periodic table", "programming language",
    "swimming stroke", "school subject", "american football", "mountain range",
    "state of matter", "emergency service", "pencil case", "movie streaming",
    "potato chip", "pizza topping", "hamburger topping", "breakfast cereal",
    "breakfast drink", "dog breed", "cat breed", "type of bear", "type of shark",
    "type of snake", "type of cake", "type of candy", "type of flower",
    "type of juice", "type of light", "type of tree", "type of wood",
    "type of cheese", "type of transportation", "disney princess", "disney movie",
    "pixar movie", "horror movie", "bathroom", "bedroom", "living room", "backpack",
    "freezer", "garage", "wallet", "camping", "sleepover", "playground", "wedding",
    "halloween", "christmas", "thanksgiving", "birthday", "beach", "ocean", "mountain",
    "desert", "jungle", "outdoor", "indoor", "minecraft", "roblox", "pokemon",
    "overwatch", "fortnite", "frozen", "encanto", "mario", "batman", "simpsons",
    "shrek", "disney", "pixar", "anime", "meme", "sport", "animal", "color",
    "colour", "country", "planet", "dinosaur", "religion", "shape", "instrument",
    "hobby", "activity", "character", "inventor", "invention", "language", "subject",
    "currency", "coin", "gem", "weapon", "clothing", "footwear", "celebrity",
    "youtuber", "brand", "topping", "breakfast", "dessert", "restaurant", "food",
    "fruit", "vegetable", "candy", "soda", "drink", "juice", "cereal", "car", "shoe",
    "bird", "fish", "shark", "snake", "bear", "flower", "tree", "emotion", "season",
    "month", "holiday", "president", "movie", "song", "music", "dance", "book",
    "superhero", "weather", "cheese", "meat", "sauce", "spice", "herb", "swimming",
    "running", "climbing", "exercise",
]

# ── Globals ───────────────────────────────────────────────────────────────────

bot_running   = threading.Event()
last_question = ""
stats         = {"scans": 0, "answers": 0, "start_time": 0.0}

# ── Screen helpers ────────────────────────────────────────────────────────────

def get_screen_size():
    with mss.mss() as sct:
        mon = sct.monitors[1]
        return mon["width"], mon["height"]

CALIBRATION_FILE = "region.calib"
calibration_hotkey = None

def calibrate_region():
    global calibration_hotkey
    
    # Remove F5 hotkey temporarily
    if calibration_hotkey:
        keyboard.remove_hotkey(calibration_hotkey)
        calibration_hotkey = None
    
    print("\n=== CALIBRATION MODE ===")
    print("Move mouse to TOP-LEFT corner of the question text area.")
    print("Then press F5...")
    
    # Wait for F5 press using polling (no recursion)
    while True:
        if keyboard.is_pressed('f5'):
            time.sleep(0.2)  # debounce
            break
        time.sleep(0.05)
    
    x1, y1 = pyautogui.position()
    print(f"Top-left set to ({x1}, {y1})")
    
    time.sleep(0.5)
    print("Move mouse to BOTTOM-RIGHT corner of the question text area.")
    print("Then press F5 again...")
    
    while True:
        if keyboard.is_pressed('f5'):
            time.sleep(0.2)
            break
        time.sleep(0.05)
    
    x2, y2 = pyautogui.position()
    print(f"Bottom-right set to ({x2}, {y2})")
    
    region = {"left": x1, "top": y1, "width": x2 - x1, "height": y2 - y1}
    with open(CALIBRATION_FILE, "wb") as f:
        pickle.dump(region, f)
    print(f"Region saved: {region}")
    print("=== CALIBRATION COMPLETE ===\n")
    
    # Re-add F5 hotkey
    calibration_hotkey = keyboard.add_hotkey("f5", calibrate_region)

def get_question_region():
    if os.path.exists(CALIBRATION_FILE):
        with open(CALIBRATION_FILE, "rb") as f:
            return pickle.load(f)
    else:
        w, h = get_screen_size()
        return {
            "left": int(w * QUESTION_REGION_PCT[0]),
            "top": int(h * QUESTION_REGION_PCT[1]),
            "width": int(w * (QUESTION_REGION_PCT[2] - QUESTION_REGION_PCT[0])),
            "height": int(h * (QUESTION_REGION_PCT[3] - QUESTION_REGION_PCT[1])),
        }

def capture_region(region):
    with mss.mss() as sct:
        shot = sct.grab(region)
        img = np.array(shot)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

# ── OCR ───────────────────────────────────────────────────────────────────────

def preprocess_for_ocr(img_bgr):
    h, w = img_bgr.shape[:2]
    big  = cv2.resize(img_bgr, (w * 3, h * 3), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    inv = cv2.bitwise_not(thresh)
    th, tw = inv.shape
    tx, ty = int(tw * 0.08), int(th * 0.10)
    return inv[ty:th-ty, tx:tw-tx]

def ocr_region(region):
    img = capture_region(region)
    processed = preprocess_for_ocr(img)
    text = pytesseract.image_to_string(Image.fromarray(processed), config="--psm 7")
    return clean_text(text)

def clean_text(text):
    text = re.sub(r"[^\x20-\x7E]", "", text)
    return re.sub(r"\s+", " ", text).strip()

# ── Question filter ───────────────────────────────────────────────────────────

QUESTION_STARTERS = ("name ", "what ", "which ", "how ", "where ", "who ", "when ")

def is_real_question(text):
    lower = text.lower().rstrip(" -|.~*p")
    if len(lower) < MIN_QUESTION_LEN:
        return False
    return any(lower.startswith(s) for s in QUESTION_STARTERS)

# ── DB Lookup ─────────────────────────────────────────────────────────────────

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return re.sub(r"\s+", " ", text).strip()

def local_lookup(question):
    key = normalize(question)
    if key in ANSWERS_DB:
        print(f"[DB] Exact match: {key!r}")
        return ANSWERS_DB[key]
    for db_key, answer in ANSWERS_DB.items():
        if db_key in key or key in db_key:
            print(f"[DB] Partial match: {db_key!r}")
            return answer
    question_words = set(key.split())
    matched_keywords = [kw for kw in KEYWORDS if kw in key]
    if matched_keywords:
        candidates = {}
        for kw in matched_keywords:
            for db_key, answer in ANSWERS_DB.items():
                if kw in db_key:
                    candidates[db_key] = answer
        if candidates:
            def score(db_key):
                db_words = set(db_key.split())
                return len(db_words & question_words)
            best_key = max(candidates, key=score)
            best_score = score(best_key)
            print(f"[DB] Keyword match (score={best_score}, key={best_key!r})")
            return candidates[best_key]
    best_match, ratio = fuzzy_match(key, list(ANSWERS_DB.keys()), threshold=0.7)
    if best_match:
        print(f"[DB] Fuzzy match (ratio={ratio:.2f}): {best_match!r}")
        return ANSWERS_DB[best_match]
    print(f"[DB] No match for: {key!r}")
    return None

def fuzzy_match(question, db_keys, threshold=0.7):
    best = None
    best_ratio = 0
    for db_key in db_keys:
        ratio = difflib.SequenceMatcher(None, question, db_key).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best = db_key
    if best_ratio >= threshold:
        return best, best_ratio
    return None, 0

# ── Input ─────────────────────────────────────────────────────────────────────

def type_answer(answer):
    global last_question
    time.sleep(ANSWER_DELAY)
    pyperclip.copy(answer)
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.2)
    keyboard.press("enter")
    time.sleep(0.2)
    keyboard.release("enter")
    print(f"[BOT] Typed: {answer!r}")
    stats["answers"] += 1

    time.sleep(0.3)
    keyboard.press("esc")
    time.sleep(0.3)
    keyboard.release("esc")
    time.sleep(0.3)
    keyboard.press("r")
    time.sleep(0.3)
    keyboard.release("r")
    time.sleep(0.3)
    keyboard.press("enter")
    time.sleep(0.3)
    keyboard.release("enter")
    print("[BOT] Sent Esc -> R -> Enter")
    last_question = ""

# ── Bot loop ──────────────────────────────────────────────────────────────────

def bot_loop():
    global last_question
    region = get_question_region()
    print(f"[BOT] Scanning region: {region}")

    while bot_running.is_set():
        stats["scans"] += 1
        try:
            question = ocr_region(region)
        except Exception as e:
            print(f"[OCR ERROR] {e}")
            time.sleep(SCAN_INTERVAL)
            continue

        if len(question) >= MIN_QUESTION_LEN:
            if question != last_question:
                if not is_real_question(question):
                    print(f"[OCR] Not a real question: {question!r}")
                    last_question = question
                    time.sleep(SCAN_INTERVAL)
                    continue
                print(f"[OCR] Question: {question!r}")
                last_question = question
                answer = local_lookup(question)
                if answer:
                    type_answer(answer)
                else:
                    print("[BOT] No answer in DB — skipping.")
            else:
                print(f"[OCR] Same as last question, waiting: {question!r}")
        else:
            print(f"[OCR] Too short: {question!r}")

        time.sleep(SCAN_INTERVAL)

    print("[BOT] Stopped.")

# ── Hotkeys ───────────────────────────────────────────────────────────────────

def toggle_bot():
    if bot_running.is_set():
        bot_running.clear()
        print("[HOTKEY] Paused.")
    else:
        bot_running.set()
        stats.update({"start_time": time.time(), "answers": 0, "scans": 0})
        print("[HOTKEY] Starting in 3 seconds — switch to Roblox!")
        time.sleep(3)
        threading.Thread(target=bot_loop, daemon=True).start()

def stop_bot():
    bot_running.clear()
    elapsed = time.time() - stats["start_time"] if stats["start_time"] else 0
    print(f"[STOP] Answers: {stats['answers']} | Scans: {stats['scans']} | Time: {elapsed:.1f}s")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global calibration_hotkey
    print("=" * 55)
    print(f"  Type or Die Bot  ({len(ANSWERS_DB)} questions in DB)")
    print("=" * 55)
    print(f"  {HOTKEY_TOGGLE.upper()} — Start / Pause")
    print(f"  {HOTKEY_STOP.upper()}  — Stop & exit")
    print("  F5 — Calibrate question region (put mouse at corners and press F5)")
    print("=" * 55)

    keyboard.add_hotkey(HOTKEY_TOGGLE, toggle_bot)
    keyboard.add_hotkey(HOTKEY_STOP,   stop_bot)
    calibration_hotkey = keyboard.add_hotkey("f5", calibrate_region)

    print("[READY] Waiting for hotkey...")
    keyboard.wait(HOTKEY_STOP)

if __name__ == "__main__":
    main()