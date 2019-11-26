[app]
title = BubbleKiller
package.name = bubblekiller
package.domain = com.manatlan.guy
source.dir = .
source.include_exts =
version = 0.1
requirements = python3,kivy,tornado
presplash.filename = %(source.dir)s/static/logo.png
icon.filename = %(source.dir)s/static/logo.png
orientation = portrait
osx.python_version = 3
osx.kivy_version = 1.9.1
fullscreen = 0
android.permissions = INTERNET
android.api = 28
android.ndk = 17c
android.arch = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
