import argparse
from abc import ABC, abstractmethod
from collections import namedtuple
from tempfile import NamedTemporaryFile
import time
from turtle import left
from numbers import Number
from typing import NamedTuple, Optional
import logging

import win32gui, win32ui
import win32con
import winsound

import pyautogui
import keyboard
import cv2 as cv
import numpy as np
from PIL import ImageGrab
from matplotlib import pyplot as plt


logger = logging.getLogger(__name__)


class Point(NamedTuple):
    x: Number
    y: Number

    def scale(self, factor):
        return self.__class__(int(self.x * factor), int(self.y * factor))

    def offset(self, x, y):
        return self.__class__(self.x + x, self.y + y)

    def is_in(self, rect: "Rectangle"):
        return rect.left < self.x < rect.right and rect.top < self.y < rect.bottom


class Rectangle(NamedTuple):
    left: Number
    top: Number
    right: Number
    bottom: Number

    def scale(self, factor):
        return self.__class__(
            int(self.left * factor),
            int(self.top * factor),
            int(self.right * factor),
            int(self.bottom * factor),
        )

    def offset(self, x, y):
        return self.__class__(
            self.left + x,
            self.top + y,
            self.right + x,
            self.bottom + y,
        )

    @property
    def middle(self) -> Point:
        return Point(
            int((self.left + self.right) / 2), int((self.top + self.bottom) / 2)
        )

    @property
    def width(self):
        return self.right - self.left

    @property
    def height(self):
        return self.bottom - self.top


class MobileClickerBase(ABC):
    # TODO: screen_scale seems not necessary
    def __init__(
        self,
        name: str,
        *,
        hwnd=None,
        screen_scale: Optional[float] = 1,
        debug_level: Optional[int] = 0
    ):
        if not hwnd:
            hwnd = self.get_window_by_name(name)
        if not hwnd:
            raise ValueError(
                (
                    "Cannot find Window: %s. "
                    "Maybe you've not connected your mobile or you gave a wrong window name?"
                )
                % name
            )
        self.hwnd = hwnd
        self.screen_scale = screen_scale or 1  # not really used now
        self.debug_level = debug_level or 0
        self.cancel = False  # flag to indicate cancel execution
        self.position_back = self.position(0.7, 0.96)
        logger.debug("Window rectangle: %s", self.rect)

    def back(self, *, sleep=0.5):
        logger.debug("Android back button ...")
        pos = self.cursor_position()
        if not pos.is_in(self.rect):
            pyautogui.moveTo(self.position_back())
        pyautogui.click(button="right")

        time.sleep(sleep)

    @classmethod
    def get_window_by_name(cls, name: str):
        """
        Returns (left, top, right, bottom)
        """
        return win32gui.FindWindow(0, name)

    # TODO: maybe cache rect and listen on window move event to refresh cache?
    @property
    def rect(self) -> Rectangle:
        """Get window rectangle.
        Returns (left, top, right, bottom)
        """
        rect = win32gui.GetWindowRect(self.hwnd)
        return Rectangle(*rect)

    def position(self, xfactor, yfactor) -> callable:
        def f() -> Point:
            left, top, right, bottom = self.rect
            x = int((right - left) * xfactor + left)
            y = int((bottom - top) * yfactor + top)
            return Point(x, y)

        return f

    def area(self, lfactor, tfactor, rfactor, bfactor) -> callable:
        def f() -> Rectangle:
            left, top, right, bottom = self.rect
            l = int((right - left) * lfactor + left)
            t = int((bottom - top) * tfactor + top)
            r = int((right - left) * rfactor + left)
            b = int((bottom - top) * bfactor + top)
            return Rectangle(l, t, r, b)

        return f

    def notify(self):
        while True:
            winsound.PlaySound("*", winsound.SND_ALIAS)
            time.sleep(0.1)
            if self.cancel:
                break

    def cursor_position(self) -> Point:
        pos = pyautogui.position()
        pos = Point(*pos)
        logger.debug("Cursor at %s", pos)
        return pos

    def show_rect(self, rect: Rectangle, padding: int = 0):
        """Display rectangle. For development debug purpose."""
        dc = win32gui.GetDC(0)
        dc_obj = win32ui.CreateDCFromHandle(dc)

        # TODO: transparent background does not work.
        dc_obj.SetBkMode(win32con.TRANSPARENT)
        rect_padded = Rectangle(
            rect.left - padding,
            rect.top - padding,
            rect.right + padding,
            rect.bottom + padding,
        )
        dc_obj.Rectangle(rect_padded)
        hwnd = win32gui.WindowFromPoint((0, 0))
        win32gui.InvalidateRect(hwnd, rect, True)

    @abstractmethod
    def check_one(self) -> bool:
        pass

    def check_loop(self):
        while True:
            if self.check_one():
                self.notify()
                break
            if self.cancel:
                break

    def move_cursor(self, pos: Point):
        logger.debug("Moving mouse to %s ...", pos)
        pyautogui.moveTo(*pos)

    def click(self, pos: Point, *, button="left", sleep=0.5):
        logger.debug("Clicking mouse at %s ...", pos)
        pyautogui.moveTo(*pos)
        pyautogui.click(button=button)

        time.sleep(sleep)

    def drag_down(self, pos: Point, distance: int, duration: float = 0.1, *, sleep=0.5):
        """Drag down can usually be used for page refreshing for mobile app."""

        # Ideally I should be able to use pyautogui.drag(),
        # but don't know why but drag() seems to have chance to mis-click.
        # So I implement drag() myself..
        pyautogui.moveTo(pos)
        pyautogui.mouseDown(button="left")
        pyautogui.move(0, distance)
        pyautogui.mouseUp()

        time.sleep(sleep)

    def pause(self):
        """This can be used for debug."""
        if self.debug_level > 1:
            self.cursor_position()
            input("Press Enter to continue...")

    def log_cursor_position(self):
        pos = self.cursor_position()
        rect = self.rect
        if pos.is_in(rect):
            pos_rel = pos.offset(-rect.left, -rect.top)
            factor = (pos_rel.x / rect.width, pos_rel.y / rect.height)
            logger.info(
                "Cursor position: absolute: %s, relative: %s, relative factor: %s",
                pos,
                pos_rel,
                factor,
            )
        else:
            logger.info("Cursor position: absolute: %s", pos)


class DingDong(MobileClickerBase):

    CHECK_BOX_YOFFSET_FACTOR = 0.055
    TIME_SLOTS_TO_CHECK = 5
    POSITION_PAY_FACTOR = (0.8, 0.9)
    POSITION_SUBMIT_CART_FACTOR = (0.85, 0.85)
    POSITION_DRAG_DOWN_FACTOR = (0.5, 0.3)
    RECT_CHECK_TIME_SLOT_FACTOR = (0.36, 0.48, 0.7, 0.52)

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.position_pay = self.position(*self.POSITION_PAY_FACTOR)
        self.position_submit_cart = self.position(*self.POSITION_SUBMIT_CART_FACTOR)
        self.position_drag_down = self.position(*self.POSITION_DRAG_DOWN_FACTOR)
        self.rect_check_time_slot = self.area(*self.RECT_CHECK_TIME_SLOT_FACTOR)

    def check_pay_ready(self) -> bool:
        """Check "deliver time" area:
        When it's not deliverable, font color in the area is light.
        When it's deliverable, font color in the area is dark.
        And we use OpenCV to process it.
        """
        window_height = self.rect.height
        first_check_rect = self.rect_check_time_slot()

        # check 4 deliver time boxes
        logger.debug("Will check %s delivery time slots", self.TIME_SLOTS_TO_CHECK)
        rects_to_check = (
            first_check_rect.offset(
                0, int(window_height * self.CHECK_BOX_YOFFSET_FACTOR * i)
            )
            for i in range(self.TIME_SLOTS_TO_CHECK)
        )

        for i, rect in enumerate(rects_to_check):
            logger.debug("Checking rect: %s", rect)

            rect_real = rect

            # TODO: Seems screen_scale factor is not needed? But did I thought it's needed on first day of this project?
            # rect_real = rect.scale(self.screen_scale)

            if self.debug_level > 0:
                self.show_rect(rect_real, padding=2)
                time.sleep(1)

            img_pil = ImageGrab.grab(bbox=tuple(rect_real))

            img = np.array(img_pil)
            img = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
            ret, thresh = cv.threshold(img, 127, 255, cv.THRESH_BINARY)

            # if i == 0:
            #    plt.subplot(2, 1, 1)
            #    plt.imshow(img, "gray", vmin=0, vmax=255)
            #    plt.subplot(2, 1, 2)
            #    plt.imshow(thresh, "gray", vmin=0, vmax=255)
            #    plt.show()

            cnt = np.sum(thresh == 0)
            if cnt > 20:
                # Got good state!
                # Then we select the delivery time slot.
                logger.warning("Pay is ready at check box %s!!", i)
                self.click(rect.middle)
                return True
        logger.info("Sigh.. No delivery time slot.")
        return False

    def refresh(self, *, sleep=0.5):
        logger.info("Refreshing shopping cart page...")
        self.drag_down(self.position_drag_down(), self.rect.height / 3)
        time.sleep(sleep)

    def check_one(self) -> bool:
        self.refresh(sleep=1)

        self.pause()
        pos_goto_pay = self.position_submit_cart()
        self.click(pos_goto_pay, sleep=0.5)

        self.pause()
        pos_pay = self.position_pay()
        self.click(pos_pay, sleep=0.5)

        self.pause()
        if self.check_pay_ready():
            # Now we should be able to pay!
            self.click(pos_pay, sleep=0.5)
            return True

        # get back to the shopping cart page
        self.back(sleep=0.2)
        self.back(sleep=0.2)
        return False


def onkeypress(obj: MobileClickerBase):
    def callback(event):
        if event.name == "esc":  # Terminate on ESC
            logger.warning("Cancel signal detected!!")
            obj.cancel = True

        elif event.name == "p":  # show cursor position on p, for debug
            obj.log_cursor_position()

    return callback


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Mobile phone clicker.")
    parser.add_argument("name", type=str, help="Mobile phone window name.")
    parser.add_argument("--verbose", action="store_true", help="verbose mode.")
    parser.add_argument(
        "--study", action="store_true", help="Only for studying cursor position."
    )
    parser.add_argument(
        "--debuglevel",
        type=int,
        default=0,
        help=(
            "For debug. "
            "If debuglevel > 1, it will run only one check iteration, and pause() will take effect."
        ),
    )
    args = parser.parse_args()
    if args.study:
        args.verbose = True

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    dingdong = DingDong(args.name, screen_scale=1.5, debug_level=args.debuglevel)
    keyboard.on_press(onkeypress(dingdong))

    if args.study:
        while True:
            time.sleep(0.1)
            if dingdong.cancel:
                break
    elif args.debuglevel > 1:
        dingdong.cursor_position()
        dingdong.check_one()
    else:
        dingdong.check_loop()
