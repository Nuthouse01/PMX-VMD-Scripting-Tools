# Nuthouse01 - 07/24/2020 - v4.63
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


# first, system imports
from typing import List

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from . import nuthouse01_core as core
except ImportError as eee:
	try:
		import nuthouse01_core as core
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = None



class VmdHeader(object):
	def __init__(self, version, modelname):
		self.version = version
		self.modelname = modelname
	def __str__(self) -> str:
		return "[%d, %s]" % (self.version, self.modelname)


class VmdBoneFrame(object):
	def __init__(self, name:str="", f:int=0, pos:List[float]=None, rot:List[float]=None,
				 phys_off:bool=False, interp:List[int]=None):
		if pos is None: pos = [0.0] * 3
		if rot is None: rot = [0.0] * 3
		if interp is None: interp = [0] * 16
		self.name = name
		self.f = f
		self.pos = pos  # X Y Z
		self.rot = rot  # X Y Z euler angles in degrees
		self.phys_off = phys_off
		# interp = [x_ax, y_ax, z_ax, r_ax, 	x_ay, y_ay, z_ay, r_ay,
		# 			x_bx, y_bx, z_bx, r_bx, 	x_by, y_by, z_by, r_by]
		self.interp = interp  # 16x int [0-127], see readme for interp explanation
	def list(self) -> list:
		return [self.name, self.f, *self.pos, *self.rot, self.phys_off, *self.interp]
	def __str__(self) -> str:
		return str(self.list())


class VmdMorphFrame(object):
	def __init__(self, name:str="", f:int=0, val:float=0.0):
		self.name = name
		self.f = f
		self.val = val
	def list(self) -> list:
		return [self.name, self.f, self.val]
	def __str__(self) -> str:
		return str(self.list())


class VmdCamFrame(object):
	def __init__(self, f:int=0, dist:float=0.0, pos:List[float]=None, rot:List[float]=None, interp:List[int]=None,
				 fov:int=0, perspective:bool=True):
		if pos is None: pos = [0.0] * 3
		if rot is None: rot = [0.0] * 3
		if interp is None: interp = [0] * 24
		self.f = f
		self.dist = dist
		self.pos = pos  # X Y Z float
		self.rot = rot  # X Y Z float euler angles in degrees
		# interp = [x_ax, x_bx, x_ay, x_by, 	y_ax, y_bx, y_ay, y_by, 				z_ax, z_bx, z_ay, z_by,
		# 			r_ax, r_bx, r_ay, r_by,		dist_ax, dist_bx, dist_ay, dist_by, 	ang_ax, ang_bx, ang_ay, ang_by]
		self.interp = interp  # 24x int [0-127], see readme for interp explanation
		self.fov = fov  # int
		self.perspective = perspective
	def list(self) -> list:
		return [self.f, self.dist, *self.pos, *self.rot, *self.interp, self.fov, self.perspective]
	def __str__(self) -> str:
		return str(self.list())


class VmdLightFrame(object):
	def __init__(self, f:int=0, color:List[int]=None, pos:List[float]=None):
		if color is None: color = [0] * 3
		if pos is None: pos = [0.0] * 3
		self.f = f
		self.color = color  # R G B int [0-255]
		self.pos = pos  # X Y Z
	def list(self) -> list:
		return [self.f, *self.color, *self.pos]
	def __str__(self) -> str:
		return str(self.list())


class VmdShadowFrame(object):
	def __init__(self, f:int=0, mode:int=0, val:int=0):
		self.f = f
		self.mode = mode  # int (0=off, 1=mode1, 2=mode2)
		self.val = val  # int [0-9999]
	def list(self) -> list:
		return [self.f, self.mode, self.val]
	def __str__(self) -> str:
		return str(self.list())


class VmdIkbone(object):
	def __init__(self, name:str="", enable:bool=False):
		self.name = name
		self.enable = enable
	def list(self) -> list:
		return [self.name, self.enable]
	def __str__(self) -> str:
		return str(self.list())


class VmdIkdispFrame(object):
	def __init__(self, f:int=0, disp:bool=True, ikbones:List[VmdIkbone]=None):
		if ikbones is None: ikbones = []
		self.f = f
		self.disp = disp
		self.ikbones = ikbones
	def list(self) -> list:
		ret = [self.f, self.disp]
		for ik in self.ikbones:
			ret.append(ik.name)
			ret.append(ik.enable)
		return ret
	def __str__(self) -> str:
		return str(self.list())


class Vmd(object):
	def __init__(self, header:VmdHeader, boneframes:List[VmdBoneFrame], morphframes:List[VmdMorphFrame],
				 camframes:List[VmdCamFrame], lightframes:List[VmdLightFrame], shadowframes:List[VmdShadowFrame],
				 ikdispframes:List[VmdIkdispFrame]):
		# header = version, modelname
		# self.version = version
		# self.modelname = modelname
		self.header = 		header
		self.boneframes = 	boneframes
		self.morphframes = 	morphframes
		self.camframes = 	camframes
		self.lightframes = 	lightframes
		self.shadowframes = shadowframes
		self.ikdispframes = ikdispframes
		
if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 07/24/2020 - v4.63")
	core.pause_and_quit("you are not supposed to directly run this file haha")


