    menu(type='file' mode="multiple" title='Tools' image ='C:\Program Files\Nilesoft Shell\icons\tools.ico')
{


item(type='file' title='BGR' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "C:\Program Files\Nilesoft Shell\script\imageBR.bat"' image='C:\Program Files\Nilesoft Shell\icons\br.ico')

    menu(type='file' mode="multiple" title='Resize' image ='C:\Program Files\Nilesoft Shell\icons\resize.ico')
{
item(type='file' title='Resize Image' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "C:\Program Files\Nilesoft Shell\script\resize_image.bat"' image='C:\Program Files\Nilesoft Shell\icons\image.ico')
item(type='file' title='Resize Video' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "C:\Program Files\Nilesoft Shell\script\resize_video.bat"' image='C:\Program Files\Nilesoft Shell\icons\video.ico')

}

item(type='file' title='MP4>MP3' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "C:\Program Files\Nilesoft Shell\script\mp4-3.bat"' image='C:\Program Files\Nilesoft Shell\icons\mp4-3.ico')
item(type='file' title='Video>Gif' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "C:\Program Files\Nilesoft Shell\script\vid2gif.bat"' image='C:\Program Files\Nilesoft Shell\icons\gif.ico')
item(type='file' title='Convert' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "C:\Program Files\Nilesoft Shell\script\convert.bat"' image='C:\Program Files\Nilesoft Shell\icons\convert.ico')
item(type='file' title='Reduce' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "C:\Program Files\Nilesoft Shell\script\reduce.bat"' image='C:\Program Files\Nilesoft Shell\icons\reduce.ico')
item(type='file' title='Merge' cmd='cmd.exe' args='/c echo @sel.path | clip & start "" "C:\Program Files\Nilesoft Shell\script\merge.bat"' image='C:\Program Files\Nilesoft Shell\icons\merge.ico')



}


