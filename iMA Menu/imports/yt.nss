menu(
    type='namespace|back' 
    title='YouTube' 
    image=\uE248
    where = '@(str.contains(clipboard.get, "youtube.com/watch"))'
)
{
    item(title='Video' cmd='@app.dir\script\video.bat' image=\uE248)
    item(title='Audio' cmd='@app.dir\script\audio.bat' image=\uE155)
}

menu(
    type='namespace|back' 
    title='X' 
    image=\uE248
    where = '@(str.contains(clipboard.get, "x.com"))'
)
{
    item(title='Video' cmd='@app.dir\script\video.bat' image=\uE248)
    item(title='Audio' cmd='@app.dir\script\audio.bat' image=\uE155)
}

menu(
    type='namespace|back' 
    title='Reddit' 
    image=\uE248
    where = '@(str.contains(clipboard.get, "redd.it"))'
)
{
    item(title='Video' cmd='@app.dir\script\video.bat' image=\uE248)
    item(title='Audio' cmd='@app.dir\script\audio.bat' image=\uE155)
}

menu(
    type='namespace|back' 
    title='TikTok' 
    image=\uE248
    where = '@(str.contains(clipboard.get, "tiktok.com"))'
)
{
    item(title='Video' cmd='@app.dir\script\video.bat' image=\uE248)
    item(title='Audio' cmd='@app.dir\script\audio.bat' image=\uE155)
}

menu(
    type='namespace|back' 
    title='Twitch' 
    image=\uE248
    where = '@(str.contains(clipboard.get, "twitch.tv"))'
)
{
    item(title='Video' cmd='@app.dir\script\video.bat' image=\uE248)
    item(title='Audio' cmd='@app.dir\script\audio.bat' image=\uE155)
}

menu(
    type='namespace|back' 
    title='Instagram' 
    image=\uE248
    where = '@(str.contains(clipboard.get, "instagram.com"))'
)
{
    item(title='Video' cmd='@app.dir\script\video.bat' image=\uE248)
    item(title='Audio' cmd='@app.dir\script\audio.bat' image=\uE155)
}

