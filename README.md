# iMShare

iMShare adds Download / Upload options to the Context Menu for easy file transfer between devices with just 1 click.
Click a file to upload and give the downloader your password, or click anywhere to download in the same path you're in and type the password. 

<p align="center">
  <img src="https://github.com/iMAboud/iMShare/assets/80198949/3c6c70d6-f609-4516-9388-ca627dd5bba2">
</p>


## Features

- Lightweight, fast, easy, portable and no server hosts, you're your own server.
- Fully automated, with commands recognizing where you click for download and upload.
- Installs both Nilesoft Shell and Schollz Croc.
- Additional features and config details from [Nilesoft](https://github.com/moudey/Shell) and [Croc](https://github.com/schollz/croc) repositories.

## Download & Installation

1. **Download Installer:**
   Light version (recommended) [Download](https://github.com/iMAboud/iMShare/raw/main/iMShare.exe)
   This is a light, clutter free version comes with a theme and smaller compact context menu.

   Default (Nilesoft's version) [Download](https://github.com/iMAboud/iMShare/raw/main/iMShare_default.exe)

2. **Run Installer:**
   - Execute `iMShare.exe` and let the magic happen.
   - After installation, you'll be prompted with Nilesoft Shell to register to context menu
     Press `CTRL`+`R` to update the Explorer.
     Close Shell prompt now.
   For any changes in scripts, theme or config just press `CTRL`+`RIGHT CLICK` anywhere.

   *Note: If context menu doesn't update, try restarting Windows Explorer from Task Manager.*

 **Manual Installation:**
   - Run the following command-lines:
     ```bash
     winget install Nilesoft.Shell
     winget install Schollz.Croc
     ```

 **Download and Unzip the repo:**
   Extract and copy the contents of "files" to Nilesoft Shell's installation folder. default: `C:\Program files\Nilesoft Shell`

 **Edit shell.nss:**
   - In Nilesoft's folder, edit  `Shell.nss` and add : 
     ```bash
     import 'imports/iMShare.nss'
     ```
     
*Note: Nilesoft website goes down recently quit a lot, so in the meantime, the installer will not install Nilesoft.Shell with the latest update, instead it's preloaded with the portable version 1.9.15.

## Usage
  
 **Upload:**
   - Right-click the file/folder you want to upload.
   - Navigate to `iMShare` > `Upload`.

 **Download:**
   - Right-click in any directory you want the files to be downloaded.
   - Navigate to `iMShare` > `Download`, and insert the password provided by the uploader.

 **Configure Croc and add your own password:**
   - Edit `Croc.bat` in `C:\Program Files\Nilesoft\script` to set your own password with "--code" followed by your password (minimum 6 digits).

Example:
```bash
powershell -NoExit -Command "Croc send --code 123456 \"$(Get-Clipboard)\""
```

   *Change `123456` to your password*
This will be used by the Downloader to type and download without having to copy your randome generated password.


 ## Auto accept:
By default, you must press "Y" to accept receiving any file, to allow transfer without the need to accept just run in powershell/cmd: 

```bash
croc --yes --remember
```


You'll be prompted to type a code from the uploader type anything, accept one last time to confirm and save your config.


## Screenshots

![upload](https://i.imgur.com/OGehNdS.png)
![downloading](https://i.imgur.com/tMEe1wy.png)


## Debug
Croc might not register itself by default to path, if you run into issues with transfering add croc to path in "System Environment Variables".
Croc path `C:\Users\YourUser\AppData\Local\Microsoft\WinGet\Packages\schollz.croc_Microsoft.Winget.Source_xxxxxx`

## Donate

- [PayPal](https://www.paypal.com/paypalme/imaboud)
- [Buy Me a Coffee](https://buymeacoffee.com/imaboud)


## License

This project is licensed under the [MIT License](LICENSE).
