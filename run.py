import sys
from PyQt5.QtWidgets import QApplication

from core.daemon import daemonize
from core.pets import DesktopPet

if __name__ == '__main__':
    argv = sys.argv
    if "--daemon" in argv:
        daemonize()

    tray = "--tray" in argv
    app = QApplication(argv)
    pet = DesktopPet(tray=tray)

    # 默认模式直接显示宠物，托盘模式不主动显示
    if not tray:
        pet.show()
        pet.welcomePage()

    sys.exit(app.exec())