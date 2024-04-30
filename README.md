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
   [Download Installer](#) (insert link here)

2. **Run Installer:**
   - Execute `iMShare.exe` and let the magic happen.
   - After installation, update your Context menu by holding `CTRL`+`RIGHT CLICK` anywhere.

   *Note: If context menu doesn't update, try restarting Windows Explorer from Task Manager.*

3. **Manual Installation:**
   - Run the following command-lines:
     ```bash
     winget install Nilesoft.Shell
     winget install Schollz.Croc
     ```

4. **Download iMShare Scripts:**
   [Download iMShare Scripts](#) (insert link here)
   Extract and copy the contents to Nilesoft Shell's installation folder.

5. **Edit shell.nss:**
   - If you already have Nilesoft installed with a custom `shell.nss`, add the following line at the bottom:
     ```bash
     import 'imports/iMShare.nss'
     ```

## Usage
  
1. **Upload:**
   - Right-click the file/folder you want to upload.
   - Navigate to `iMShare` > `Upload`.

2. **Download:**
   - Right-click in any directory you want the files to be downloaded.
   - Navigate to `iMShare` > `Download`, and insert the password provided by the uploader.

 **Configure Croc:**
   - Edit `Croc.bat` in `C:\Program Files\Nilesoft\script` to set your own password with "--code" followed by your password (minimum 6 digits).
This will be used by the Downloader to type and download without having to copy your randome generated password.

+ Pros: Easy to memories, same password every time the downloader inserts. 
- Cons: Obviously security, I suggest to avoide setting the password easy to guess. 

## Important Note
The Download script will only accept 6+ digits. 

## Screenshots


![upload](https://i.imgur.com/OGehNdS.png)
![downloading](https://i.imgur.com/tMEe1wy.png)

## Donate

- [PayPal](https://www.paypal.com/paypalme/imaboud)
- [Buy Me a Coffee](https://buymeacoffee.com/imaboud)


## License

This project is licensed under the [MIT License](LICENSE).
