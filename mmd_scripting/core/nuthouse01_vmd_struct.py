import abc
import copy
import enum
import sys
import traceback
from typing import List, Union

import mmd_scripting.core.nuthouse01_core as core

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.04 - 8/19/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

__all__ = ['ShadowMode', 'Vmd', 'VmdBoneFrame', 'VmdCamFrame', 'VmdHeader', 'VmdIkbone', 'VmdIkdispFrame',
		   'VmdLightFrame', 'VmdMorphFrame', 'VmdShadowFrame']

# this is an abstract base class that all the PMX classes inherit
# this lets them all get the __str__ method and forces them all to implement list()
# it also lets me detect any of them by isinstance(x, _BasePmx)
class _BaseVmd(abc.ABC):
	def copy(self):
		""" Return a separate copy of the object. """
		return copy.deepcopy(self)
	def __str__(self) -> str: return str(self.list())
	@abc.abstractmethod
	def list(self) -> list: pass
	
	@abc.abstractmethod
	def _validate(self, parentlist=None):
		""" This is overloaded for each class and contains the actual assertion statements.
		Should not be called directly. """
		pass
	
	def validate(self, parentlist=None) -> bool:
		""" This performs type-checking and input validation on the item, as a way to protect against bad code
		assigning invalid values or incorrect datatypes into my structures. If it fails it will raise an Exception
		of some kind and probably print a stack trace I guess?"""
		try:
			# run all assertion checks on this item
			self._validate(parentlist)
			return True
		except AssertionError as e3:
			# if there is an assertion error, print the raw traceback to default console
			# traceback.print_exc()
			exc_type, exc_value, exc_traceback = sys.exc_info()
			something = traceback.extract_tb(exc_traceback, limit=None)
			
			# print some more selective stack trace info to the GUI
			# maybe print the whole stack trace to GUI console? it formats just fine
			lowesttrace = something[-1]
			core.MY_PRINT_FUNC(
				'VALIDATE ERROR: Object "{}" failed validation check "{}" at line "{}" in nuthouse01_vmd_struct.py'.format(
					self.__class__.__name__, lowesttrace.line, lowesttrace.lineno
				))
			core.MY_PRINT_FUNC("This happens when the PMX/VMD object has incorrect data sizes/types.")
			core.MY_PRINT_FUNC("Figure out why/how bad data got into this field, then stop it from happening in the future!")

			# determine "which index this is within the whole object" if possible???
			if parentlist is not None:
				idx = self.idx_within(parentlist)
				if idx is not None:
					core.MY_PRINT_FUNC(
						'Object {} found at index {} of containing list'.format(self.__class__.__name__, idx))
			raise RuntimeError("validation fail") from e3
		except RuntimeError:
			# if there is a runtime error, only do the "determine which index this is" part
			# determine "which index this is within the whole object" if possible???
			if parentlist is not None:
				idx = self.idx_within(parentlist)
				if idx is not None:
					core.MY_PRINT_FUNC(
						'Object {} found at index {} of containing list'.format(self.__class__.__name__, idx))
			# raise with no arg to re-raise the same exception
			raise
	
	def __eq__(self, other):
		if type(self) != type(other): return False
		return self.list() == other.list()
	def idx_within(self, L: List) -> Union[int, None]:
		"""
		If you have the object and the list it lives in, this will find where it is within the list.
		:param L: the list it lives in
		:return: the index if it is found; None otherwise
		"""
		for d, thing in enumerate(L):
			if self is thing: return d
		return None

def is_good_vector(length:int, thing) -> True:
	""" Used in the "validate" member of each class for code reuse... returns a bool so if an assertion fails, it
	will point at the check for "is_good_vector" of a specific member of a specific object class, instead of pointing
	at this used-everywhere function. """
	# thing is a list, and has specific length, and all members are int/float
	return isinstance(thing, (list, tuple)) \
		   and len(thing) == length \
		   and all(isinstance(a, (int,float)) for a in thing) # and all(float("-inf") < a < float("inf") for a in thing)
def is_good_flag(thing) -> True:
	""" Used in the "validate" member of each class for code reuse... returns a bool so if an assertion fails, it
	will point at the check for "is_good_vector" of a specific member of a specific object class, instead of pointing
	at this used-everywhere function. """
	return (thing is 1) or (thing is 0) or (thing is True) or (thing is False)


class ShadowMode(enum.Enum):
	OFF = 0
	MODE1 = 1
	MODE2 = 2


# NOTE: for simplicity, all the list() members (except Vmd.list()) should return FLAT LISTS
# that way they can be used to easily convert vmd to txt


class VmdHeader(_BaseVmd):
	def __init__(self, version: int, modelname: str):
		self.version = version
		self.modelname = modelname
	def list(self) -> list:
		return [self.version, self.modelname]
	def _validate(self, parentlist=None):
		# version: int, either 1 or 2
		assert isinstance(self.version, int)
		assert (self.version is 1) or (self.version is 2)
		# modelname: str
		assert isinstance(self.modelname, str)

class VmdBoneFrame(_BaseVmd):
	def __init__(self,
				 name: str,
				 f: int,
				 pos: List[float],
				 rot: List[float],
				 phys_off: bool,
				 interp_x: List[int]=None,
				 interp_y: List[int]=None,
				 interp_z: List[int]=None,
				 interp_r: List[int]=None,
				 ):
		self.name = name
		self.f = f
		self.pos = pos  # X Y Z
		self.rot = rot  # X Y Z euler angles in degrees
		self.phys_off = phys_off
		
		# all interpolation parameters are stored as (Ax, Ay, Bx, By)
		# point A is the bottom-left control point and point B is the top-right control point
		# Ax represents the x-location of A on a scale of 0 to 127, Ay represents the y-location, etc
		# if omitted, set to default linear interpolation values
		# the x-channel, y-channel, z-channel, and rotation channel are all stored independently
		# NOTE: interpolation data for is used when moving from teh PREVIOUS frame to THIS frame
		if interp_x is None: self.interp_x = core.interpolation_default_linear.copy()
		else:                self.interp_x = interp_x  # interpolation parameters for the X motion
		if interp_y is None: self.interp_y = core.interpolation_default_linear.copy()
		else:                self.interp_y = interp_y  # interpolation parameters for the Y motion
		if interp_z is None: self.interp_z = core.interpolation_default_linear.copy()
		else:                self.interp_z = interp_z  # interpolation parameters for the Z motion
		if interp_r is None: self.interp_r = core.interpolation_default_linear.copy()
		else:                self.interp_r = interp_r  # interpolation parameters for the rotation
	def list(self) -> list:
		return [self.name, self.f, *self.pos, *self.rot, self.phys_off, *self.interp_x, *self.interp_y, *self.interp_z, *self.interp_r]
	def _validate(self, parentlist=None):
		# name: str, at this level i don't care about the 15 byte limit
		assert isinstance(self.name, str)
		# f: int, frame number, cannot be negative
		assert isinstance(self.f, int)
		assert self.f >= 0
		# pos: X Y Z position vec3
		assert is_good_vector(3, self.pos)
		# rot: X Y Z rotation vec3, degrees
		assert is_good_vector(3, self.rot)
		# phys_off: bool flag
		assert is_good_flag(self.phys_off)
		# interp_x: list of 4 ints, each limited to range [0 - 127]
		assert isinstance(self.interp_x, (list,tuple))
		assert len(self.interp_x) == 4
		for a in self.interp_x:
			assert isinstance(a, int)
			assert 0 <= a <= 127
		# interp_y: list of 4 ints, each limited to range [0 - 127]
		assert isinstance(self.interp_y, (list,tuple))
		assert len(self.interp_y) == 4
		for a in self.interp_y:
			assert isinstance(a, int)
			assert 0 <= a <= 127
		# interp_z: list of 4 ints, each limited to range [0 - 127]
		assert isinstance(self.interp_z, (list,tuple))
		assert len(self.interp_z) == 4
		for a in self.interp_z:
			assert isinstance(a, int)
			assert 0 <= a <= 127
		# interp_r: list of 4 ints, each limited to range [0 - 127]
		assert isinstance(self.interp_r, (list,tuple))
		assert len(self.interp_r) == 4
		for a in self.interp_r:
			assert isinstance(a, int)
			assert 0 <= a <= 127


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
	def _validate(self, parentlist=None):
		# name: str, at this level i don't care about the 15 byte limit
		assert isinstance(self.name, str)
		# f: int, frame number, cannot be negative
		assert isinstance(self.f, int)
		assert self.f >= 0
		# val: the value of the morph, float, normally 0 to 1 but can technically be anything
		assert isinstance(self.val, (int,float))

class VmdCamFrame(_BaseVmd):
	def __init__(self,
				 f: int,
				 dist: float,
				 pos: List[float],
				 rot: List[float],
				 fov: int,
				 perspective: bool,
				 interp_x: List[int]=None,
				 interp_y: List[int]=None,
				 interp_z: List[int]=None,
				 interp_r: List[int]=None,
				 interp_dist: List[int]=None,
				 interp_fov: List[int]=None,
				 ):
		self.f = f
		self.pos = pos  # X Y Z float
		# NOTE: bone frames internally store rotation as quaternions, and therefore euler representation is always
		# as "reasonable" i.e. -180 to +180. but cam frames internally store rotation as EULER, meaning their values
		# can be "unreasonable" i.e. 700 degrees around the Y axis or whatever. be careful of this if doing math on
		# the cam frame rotations that requires going to quaternion-space and back!
		self.rot = rot  # X Y Z float euler angles in degrees
		self.dist = dist
		self.fov = fov  # int
		# perspective: if true, use perspective (normal), if false use orthagonal viewport?
		self.perspective = perspective
		
		# all interpolation parameters are stored as (Ax, Ay, Bx, By)
		# point A is the bottom-left control point and point B is the top-right control point
		# Ax represents the x-location of A on a scale of 0 to 127, Ay represents the y-location, etc
		# if omitted, set to default linear interpolation values
		# the x-channel, y-channel, z-channel, rotation channel, distance channel, and FOV channel are all stored independently
		# NOTE: interpolation data for is used when moving from teh PREVIOUS frame to THIS frame
		if interp_x is None: self.interp_x = core.interpolation_default_linear.copy()
		else:                self.interp_x = interp_x  # interpolation parameters for the X motion
		if interp_y is None: self.interp_y = core.interpolation_default_linear.copy()
		else:                self.interp_y = interp_y  # interpolation parameters for the Y motion
		if interp_z is None: self.interp_z = core.interpolation_default_linear.copy()
		else:                self.interp_z = interp_z  # interpolation parameters for the Z motion
		if interp_r is None: self.interp_r = core.interpolation_default_linear.copy()
		else:                self.interp_r = interp_r  # interpolation parameters for the rotation
		if interp_dist is None: self.interp_dist = core.interpolation_default_linear.copy()
		else:                self.interp_dist = interp_dist  # interpolation parameters for the distance to focal point
		if interp_fov is None: self.interp_fov = core.interpolation_default_linear.copy()
		else:                self.interp_fov = interp_fov  # interpolation parameters for the FOV slider

	def list(self) -> list:
		return [self.f, self.dist, *self.pos, *self.rot, self.fov, self.perspective,
				*self.interp_x, *self.interp_y, *self.interp_z, *self.interp_r, *self.interp_dist, *self.interp_fov]
	def _validate(self, parentlist=None):
		# f: int, frame number, cannot be negative
		assert isinstance(self.f, int)
		assert self.f >= 0
		# pos: X Y Z position vec3
		assert is_good_vector(3, self.pos)
		# rot: X Y Z rotation vec3, degrees
		assert is_good_vector(3, self.rot)
		# dist: float, distance from focus point to camera
		assert isinstance(self.dist, (int,float))
		# fov: field of view, degrees? must be an int
		assert isinstance(self.fov, int)
		# perspective: bool flag
		assert is_good_flag(self.perspective)
		# interp_x: list of 4 ints, each limited to range [0 - 127]
		assert isinstance(self.interp_x, (list,tuple))
		assert len(self.interp_x) == 4
		for a in self.interp_x:
			assert isinstance(a, int)
			assert 0 <= a <= 127
		# interp_y: list of 4 ints, each limited to range [0 - 127]
		assert isinstance(self.interp_y, (list,tuple))
		assert len(self.interp_y) == 4
		for a in self.interp_y:
			assert isinstance(a, int)
			assert 0 <= a <= 127
		# interp_z: list of 4 ints, each limited to range [0 - 127]
		assert isinstance(self.interp_z, (list,tuple))
		assert len(self.interp_z) == 4
		for a in self.interp_z:
			assert isinstance(a, int)
			assert 0 <= a <= 127
		# interp_r: list of 4 ints, each limited to range [0 - 127]
		assert isinstance(self.interp_r, (list,tuple))
		assert len(self.interp_r) == 4
		for a in self.interp_r:
			assert isinstance(a, int)
			assert 0 <= a <= 127
		# interp_dist: list of 4 ints, each limited to range [0 - 127]
		assert isinstance(self.interp_dist, (list,tuple))
		assert len(self.interp_dist) == 4
		for a in self.interp_dist:
			assert isinstance(a, int)
			assert 0 <= a <= 127
		# interp_fov: list of 4 ints, each limited to range [0 - 127]
		assert isinstance(self.interp_fov, (list,tuple))
		assert len(self.interp_fov) == 4
		for a in self.interp_fov:
			assert isinstance(a, int)
			assert 0 <= a <= 127


class VmdLightFrame(_BaseVmd):
	def __init__(self,
				 f: int,
				 color: List[float],
				 pos: List[float]
				 ):
		self.f = f
		self.color = color  # R G B float [0.0 - 1.0]
		self.pos = pos  # X Y Z
	def list(self) -> list:
		return [self.f, *self.color, *self.pos]
	def _validate(self, parentlist=None):
		# f: int, frame number, cannot be negative
		assert isinstance(self.f, int)
		assert self.f >= 0
		# pos: X Y Z position vec3. each value must be limited to -1.0 to 1.0
		assert is_good_vector(3, self.pos)
		for a in self.pos:
			assert -1.0 <= a <= 1.0
		# color: R G B list of 3 floats, each range [0.0 - 1.0]
		assert is_good_vector(3, self.color)
		for a in self.color:
			assert 0.0 <= a <= 1.0


class VmdShadowFrame(_BaseVmd):
	def __init__(self,
				 f: int,
				 mode: ShadowMode,
				 val: int
				 ):
		self.f = f
		# mode: see ShadowMode enum for more details (0=off, 1=mode1, 2=mode2)
		self.mode = mode
		# val: controls the shadow draw distance I think? int [0-9999]
		self.val = val
	def list(self) -> list:
		return [self.f, self.mode.value, self.val]
	def _validate(self, parentlist=None):
		# f: int, frame number, cannot be negative
		assert isinstance(self.f, int)
		assert self.f >= 0
		# mode: ShadowMode enum
		assert isinstance(self.mode, ShadowMode)
		# val: int [0 - 9999]
		assert isinstance(self.val, int)
		assert 0 <= self.val <= 9999


class VmdIkbone(_BaseVmd):
	def __init__(self,
				 name: str,
				 enable: bool
				 ):
		self.name = name
		self.enable = enable
	def list(self) -> list:
		return [self.name, self.enable]
	def _validate(self, parentlist=None):
		# name: string, don't care about the ?? byte cutoff at this level
		assert isinstance(self.name, str)
		# enable: bool flag
		assert is_good_flag(self.enable)


class VmdIkdispFrame(_BaseVmd):
	def __init__(self,
				 f: int,
				 disp: bool,
				 ikbones: List[VmdIkbone]
				 ):
		self.f = f
		# disp: is the model currently being rendered? bool flag
		self.disp = disp
		self.ikbones = ikbones
	def list(self) -> list:
		ret = [self.f, self.disp]
		for ik in self.ikbones:
			ret.extend(ik.list())
		return ret
	def _validate(self, parentlist=None):
		# f: int, frame number, cannot be negative
		assert isinstance(self.f, int)
		assert self.f >= 0
		# disp: bool flag
		assert is_good_flag(self.disp)
		# ikbones: list of some number of VmdIkBone objects
		assert isinstance(self.ikbones, (list,tuple))
		for a in self.ikbones:
			assert isinstance(a, VmdIkbone)
			assert a.validate(parentlist=self.ikbones)


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
	def _validate(self, parentlist=None):
		# header
		assert isinstance(self.header, VmdHeader)
		# boneframes
		assert isinstance(self.boneframes, (list,tuple))
		for a in self.boneframes:
			assert isinstance(a, VmdBoneFrame)
			assert a.validate(parentlist=self.boneframes)
		# morphframes
		assert isinstance(self.morphframes, (list,tuple))
		for a in self.morphframes:
			assert isinstance(a, VmdMorphFrame)
			assert a.validate(parentlist=self.morphframes)
		# camframes
		assert isinstance(self.camframes, (list,tuple))
		for a in self.camframes:
			assert isinstance(a, VmdCamFrame)
			assert a.validate(parentlist=self.camframes)
		# lightframes
		assert isinstance(self.lightframes, (list,tuple))
		for a in self.lightframes:
			assert isinstance(a, VmdLightFrame)
			assert a.validate(parentlist=self.lightframes)
		# shadowframes
		assert isinstance(self.shadowframes, (list,tuple))
		for a in self.shadowframes:
			assert isinstance(a, VmdShadowFrame)
			assert a.validate(parentlist=self.shadowframes)
		# ikdispframes
		assert isinstance(self.ikdispframes, (list,tuple))
		for a in self.ikdispframes:
			assert isinstance(a, VmdIkdispFrame)
			assert a.validate(parentlist=self.ikdispframes)
		pass

if __name__ == '__main__':
	print(_SCRIPT_VERSION)
	core.pause_and_quit("you are not supposed to directly run this file haha")


