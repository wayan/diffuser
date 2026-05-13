"""filename.py

   Here a short but significant description of what the script do 

"""

import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import MF12 

holder = MF12.holderLocLine()
Part.show(holder, "holder")

