pyinstaller --noconsole --onefile ^
  --hidden-import=socks ^
  --add-data "img\icon_green.png;." ^
  --add-data "img\icon_yellow.png;." ^
  --add-data "img\icon_red.png;." ^
  win7_proxymon.py