# iMShare

<div align="center">

[![PayPal](https://img.shields.io/badge/Paypal-blue)](https://www.paypal.com/paypalme/imaboud)
[![Donate](https://img.shields.io/badge/Donate-%23008080)](https://buymeacoffee.com/imaboud)

</div>

- iMShare adds a lot of useful features right on your context menu.
- Large file sharing between devices - Video/Image editing - Draw over apps - Search and set a wallpaper - Youtube and X downloader, and more.

![](https://i.imgur.com/NlXTZOy.png) ![](https://i.imgur.com/wIaeznc.png) ![](https://i.imgur.com/VWCJmhs.png) ![](https://i.imgur.com/bJqrU9K.png)
![Manage](https://i.imgur.com/n4fQIsC.png) 


## Update
- Added GUI to edit the theme.nss
- Added a GUI to the "modify" file to easily edit, remove or add anything in the context menu. 
- StremiM utilizes "Peario" and "Stremio" to stream a movie to a friend the easy way. 
- Added Color picking anywhere, right click on the pixel color to copy hex to clipboard
- Added Merging 2 files (Video / Audio) to overlap. 

## Features

- Transfer files super fast with no size limit to any PC with just a pass code.
- Download a video or directly conver it to audio from Youtube or X with a button.
- Remove background of any image.
- Color picking to hex over desktop and programs. 
- Merging 2 media files.
- Resize dimensions of an image and aspect of a video.
- MP4 to MP3
- Video to GIF, no limit, gif can be up to 2 hours (it might go longer, I didn't test it).
- Convert any video to any format.
- Reduce file size of any image or video without losing too much quality. 
- Draw over apps, scroll wheel to increase of decrease opacity of desktop.
- Change a wallpaper with commands, search a wallpaper, select from options and it'll save and set as background instantly.
- Clean temp/cookies/cache..etc.
- Open multiple accounts e.g: Steam, Valorant.. with "TcNo Account Switcher" but from context menu. 
- Custom theme and settings for Nilesoft for minimalism.
- Fast search any file in all drives, copy the path, paste and you're redirected to that path. 
- Lightweight, fast, easy, portable, no background apps, almost %100 pre-configured and ready to use.
- Fully automated, with pre-configured scripts, automatically sets the location path where you click.
- Additional features and config details from [Nilesoft](https://github.com/moudey/Shell) and [Croc](https://github.com/schollz/croc) [yt-dlp](https://github.com/yt-dlp/yt-dlp) repositories.

## Requierments

Download|Manuall installation
:---|:---
[iMShare](https://github.com/iMAboud/iMShare/raw/main/iMShare.zip)| Or download zip from the repo.
[Nilesoft Shell](https://nilesoft.org/download/shell/1.9.15/setup.exe)| Or run in powershell: `winget install nilesoft.shell`
[Schollz Croc](https://github.com/schollz/croc/releases/download/v9.6.15/croc_v9.6.15_Windows-64bit.zip)|Or run in powershell: `winget install schollz.croc`
[Python](https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe)|Or run in powershell: `winget install -e -i --id=Python.Python.3.12 --source=winget --scope=machine` Make sure to check add python to path.
[yt-dlp](https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe)|Or run in powershell: `python -m pip install -U yt-dlp[default]`
[ffmpeg](https://www.gyan.dev/ffmpeg/builds/)|Or use this one line installer from [TCNOco](https://github.com/TCNOco) `iex (irm ffmpeg.tc.ht)`
Backgroundremover|In powershell run: `pip install backgroundremover`
Hex & Draw|In powershell run: `pip install pyautogui pyperclip pynput colorama pillow PyQt5`

## Installation

- Unzip `iMShare` and set it aside for now
- Install `Nilesoft Shell` & `Shollz Croc` & `Python` & `yt-dlp` & `ffmpeg` &`backgroundremover` from the table above, or your desired method.
- After `Nilesoft Shell` is installed and activated copy all contents of `files` into Nilesoft's installation folder `C:\Program Files\Nilesoft Shell` (Replace `imports`&`Shell.nss` and add `icons`&`script` folders.
- Hold CTRL+Right-Click to update context menu.

   *Note: If context menu didn't update, try restarting Windows Explorer from Task Manager.*

## IMPORTANT STEP:
- Navigate to `C:\Program Files\Nilesoft Shell\script` and right-click EDIT `croc.bat`
- Change the line "SET_YOUR_CODE_HERE" to your password. **6+ character**
e.g: `powershell -NoExit -Command "Croc send --code PASSWORD999 \"$(Get-Clipboard)\""`


## Usage & Config
  
 **File Transfer**


**Upload** ![](https://i.imgur.com/81GPsUN.png)
   - Right-click the file/folder you want to upload.
   - Select `Upload`, give the receiver your password.

**Download** ![](https://i.imgur.com/SZCXfZf.png)
   - Right-click in any directory you want the files to be downloaded in.
   - Select `Download`, and insert the password provided by the uploader.

(Upload is active only when you select a file, and Download is active only when you right-click an empty space)


 **Configure Croc:**
   Make Croc auto accepts once you insert a password without typing "Y" to confirm everytime.
- From powershell run `Croc --yes --remember`
- Insert a password "You can transfer a file to yourself to save the configuration".

If you want to generate a unique code everytime you want to share a file simly remove the command `--code`& your code from `croc.bat`.

**Most of the scripts below will be executed with a minimized window, DO NOT PANIC when you click and see nothing, it's minimized, just open the window to see the progress**
## YouTube & X downloader 
![](https://i.imgur.com/5slVepk.png)
- Copy the video's link
- Right-Click an empty space (This is where your video will be saved in)
- Hover over Youtube, and select either `Video` or `Audio`.
- It will start installing instantly if everything is configured correctly.

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

## Search & Draw & Clean Temp & Wallpaper Changer (Found under "File Manage"

![](https://i.imgur.com/JrNBaGz.png)

**Search**
- Type the name of the file, search in all directory
- Copy the path you want to look for, and paste it in the same window to open the path and highlight the file.



**Draw**
- Right Click to Draw, Left Click to change color
- Mousewheel to change opacity of canvas
- ESC to stop and close



**Clean Temp**
- This will clean all of `temp`,`cache`,`recent`,`cookies`, and `prefetch`. 


**Wallpaper Changer**

You need to aquire the API from "https://api.unsplash.com".
It's free of charge and easy to sign-up. Once you create your Application page setup in `unsplash` you'll get your own free API.
- Copy your `Access Key`
- Open `wallpaper.py` located in Nilesoft's folder `script`
- Replace the key with "YOUR_ACESS_KEY"
- Save & Exit

**Color Picking**
- Shows the pixel color your cursor is pointing at, right click to copy it to clipboard


**Merge media**
- Merge 2 media files to overlap. 



**StremiM**

![](https://i.imgur.com/wD3OsGX.png)

Stream anything from Stremio using peario with an automation to open peario + stremio + copy share link + send it to a friend, friend can type your code and it will automatically retrieves that link + opens peario and stremio and starts watching. 

You'll need Stremio properly installed for both devices and optionally configured with "Torrentio".

You'll also need to edit the "Stream.bat" file in `Script > stremiM folder, and scroll down to find "YOUR_CODE_HERE", replace it with your code "minimum 6". 

Then you just right-click "Stream" , search a movie / series and click "Copy link". 

![](https://i.imgur.com/vor6wI7.png).

The script will automatically detect that a link is copied and will send it using "Croc".

To watch, click "Watch", type your friend's code, it will retreve the link, pastes it in chrome and opens it as an app. 

The script will automatically resends the link multiple times if you have more than 1 friend you want to share the link to it will do it automatically after you copy the link just set and wait for all of them to connect, it will loop until you're done. 

**Account Switching**
- I might update this with my own Valorant account switching configuration, which uses TcNo Account Switching but for now TcNo has too many bugs so I'll updat this later.


**Remove/Add/Edit**
- In the GUI in taskbar > Shell > modify
- You can add any item to Hide box to hide it everywhere, or in More options menu or active with Shift button, just drag an id from the ids list and drop it in any of the boxes. 
- You can edit any option in context menu's name and icon, write the old name, and the new name you want and if you don't want to add a custom icon you can leave the icon option blank, it will use the default icon. 
- You can see and delete any custom display name to set it as the default name and icon.

**GUI Theme editor**
- Taskbar > Shell > theme 

## Screenshots

![upload](https://i.imgur.com/OGehNdS.png)
![downloading](https://i.imgur.com/tMEe1wy.png)
![Draw](https://i.imgur.com/U6syLCl.png)
![HEX](https://i.imgur.com/qQvxrdB.png)
![](https://i.imgur.com/c6O9rAK.png)
![](https://i.imgur.com/kdpAAlv.png)


**Undo/Redo** 

Add this command anywhere in shell.nss to remove it (at the very bottom will do). 
(Right-click taskbar > shell > config)

```
remove(find="undo|redo")
```

**Add GUI to taskbar**

![](https://i.imgur.com/lWG7w2c.png)

- If you already have all the files in my repo updated you do not need to do the below.

- Go to Nilesoft's installation folder > script > place the "theme.pyw" in script
- Go to imports > taskbar > edit and place this script in a convenient place e.g: under `Config and Directory`

```
item(title='Theme' cmd='C:\Program Files\Nilesoft Shell\script\theme.pyw' image='C:\Program Files\Nilesoft Shell\icons\theme.ico')
```

## issues & fixes
- yt-dlp needs both "Python `Set to path correctly` and ffmpeg `Set to path correctly`" to run. Make sure you have both set if you're having issues with it.
- Draw does not undo entire action, only pixel by pixel. This still has no fix, you can contirbute if you know the fix. 
- Color picking only works on 1 monitor, I'll try to fix this.
- If you run Background remover the first time it might not work or takes too long to finish, a temporary fix is to close the script and run it again, this only occurs the first time you run it.
- Sometimes "Reduce" makes files larger instead of making it smaller, this happens when file size is already small. 

## License

This project is licensed under the [MIT License](LICENSE).
