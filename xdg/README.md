# galaview.sh as default image viewer

* `galaview.desktop` is placed in `~/.local/share/applications/`
* `xdg` commands to change default image viewer
```
xdg-mime query filetype image.jpg
image/jpeg
xdg-mime default galaview.desktop image/jpeg
xdg-open image.jpg
```
