# RinvosBlendshapeTransfer
Blender plugin for transfering blendshapes between the meshes

Initially made for VRChat, but might be useful elsewhere.

I made this plugin for myself a bit ago, but it was too useful to keep it in my private library. 
Used on a bunch of my own assets and contunuing to use it every time i need to fit stuff - tho beware that it still requires cleanup after tranfer in a lot of cases.

> all the limitation of the underlying Surface Defrom modifier also apply to this plugin, it just automates the process and give some pre-processing options to potentially increase the quality

Experiment with it, you might find perfect settings for your case by just playing around with it.

## Quick Start Guide

### Installation 
1. Download the .zip file for the plugin [here](https://github.com/neongm/RinvosBlendshapeTransfer/releases)
2. Open Blender and go to Edit > Preferences > Add-ons.
3. Click Install... and select the downloaded .zip file.
4. Enable the plugin by checking the box next to its name.

### Usage
1. In the 3D View, open the `Blendshape` panel in the sidebar (press N to open the sidebar).
2. Select the Source object (the object with the blendshapes you want to transfer).
3. Select the Target object (the object that will receive the blendshapes).
4. Click the Transfer Blendshapes button to start the transfer.



## Advanced usage

### Pre-Processing Modifiers
To increase quality of transfer you can use Pre-Processing Modifiers. At the time of launch, there are 2 available:
1. Subdivision surface - smoothes out source mesh for the transfer to have more data to work with
2. Displace - displaces geometry to get it closer to the target object


Sometimes they will significantly increase the transfer quality even with default settings, but be careful when using subdivision with high values on dense meshes, its very computationlly expensve. It usually doens't need to go above 1-2x. 

> Both modifiers can be previewed using a preview checkbox next to their settings.

### Masking
Plugin creates a mask for the transfer, everyting red - will be transfered fully, everything blue - won't be transfered at all. You can pain in the areas you want or don't want to transfer by clicking "Draw Transfer Mask" button in the UI.



## Other info

If you want to follow the devempment, report bugs, or just help with any of my stuff, join my tiny discord community or just see my other stuff, all the links are here: 

- Discord Server - [Rinvo's Lowpoly Shack](https://discord.gg/gnSr2gysbf)
- Twitter - [Rinvo](https://x.com/rinvovrc)
- Bsky - [Rinvo.bsky.social](https://bsky.app/profile/rinvo.bsky.social)
- Carrd - [Rinvo.carrd.co](https://rinvolinks.carrd.co/)


#### Thanks for support:3
