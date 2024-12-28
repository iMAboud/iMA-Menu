menu(type='file|dir' mode="multiple" title='Tools' image =\uE0F8)
{
    item(type='file' title='Upload' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "@app.dir\script\imgur.bat"' image=\uE14F)
    menu(type='file' mode="multiple" title='Resize' image =\uE1B1)
    {
        item(type='file' title='Resize Image' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "@app.dir\script\resize_image.bat"' image=\uE150)
        item(type='file' title='Resize Video' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "@app.dir\script\resize_video.bat"' image=\uE248)
    }
    item(type='file' title='MP4>MP3' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "@app.dir\script\mp4-3.bat"' image=\uE154)
    item(type='file' title='Video>Gif' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "@app.dir\script\vid2gif.bat"' image=\uE1F9)
    item(type='file' title='Convert' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "@app.dir\script\convert.bat"' image=\uE153)
    item(type='file' title='Reduce' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "@app.dir\script\reduce.bat"' image=\uE0D7)
    item(type='file' title='Merge' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "@app.dir\script\merge.bat"' image=\uE1AC)
}


