menu(find='.mkv|.mp4|.webm|.flv|.m4p|.mov|.png|.jpg|.jpeg|.svg|.webp|.bmp|.ico' title='Tools' image =\uE0F8)
{
    item(find='.png|.jpg|.jpeg|.svg|.webp|.bmp' 
    title='Upload to imgur' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "@app.dir\script\imgur.pyw"' image=\uE14F)

    item(find='.png|.jpg|.jpeg|.svg|.webp|.bmp|.ico'
    title='Resize Image' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "@app.dir\script\resize_image.bat"' image=\uE150)

    item(find='.mkv|.mp4|.webm|.flv|.m4p|.mov'
    title='Resize Video' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "@app.dir\script\resize_video.bat"' image=\uE248)
    
    item(find='.mkv|.mp4|.webm|.flv|.m4p|.mov'
    title='MP4>MP3' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "@app.dir\script\mp4-3.bat"' image=\uE154)

    item(find='.mkv|.mp4|.webm|.flv|.m4p|.mov'
    title='Video>Gif' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "@app.dir\script\vid2gif.bat"' image=\uE1F9)

    item(find='.mkv|.mp4|.webm|.flv|.m4p|.mov'
    title='Reduce Size' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "@app.dir\script\reduce.bat"' image=\uE0D7)

    item(find='.mkv|.mp4|.webm|.flv|.m4p|.mov'
    title='Merge' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "@app.dir\script\merge.bat"' image=\uE1AC)
}


