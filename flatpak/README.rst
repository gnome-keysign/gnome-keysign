Note
----------

These instructions do only apply if you want to build the flatpak yourself.
For installing the app, Flathub is most likely the best place to go:
https://flathub.org/apps/details/org.gnome.Keysign


Building
--------------

Build the software in flatpak using a command like this:

    flatpak-builder  --force-clean -v  --repo=/var/tmp/fb.repo --gpg-sign=tobiasmue@gnome.org  fpbuilder org.gnome.Keysign.json

That will have populated the *repository* in /var/tmp/fb.repo with the build.


Then, you have to make the build known in the repository:

    flatpak build-update-repo --title='GNOME Keysign' --generate-static-deltas --prune --prune-depth=5  --gpg-sign="tobiasmue@gnome.org"  /var/tmp/fb.repo


To create a bundle file, use something like the following:


    gpg2 --output="$HOME/tobiasmue@gnome.org.gpg.asc" --armor --export \
            "tobiasmue@gnome.org"


    flatpak build-bundle \
        --repo-url=https://muelli.cryptobitch.de/flatpak \
        --gpg-keys="$HOME/tobiasmue@gnome.org.gpg.asc" /var/tmp/fb.repo   \
        GNOME-Keysign.flatpak org.gnome.Keysign           \
        master


Installation
--------------

Several options for installing a flatpaked application exist.

With a flatpakref you can have an application as well as its runtime
installed with little effort.

    flatpak install --from https://muelli.cryptobitch.de/tmp/2017-01-29-keysign.flatpakref


If that does not work or you would like to install the application manually,
e.g. because you want to install a particular version,
you need to install a runtime first.
We use a GNOME runtime which you can get from Flathub.
In order to add flathub to your repositories, you can execute the following:

    flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

Then you can try to install the runtime with the following command:

    flatpak --user install --runtime flathub org.gnome.Platform//3.26



Then, if you have a bundle file of GNOME Keysign, you can do

    flatpak install --user --bundle GNOME-Keysign.flatpak


Otherwise, you have to manually add the repository and install from there:

    flatpak remote-add --user --gpg-import=$HOME/tobiasmue@gnome.org.gpg.asc   gks https://muelli.cryptobitch.de/flatpak/

    flatpak install --verbose --user gks org.gnome.Keysign




Repository
--------------

If you haven't done so already, you need to make the latest build
known to the (local) repository with the *build-update-repo* mentioned
above.

Then, you can simply copy the local repository directory to a remote location:

    rsync --delete --numeric-ids  -r  --partial --progress -v --links /var/tmp/fb.repo/ server:~/public_html/flatpak/

Note that if "summary" and "summary.sig" do not get copied last,
a client won't be able to pull the lastest changes while they
are still in transit.
