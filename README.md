Please consider getting the installer from my [Gumroad account](https://3dcgguru.gumroad.com/l/jowgd) as this allows me to more easily announce updates and track the userbase.


![maya2024](https://img.shields.io/badge/Maya_2024-tested-brightgreen.svg)
![maya2023](https://img.shields.io/badge/Maya_2023-tested-brightgreen.svg)
![maya2022](https://img.shields.io/badge/Maya_2022-tested-brightgreen.svg)

![casc](https://img.shields.io/badge/Cascadeur_2023.2+-required-red.svg)

![Windows](https://img.shields.io/badge/Windows-tested-blue)


# cg3d-maya-casc
Easily bridge data between Maya and Cascadeur with this Maya Module.

[Youtube video on how to use](https://youtu.be/BQiqKtXEmP4)

# Installation

Notes:
Python 3 is required for Maya 2022. 

The installation can be found under documents\maya\modules\

If the tool gives you issues you can open the cascadeur.mod file in a text editor and replace the + to -, to avoid loading the tool.  You can also simply delete the cascadeur.mod file and folder.

## Drag & Drop
The easiest way to install this application is to ...
1. Click this File Link > [maya_casc_installer.py](https://github.com/Nathanieljla/cg3d-maya-casc/releases/download/v1.1.0/maya_casc_installer.py) < to download the installation python file.
2. Drag-n-drop it from the browser into a maya-viewport. 
This will automatically install all the dependencies without requiring admin privileges into your user-directory.
3. Hit 'Install'.  If any pop-ups appear, say "yes" or "allow".  The installer will likely take 20+ seconds.
4. when closing Maya for the first time after installing the scripts you'll likely see a question like this:
   ![image](https://github.com/Nathanieljla/cg3d-maya-casc/assets/1466171/3c40331a-5e3b-4151-85c5-1e2127ff3f28)
   
 (you can say 'yes' to the question)

 # Revisions
 ### 1.1.2
 Updated to support Cascadeur 2024.1
 Updated package dependencies to be version specific
 
 
 ### 1.1.0
 
 Updated the installer to support upgrading if a previous install is found.
 
 Added a preferences menu.
 
 Added support for exporting sparse key data.
 
 Fixed textures not being sent to Cascadeur in certain situations.
 
 ### 1.0.1
 
 Bug fixes for Maya 2022.
   

