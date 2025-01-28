<div align="center">

![](https://i.imgur.com/Nn5hli0.png)

<a href="https://www.buymeacoffee.com/imaboud" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-green.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>


- iMA Menu adds a lot of useful features right on your context menu, and allows easy theming and editing without priour programming knowledge.

![](https://i.imgur.com/fO94CpQ.png)


_____________________________________________________________________
## Download Installer

- [iMA Menu installer (3.7MB)](https://github.com/iMAboud/iMA-Menu/releases/download/v.0.7/iMA.Menu.Installer.exe)

_____________________________________________________________________
- [iMA Menu - Light](https://github.com/iMAboud/iMA-Menu/releases/download/v0.5/iMA.Menu.-.Light.exe)

Includes only the menu and Send/Receieve feature
_____________________________________________________________________




## Features

- Transfer files super fast with no size limit to any PC with just a pass code.
- Download a video or directly convert it to audio from Youtube or any site.
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
Schollz Croc|In Powershell: `winget install schollz.croc`
Python|In Powershell: `winget install -e -i --id=Python.Python.3.12 --source=winget --scope=machine` Make sure to check both add python to path and use admin.
yt-dlp|In Powershell: `python -m pip install -U yt-dlp[default]`
ffmpeg|In Powershell: `iex (irm ffmpeg.tc.ht)`
Packages |In powershell: `pip install backgroundremover pyautogui pyperclip pynput colorama pillow PyQt5`

_____________________________________________________________________

## Manual Installation

- Install all required from the table above "running the commands is recommended and easier".
- Move the folder `iMA Menu` into C:\Program Files.
- Go to "C:\Program Files\iMA Menu", and run "Shell.exe" As Admin, and click "Register".

_____________________________________________________________________


## Usage & Config
  
 **iMShare: File Transfer**

**Upload and Download** ![](https://i.imgur.com/FS5swEd.jpeg)

_____________________________________________________________________

## YouTube & other sites downloader 
![Video Downloader](https://github.com/user-attachments/assets/7bec24e9-9ca1-4c6c-8786-2d1db99c97ae)
- Copy the video's link
- Right-Click an empty space (This is where your video will be saved in)
- Hover over Youtube, and select either **Video** or **Audio**.
- It will start installing instantly if everything is configured correctly.
_____________________________________________________________________

## Video & Image editing
- Pretty much self explanatory, just Right-Click a video or an image, then > Tools > select your option.

![](https://i.imgur.com/eDjS8H1.png)
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

**Color Picking**
- Shows the pixel color your cursor is pointing at, right click to copy it to clipboard

_____________________________________________________________________

**Merge media**
- Merge 2 media files to overlap. 


_____________________________________________________________________

**StremiM** Hidden by default

<img src="https://i.imgur.com/wD3OsGX.png" alt="Modify" width="400">


Stream anything from Stremio using peario with an automation to open peario + stremio + copy share link + send it to a friend, friend can type your code and it will automatically retrieves that link + opens peario and stremio and starts watching. 

- You'll need Stremio for both devices.

- Edit the "Stream.bat" file in `Script > stremiM folder, and scroll down to find "YOUR_CODE_HERE", replace it with your code "minimum 6". 

- Then you just right-click "Stream" , search a movie / series and click "Copy link". 


- The script will automatically detect that a link is copied and will send it using "Croc".

- To watch, click "Watch", type your friend's code, it will retreve the link, pastes it in chrome and opens it as an app. 

- The script will automatically resends the link multiple times if you have more than 1 friend you want to share the link to it will do it automatically after you copy the link just set and wait for all of them to connect, it will loop until you're done. 
_____________________________________________________________________

**Settings**

![](https://i.imgur.com/Uk3TwEg.png)

- Right-click Taskbar > iMA Mneu > Settings

(Modify tab)
- You can add any item to Hide box to hide it everywhere, or in More options menu or active with Shift button, just drag an id from the ids list and drop it in any of the boxes. 
- You can edit any option in context menu's name and icon, write the old name, and the new name you want and if you don't want to add a custom icon you can leave the icon option blank, it will use the default icon. 
- You can see and delete any custom display name to set it as the default name and icon.

(Theme tab)
- Change the conext menu's theme here (UI is very ugly I know, and missing a lot of features but I'm working on it).

(Shell tab) 
- Hide any thing from context menu in (remove items)
- Add or remove a custom file containing commands or shortcuts in (import files)

(Shortcut tab)
- Add a shortcut or command in 1 file (import shortcut.nss from Shell tab if not imported).

_____________________________________________________________________

## Screenshots

<img src="https://i.imgur.com/U6syLCl.png" alt="Draw" width="400">
<img src="https://i.imgur.com/qQvxrdB.png" alt="HEX" width="400">
<img src="https://i.imgur.com/2im6aLx.png" alt="Theme" width="400">
<img src="https://i.imgur.com/DXE4QFi.png" alt="Modify" width="400">
<img src="https://i.imgur.com/2i7VYLF.png" alt="Search" width="400">
<img src="https://i.imgur.com/kclvUGm.png" alt="Shell" width="400">
<img src="https://i.imgur.com/sO6JntG.png" alt="Video Downloader" width="400">
<img src="https://i.imgur.com/OGehNdS.png" alt="upload" width="400">
<img src="https://i.imgur.com/tMEe1wy.png" alt="downloading" width="400">
<img src="https://i.imgur.com/L40lJKt.png" alt="shortcut" width="400">

_____________________________________________________________________
  
## License

This project is licensed under the [MIT License](LICENSE).

</div>

