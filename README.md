<div align="center">

# iMA Menu


[![PayPal](https://img.shields.io/badge/Paypal-blue)](https://www.paypal.com/paypalme/imaboud)
[![Donate](https://img.shields.io/badge/Donate-%23008080)](https://buymeacoffee.com/imaboud)


- iMA Menu adds a lot of useful features right on your context menu, and allows easy theming and editing without priour programming knowledge.

![](https://i.imgur.com/fO94CpQ.png)


_____________________________________________________________________
## Download Installer

[iMA Menu installer beta 1](https://github.com/iMAboud/iMA-Menu/releases/download/v0.1-beta.1/iMA.Menu-beta.1.exe)

_____________________________________________________________________




## Features

- Transfer files super fast with no size limit to any PC with just a pass code.
- Download a video or directly convert it to audio from Youtube or any site.
- Remove background of any image.
- Color picking to hex over desktop and programs.
- Draw over apps, scroll wheel to increase of decrease opacity of desktop.
- An app to easily change the context menu (right click) theme
- An app to remove or change the names and icon of any item in context menu
- Customize items in cotext menu to make any item appear with holding shift, or inside a menu or hide it completly.
- Merging 2 media files.
- Resize dimensions of an image and aspect of a video.
- MP4 to MP3
- Video to GIF, no limit, gif can be up to 2 hours (it might go longer, I didn't test it).
- Convert any video to any format.
- Reduce file size of any image or video without losing too much quality. 
- Change a wallpaper with commands, search a wallpaper, select from options and it'll save and set as background instantly.
- Clean temp/cookies/cache..etc.
- Custom theme and settings for Nilesoft for minimalism.
- Fast search any file in all drives, copy the path, paste and you're redirected to that path.
- Stream to any friend that has this installed, and watch any movie/series synced in a lobby using perio & stremio.
- Lightweight, fast, easy, portable, no background apps, almost %100 pre-configured and ready to use.
- Fully automated, with pre-configured scripts, automatically sets the location path where you click.
- I'm always adding and fixing features, so I might've missed a few more features.

_____________________________________________________________________

## Setup manually

Name|installation 
:---|:---
iMA Menu| Download the repo as zip.
Nilesoft Shell| In Powershell: `winget install nilesoft.shell`
Schollz Croc|In Powershell: `winget install schollz.croc`
Python|In Powershell: `winget install -e -i --id=Python.Python.3.12 --source=winget --scope=machine` Make sure to check both add python to path and use admin.
yt-dlp|In Powershell: `python -m pip install -U yt-dlp[default]`
ffmpeg|In Powershell: `iex (irm ffmpeg.tc.ht)`
Packages |In powershell: `pip install backgroundremover pyautogui pyperclip pynput colorama pillow PyQt5`

_____________________________________________________________________

## Installation

- Unzip `iMA Menu` and set it aside for now
- Install all required from the table above "running the commands is recommended and easier".
- After Nilesoft Shell is installed copy all contents of `iMA Menu` into Nilesoft's installation folder C:\Program Files\Nilesoft Shell
- Hold CTRL+Right-Click to update context menu.

_____________________________________________________________________

## IMPORTANT STEP:
- Navigate to C:\Program Files\Nilesoft Shell\script and right-click EDIT **croc.bat**
- Change the line "SET_YOUR_CODE_HERE" to your password. **6+ character**
e.g: `powershell -NoExit -Command "Croc send --code PASSWORD999 \"$(Get-Clipboard)\""`

_____________________________________________________________________

## Usage & Config
  
 **File Transfer**


**Upload** ![](https://i.imgur.com/81GPsUN.png)
   - Right-click the file/folder you want to upload.
   - Select **Upload**, give the receiver your password.

**Download** ![](https://i.imgur.com/SZCXfZf.png)
   - Right-click in any directory you want the files to be downloaded in.
   - Select **Download**, and insert the password provided by the uploader.

(Upload is active only when you select a file, and Download is active only when you right-click an empty space)


 **Configure Croc:**
   Make Croc auto accepts once you insert a password without typing "Y" to confirm everytime.
- From powershell run `Croc --yes --remember`
- Insert a password "You can transfer a file to yourself to save the configuration".

If you want to generate a unique code everytime you want to share a file simly remove the command `--code`& your code from **croc.bat**.

**Most of the scripts below will be executed with a minimized window, DO NOT PANIC when you click and see nothing, it's minimized, just open the window to see the progress**

_____________________________________________________________________

## YouTube & X downloader 
![](https://i.imgur.com/5slVepk.png)
- Copy the video's link
- Right-Click an empty space (This is where your video will be saved in)
- Hover over Youtube, and select either **Video** or **Audio**.
- It will start installing instantly if everything is configured correctly.
_____________________________________________________________________

## Video & Image editing
- Pretty much self explanatory, just Right-Click a video or an image, then > Tools > select your option.

![](https://i.imgur.com/eDjS8H1.png)

**Pre-configuration commands, you don't need to do anything here unless you want to edit the output**
- Background Remover runs the command `backgroundremover -i "file_path" -a -ae 15 -o "output_file"`
- Resize image runs `ffmpeg -i "file_path" -s !dimensions! "output_image"`
- Resize video runs `ffmpeg -i "file_path" -aspect !aspect! "output_video"`
- MP4 to MP3 runs `ffmpeg -i "video_path" "output_audio"`
- Video to Gif runs `ffmpeg -i "video_path" -vf "fps=15,scale=320:-1:flags=lanczos" -c:v gif -loop 0 "output_video"`
- Convert runs `ffmpeg -i "video_path" -c:v copy -c:a copy "output_video"`
- Reduce Size runs `ffmpeg -i "file_path" -vf scale=-1:720 -c:a copy "output_path"`

_____________________________________________________________________


## Search & Draw & Clean Temp & Wallpaper Changer (Found under "File Manage"

![](https://i.imgur.com/JrNBaGz.png)

**Search**
- Type the name of the file, search in all directory
- Copy the path you want to look for, and paste it in the same window to open the path and highlight the file.


_____________________________________________________________________

**Draw**
- Right Click to Draw, Left Click to change color
- Mousewheel to change opacity of canvas
- ESC to stop and close


_____________________________________________________________________

**Clean Temp**
- This will clean all of temp, cache, recent, cookies, and prefetch. 

_____________________________________________________________________

**Wallpaper Changer**

You need to aquire the API from "https://api.unsplash.com".
It's free of charge and easy to sign-up. Once you create your Application page setup in `unsplash` you'll get your own free API.
- Copy your `Access Key`
- Open **wallpaper.py** located in Nilesoft's folder **script**
- Replace the key with "YOUR_ACESS_KEY"
- Save & Exit
_____________________________________________________________________

**Color Picking**
- Shows the pixel color your cursor is pointing at, right click to copy it to clipboard

_____________________________________________________________________

**Merge media**
- Merge 2 media files to overlap. 


_____________________________________________________________________

**StremiM**

<img src="https://i.imgur.com/wD3OsGX.png" alt="Modify" width="400">


Stream anything from Stremio using peario with an automation to open peario + stremio + copy share link + send it to a friend, friend can type your code and it will automatically retrieves that link + opens peario and stremio and starts watching. 

- You'll need Stremio for both devices.

- Edit the "Stream.bat" file in `Script > stremiM folder, and scroll down to find "YOUR_CODE_HERE", replace it with your code "minimum 6". 

- Then you just right-click "Stream" , search a movie / series and click "Copy link". 


- The script will automatically detect that a link is copied and will send it using "Croc".

- To watch, click "Watch", type your friend's code, it will retreve the link, pastes it in chrome and opens it as an app. 

- The script will automatically resends the link multiple times if you have more than 1 friend you want to share the link to it will do it automatically after you copy the link just set and wait for all of them to connect, it will loop until you're done. 

_____________________________________________________________________


**Account Switching**
- I might update this with my own Valorant account switching configuration, which uses TcNo Account Switching but for now TcNo has too many bugs so I'll updat this later.

_____________________________________________________________________

**Remove/Add/Edit**
- In the GUI in taskbar > Shell > modify
- You can add any item to Hide box to hide it everywhere, or in More options menu or active with Shift button, just drag an id from the ids list and drop it in any of the boxes. 
- You can edit any option in context menu's name and icon, write the old name, and the new name you want and if you don't want to add a custom icon you can leave the icon option blank, it will use the default icon. 
- You can see and delete any custom display name to set it as the default name and icon.
_____________________________________________________________________

**GUI Theme editor**
- Taskbar > Shell > theme 

_____________________________________________________________________

## Screenshots

<img src="https://i.imgur.com/OGehNdS.png" alt="upload" width="400">
<img src="https://i.imgur.com/tMEe1wy.png" alt="downloading" width="400">
<img src="https://i.imgur.com/U6syLCl.png" alt="Draw" width="400">
<img src="https://i.imgur.com/qQvxrdB.png" alt="HEX" width="400">
<img src="https://i.imgur.com/2GMg2cx.png" alt="Theme" width="400">
<img src="https://i.imgur.com/c6O9rAK.png" alt="Modify" width="400">


_____________________________________________________________________

**Added GUI to taskbar**

![](https://i.imgur.com/lWG7w2c.png)

_____________________________________________________________________
_____________________________________________________________________

## issues & fixes
- Color picking only works on 1 monitor, I'll try to fix this.
- background remover may not work, not sure why but will investigate.

_____________________________________________________________________
_____________________________________________________________________
_____________________________________________________________________
  
## License

This project is licensed under the [MIT License](LICENSE).

</div>

