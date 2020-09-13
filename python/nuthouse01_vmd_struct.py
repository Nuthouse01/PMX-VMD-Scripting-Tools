# Nuthouse01 - 09/13/2020 - v5.01
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


# first, system imports
from typing import List
from abc import ABC, abstractmethod

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


# this is an abstract base class that all the PMX classes inherit
# this lets them all get the __str__ method and forces them all to implement list()
# it also lets me detect any of them by isinstance(x, _BasePmx)
class _BaseVmd(ABC):
	def __str__(self) -> str: return str(self.list())
	@abstractmethod
	def list(self) -> list: pass
	def __eq__(self, other):
		if type(self) != type(other): return False
		return self.list() == other.list()


# NOTE: for simplicity, all the list() members (except Vmd.list()) should return FLAT LISTS
# that way they can be used to easily convert vmd to txt


class VmdHeader(_BaseVmd):
	def __init__(self, version: float, modelname: str):
		self.version = version
		self.modelname = modelname
	def list(self) -> list:
		return [self.version, self.modelname]


class VmdBoneFrame(_BaseVmd):
	def __init__(self,
				 name: str,
				 f: int,
				 pos: List[float],
				 rot: List[float],
				 phys_off: bool,
				 interp: List[int],
				 ):
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


class VmdMorphFrame(_BaseVmd):
	def __init__(self,
				 name: str,
				 f: int,
				 val: float,
				 ):
		self.name = name
		self.f = f
		self.val = val
	def list(self) -> list:
		return [self.name, self.f, self.val]


class VmdCamFrame(_BaseVmd):
	def __init__(self,
				 f: int,
				 dist: float,
				 pos: List[float],
				 rot: List[float],
				 interp: List[int],
				 fov: int,
				 perspective: bool,
				 ):
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


class VmdLightFrame(_BaseVmd):
	def __init__(self,
				 f: int,
				 color: List[int],
				 pos: List[float]
				 ):
		self.f = f
		self.color = color  # R G B int [0-255]
		self.pos = pos  # X Y Z
	def list(self) -> list:
		return [self.f, *self.color, *self.pos]


class VmdShadowFrame(_BaseVmd):
	def __init__(self,
				 f: int,
				 mode: int,
				 val: int
				 ):
		self.f = f
		self.mode = mode  # int (0=off, 1=mode1, 2=mode2)
		self.val = val  # int [0-9999]
	def list(self) -> list:
		return [self.f, self.mode, self.val]


class VmdIkbone(_BaseVmd):
	def __init__(self,
				 name: str,
				 enable: bool
				 ):
		self.name = name
		self.enable = enable
	def list(self) -> list:
		return [self.name, self.enable]


class VmdIkdispFrame(_BaseVmd):
	def __init__(self,
				 f: int,
				 disp: bool,
				 ikbones: List[VmdIkbone]
				 ):
		self.f = f
		self.disp = disp
		self.ikbones = ikbones
	def list(self) -> list:
		ret = [self.f, self.disp]
		for ik in self.ikbones:
			ret.extend(ik.list())
		return ret


class Vmd(_BaseVmd):
	def __init__(self,
				 header: VmdHeader,
				 boneframes: List[VmdBoneFrame],
				 morphframes: List[VmdMorphFrame],
				 camframes: List[VmdCamFrame],
				 lightframes: List[VmdLightFrame],
				 shadowframes: List[VmdShadowFrame],
				 ikdispframes: List[VmdIkdispFrame]
				 ):
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
	def list(self) -> list:
		return [self.header.list(),
				[i.list() for i in self.boneframes],
				[i.list() for i in self.morphframes],
				[i.list() for i in self.camframes],
				[i.list() for i in self.lightframes],
				[i.list() for i in self.shadowframes],
				[i.list() for i in self.ikdispframes],
				]
		
if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 09/13/2020 - v5.01")
	core.pause_and_quit("you are not supposed to directly run this file haha")


