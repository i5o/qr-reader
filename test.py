import sys, os
DATA = os.path.join(os.getcwd(), "tools", "64")
LIB = os.path.join(DATA, "lib")
sys.path.append(DATA)
os.environ["LD_LIBRARY_PATH"] = LIB
os.environ["GST_LIBRARY_PATH"] = LIB
from qrtools import QR
myCode = QR(filename="/home/ignacio/qr2.png")
if myCode.decode():
  print myCode.data_to_string()

