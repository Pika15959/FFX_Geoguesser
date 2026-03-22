# FFX_Geoguesser
Input random NPCs in locations for a FFX-based Geoguess Game

Required Folder Structure Arrangement:
Make a folder on your deskptop and place therin the Geoguesser.py, a folder named 'data' and a folder named 'outputs'.
![bandicam 2026-03-22 11-09-05-271](https://github.com/user-attachments/assets/8a1e006e-b83c-4f7b-823e-af7db902bcb9)

Within data create place all the other files on this repo. and a folder called 'master';
![bandicam 2026-03-22 11-08-58-164](https://github.com/user-attachments/assets/5faf3f70-8219-44a5-a4fa-c73673c917eb)

Using .VBF browers, extract a copy of all the English text files and the .ebp we will be editing.

1) Copy this obj_ps3 folder using the VBF browser and place it correctly within the Geoguesser 'master' folder such that it's folder structure matches the original games. (ENGLISH TEXT FILES)
![bandicam 2026-03-22 11-14-25-243](https://github.com/user-attachments/assets/144a523a-d37f-4ee7-8768-67b5810e67ea)

2) Copy this obj folder similarly that contains the .ebp files and place it;
![bandicam 2026-03-22 11-16-49-671](https://github.com/user-attachments/assets/d52598f0-12fe-4143-8dd8-a4549a99c0be)

How the code operates is that it uses these files in the Geoguess folders to create edited variants of each file within the 'outputs' folder.
So that you can run around the game, place Geoguess Models and Text and after you're done, navigate to the 'outputs' folder and copy and paste it into the EXTERNAL FILE LOADERS FFX folder that contains 'master'.
Thus saving individual placement.


REQUIRED MODULES:
Python modules you need to install to work the Geoguesser;

import tkinter as tk
from tkinter import ttk, messagebox
import pymem
import pymem.process
import struct
import csv
import os
import shutil
import re
import time
import json
import subprocess

Try in Command Run;
pip install tkinter
pip install pymem
...
etc.
