import argparse
import time
from datetime import datetime
import pyautogui

# =====================================================
# DEFAULT CONFIGURATION
# =====================================================

# Time (24-hour format)
DEFAULT_HOUR = 2
DEFAULT_MINUTE = 15
DEFAULT_SECOND = 0

# Image to search
DEFAULT_IMAGE = "chat_send_button_orange.png"

# Confidence (0.0 - 1.0)
DEFAULT_CONFIDENCE = 0.85

# Retry until image is found
DEFAULT_WAIT_IMAGE = True

# Coordinate fallback
DEFAULT_USE_COORDINATE = False
DEFAULT_X = 1000
DEFAULT_Y = 500

# Click options
DEFAULT_CLICKS = 1
DEFAULT_INTERVAL = 0.1


# =====================================================
# ARGUMENTS
# =====================================================

def get_args():
    parser = argparse.ArgumentParser(
        description="Automatic scheduled image clicker."
    )

    parser.add_argument("--hour", type=int, default=DEFAULT_HOUR)
    parser.add_argument("--minute", type=int, default=DEFAULT_MINUTE)
    parser.add_argument("--second", type=int, default=DEFAULT_SECOND)

    parser.add_argument("--image", default=DEFAULT_IMAGE)

    parser.add_argument("--confidence",
                        type=float,
                        default=DEFAULT_CONFIDENCE)

    parser.add_argument("--x",
                        type=int,
                        default=DEFAULT_X)

    parser.add_argument("--y",
                        type=int,
                        default=DEFAULT_Y)

    parser.add_argument("--coordinate",
                        action="store_true",
                        help="Use X,Y coordinate instead of image.")

    parser.add_argument("--clicks",
                        type=int,
                        default=DEFAULT_CLICKS)

    parser.add_argument("--interval",
                        type=float,
                        default=DEFAULT_INTERVAL)

    parser.add_argument("--record-position",
                        action="store_true",
                        help="Print mouse position after 5 seconds.")

    return parser.parse_args()


# =====================================================
# CLICK IMAGE
# =====================================================

def click_image(args):

    while True:

        location = pyautogui.locateCenterOnScreen(
            args.image,
            confidence=args.confidence
        )

        if location:
            print(f"Image found at {location}")

            pyautogui.click(
                location.x,
                location.y,
                clicks=args.clicks,
                interval=args.interval
            )

            return True

        if not DEFAULT_WAIT_IMAGE:
            print("Image not found.")
            return False

        print("Waiting for image...")
        time.sleep(0.5)


# =====================================================
# CLICK COORDINATE
# =====================================================

def click_coordinate(args):

    pyautogui.click(
        args.x,
        args.y,
        clicks=args.clicks,
        interval=args.interval
    )

    return True


# =====================================================
# MAIN
# =====================================================

def main():

    args = get_args()

    if args.record_position:
        print("Move mouse to target...")
        time.sleep(5)
        print(pyautogui.position())
        return

    print("=" * 50)
    print("AUTO CLICK SCHEDULER")
    print("=" * 50)

    print(
        f"Time      : {args.hour:02}:{args.minute:02}:{args.second:02}")

    if args.coordinate:
        print(f"Mode      : Coordinate")
        print(f"Position  : ({args.x}, {args.y})")
    else:
        print(f"Mode      : Image")
        print(f"Image     : {args.image}")
        print(f"Confidence: {args.confidence}")

    print(f"Clicks    : {args.clicks}")

    print("=" * 50)

    last_run = None

    while True:

        now = datetime.now()

        if (
            now.hour == args.hour
            and now.minute == args.minute
            and now.second == args.second
            and last_run != now.date()
        ):

            print(f"\n[{now:%Y-%m-%d %H:%M:%S}] Triggered!")

            if args.coordinate:
                click_coordinate(args)
            else:
                click_image(args)

            last_run = now.date()

            print("Done.")

            time.sleep(1)

        time.sleep(0.2)


if __name__ == "__main__":
    main()