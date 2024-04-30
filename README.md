# iMShare

iMShare adds Download / Upload options to the Context Menu for easy file transfer between devices with just 1 click. It comes pre-configured with Nilesoft Shell's "personal theme" to customize the context menu, add or remove any shortcut, function, or command. Additionally, it includes Schollz Croc for fast and convenient file transfers.

![context](https://github.com/iMAboud/iMShare/assets/80198949/3c6c70d6-f609-4516-9388-ca627dd5bba2)

## Features

- Lightweight, fast, easy, and portable.
- Fully automated, with commands recognizing where you click for download and upload.
- Installs both Nilesoft Shell and Schollz Croc.
- Additional features from [Nilesoft](https://github.com/moudey/Shell) and [Croc](https://github.com/schollz/croc) repositories.

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
Pros: Easy to memories, same password every time the downloader inserts. 
Cons: Obviously security, I suggest to avoide setting the password 123456. 

## Important Note
The Download script will only accept 6+ digits. 
This is for security reasons, however, if you insert less than 6 digits it will make it up to 6 digits by repeating the last digit until the total is 6. 
This is made so you could create a password with less than 6 digits 

e.g: if your name is John which is less than 6 digits you can set the password to "JOHNNN" , but the downloader will only need to type "JOHN" and the script will repeat the "N" exactly 2 times to be JOHNNN for you. 

## Screenshots


![upload](https://i.imgur.com/OGehNdS.png)
![downloading](https://i.imgur.com/tMEe1wy.png)

## Donate

- [PayPal](https://www.paypal.com/paypalme/imaboud)
- [Buy Me a Coffee](https://buymeacoffee.com/imaboud)


## License

This project is licensed under the [MIT License](LICENSE).
