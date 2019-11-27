# guy-bubble-killer-apk
Just the sources of my [guy](https://guy-docs.glitch.me/)'s demo apk : Bubble Killer's game ;-)

Here is the [apk on the playstore](https://play.google.com/store/apps/details?id=com.manatlan.guy.bubblekiller) ;-)

It's just a little game, with graphics & sound (you only need to kill all 100 bubbles as fast as you can).

It's a demo, of what you can do with [guy](https://guy-docs.glitch.me/) python lib ;-)

**Note:**
The server side is just handling the best score in its guy's config. All is done client side, with html/webcomponent/js/css.

If you want to test yourself ... Just follow the [HowTo](https://guy-docs.glitch.me/howto_build_apk_android/), to try to reproduce the apk.

To start, in an ubuntu console :

Clone this repo

    git clone https://github.com/manatlan/guy-bubble-killer-apk.git

Go in your local repo

    cd guy-bubble-killer-apk

Get a fresh version of guy.py

    rm guy.py && wget https://raw.githubusercontent.com/manatlan/guy/master/guy.py

Test, if it works locally 

    python3 main.py

Install the tools

    sudo apt install python3-kivy
    python3 -m pip install --upgrade buildozer

Connect your android phone thru usb cable & Test on it (first run could take more than 20 minutes)

    buildozer android debug deploy run

If you got the [`ERR_CLEARTEXT_NOT_PERMITTED`](https://guy-docs.glitch.me/howto_build_apk_android/#authorize-clear-text-traffic-in-your-apk) error on your android, just launch

    sed -i 's/<application android:label/<application android:usesCleartextTraffic="true" android:label/g' .buildozer/android/platform/build/dists/bubblekiller/templates/AndroidManifest.tmpl.xml

And re-run

    buildozer android debug deploy run

...
