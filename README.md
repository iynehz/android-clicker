# Android Clicker

This is a demo project for how you can use your PC to automatically control
your Android mobile phone. And for demo purpose we try to auto click
DingDong(叮咚买菜)'s shopping cart a little bit.

## Disclaimer
This is only for studying and demoing the idea from technology aspect! 仅供学习研究之用！

## Install

Install scrcpy. And make sure it's runnable from Windows Command.

For example if you use choco, you can run below in Windows Command in Administrator mode,

```
choco install scrcpy
choco install adb
```

See also https://github.com/Genymobile/scrcpy for other ways to install scrcpy.

Install Python 3 (for example, from https://www.python.org/downloads/).
And make sure it's runnable from Windows Command.
And install Python dependencies from requirements.txt.
For example if you use venv,

```
# git clone the repo, and cd into it 
...

# create the venv
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

Run both scrcpy and the script in your normal user mode. Administrator mode is not needed.

### Perparations

1. Enable ADB debug on your phone.
1. Connect your phone to the PC. 
1. From a Windows Command, run scrcpy.
Make sure it pop up a Window for your mobile phone. 
And make sure scrcpy window is sized properly so that the mobile UI takes the whole window.
1. Prepare your DingDong shopping cart.

### Adjusting contants

I am not sure but depending on your Android device, e.g. if it has different
resolution from my OnePlus 8T, you may need to adjust the constants
XXX_FACTOR in the DingDong class source.

And there is a "study" mode for you to know the coordinates of mouse cursor.
```
# Within your Python environment.
# i.e. if you use venv you need activate it.
python android_clicker.py your-mobile-phone-window-name --study
```

You can press "p" key to see the cursor position info from log.

### Run the script

1. From a second Windows Command,

    ```
    # Within your Python environment.
    # i.e. if you use venv you need activate it.
    python android_clicker.py your-mobile-phone-window-name
    ```
1. Once the condition's met, it will notify by beeping.
1. To terminate the script, press `ESC` key and it will finish after current iteration of the loop.

### For development: Run in verbose and debug mode

```
# --debuglevel=1 can show DingDong time slot check box
python android_clicker.py your-mobile-phone-window-name --verbose --debuglevel=1

# --debuglevel=2 can enable pause
python android_clicker.py your-mobile-phone-window-name --verbose --debuglevel=2
```
