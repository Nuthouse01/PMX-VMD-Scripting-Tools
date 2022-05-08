import abc
import copy
import enum
import sys
import traceback
from typing import List, Union, Set

import mmd_scripting.core.nuthouse01_core as core

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.02 - 7/30/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

__all__ = ['JointType', 'MaterialFlags', 'MorphPanel', 'MorphType', 'Pmx', 'PmxBone', 'PmxBoneIkLink', 'PmxFrame',
		   'PmxFrameItem', 'PmxHeader', 'PmxJoint', 'PmxMaterial', 'PmxMorph', 'PmxMorphItemBone', 'PmxMorphItemFlip',
		   'PmxMorphItemGroup', 'PmxMorphItemImpulse', 'PmxMorphItemMaterial', 'PmxMorphItemUV', 'PmxMorphItemVertex',
		   'PmxRigidBody', 'PmxSoftBody', 'PmxVertex', 'RigidBodyPhysMode', 'RigidBodyShape', 'SphMode', 'WeightMode']

############################################################################################
######## IMPORTANT NOTES ###################################################################
# pos = position = xyz
# there are NO quaternions in any of these structs, all angles are XYZ degrees
# all RGB or RGBA color stuff is floats [0.0-1.0] (below 0.0 or above 1.0 are both allowed tho, i just mean 0-255 == 0.0-1.0)
# the "list" members are just for viewing/debugging
# i STRONGLY suggest you use all keyword arguments when creating any of these objects, even if it makes things messy &
#    ugly it also makes them unambiguous and clear at a glance
# i also suggest you omit any "optional" or conditionally needed args that aren't relevant and let them default to
#    None instead of explicitly setting them to None
############################################################################################
############################################################################################


# this is an abstract base class that all the PMX classes inherit
# this lets them all get the __str__ method and forces them all to implement list()
# it also lets me detect any of them by isinstance(x, _BasePmx)
# this also defines an "==" method so my structs can be compared
# this also defines "idx_within" so if you forget the idx of a thing but still have its reference you can find its index again
class _BasePmx(abc.ABC):
	def copy(self):
		""" Return a separate copy of the object. """
		return copy.deepcopy(self)
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
			core.MY_PRINT_FUNC('VALIDATE ERROR: Object "{}" failed validation check "{}" at line "{}" in nuthouse01_pmx_struct.py'.format(
				self.__class__.__name__, lowesttrace.line, lowesttrace.lineno
			))
			core.MY_PRINT_FUNC("This happens when the PMX/VMD object has incorrect data sizes/types.")
			core.MY_PRINT_FUNC("Figure out why/how bad data got into this field, then stop it from happening in the future!")
			
			# determine "which index this is within the whole object" if possible???
			if parentlist is not None:
				idx = self.idx_within(parentlist)
				if idx is not None:
					core.MY_PRINT_FUNC('Object {} found at index {} of containing list'.format(self.__class__.__name__, idx))
			raise RuntimeError("validation fail") from e3
		except RuntimeError:
			# if there is a runtime error, only do the "determine which index this is" part
			# determine "which index this is within the whole object" if possible???
			if parentlist is not None:
				idx = self.idx_within(parentlist)
				if idx is not None:
					core.MY_PRINT_FUNC('Object {} found at index {} of containing list'.format(self.__class__.__name__, idx))
			# raise with no arg to re-raise the same exception
			raise

	def __str__(self) -> str: return str(self.list())
	def __eq__(self, other) -> bool:
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


class _BasePmxMorphItem(_BasePmx):
	@abc.abstractmethod
	def list(self) -> list: pass


class WeightMode(enum.Enum):
	# 0 = BDEF1 = [b1]
	# 1 = BDEF2 = [b1, b2, b1w]
	# 2 = BDEF4 = [b1, b2, b3, b4, b1w, b2w, b3w, b4w]
	# 3 = sdef =  [b1, b2, b1w]
	# weight_sdef = [[c1, c2, c3], [r01, r02, r03], [r11, r12, r13]]
	# 4 = qdef =  [b1, b2, b3, b4, b1w, b2w, b3w, b4w]
	BDEF1 = 0
	BDEF2 = 1
	BDEF4 = 2
	SDEF =  3
	QDEF =  4  # (only in pmx v2.1)
class SphMode(enum.Enum):
	# 0 = disabled, 1 = multiply, 2 = additive, 3 = additional vec4*
	DISABLE =  0
	MULTIPLY = 1
	ADDITIVE = 2
	# "* Environment blend mode 3 will use the first additional vec4 to map the environment texture,
	# using just the X and Y values as the texture UV. It is mapped as an additional texture layer.
	# This may conflict with other uses for the first additional vec4."
	# I think this is the mode used for normal map usage?
	SUBTEX = 3
class MorphPanel(enum.Enum):
	# this controls wich "category" a morph goes into!
	@classmethod
	def _missing_(cls, value):
		# when trying to get the enum from value, if the value isnt [0 - 4] then return 0 instead of crashing!
		return MorphPanel(0)
	# Value 	Group 		Panel in MMD
	# 0 		Hidden 		None
	# 1 		Eyebrows 	Bottom left
	# 2 		Eyes 		Top left
	# 3 		Mouth 		Top right
	# 4 		Other 		Bottom right
	HIDDEN =      0
	BROW =        1
	EYE =         2
	MOUTH =       3
	OTHER =       4
	# # let's toss in some aliases cuz why not
	# NONE =        0
	# BOTTOMLEFT =  1
	# TOPLEFT =     2
	# TOPRIGHT =    3
	# BOTTOMRIGHT = 4
class MorphType(enum.Enum):
	# morphtype
	# 0 = group = (morph_idx, influence)
	# 1 = vertex = (vert_idx, transX, transY, transZ)
	# 2 = bone = (bone_idx, transX, transY, transZ, rotX, rotY, rotZ, rotW)
	# 3/4/5/6/7 = uv = (vert_idx, A, B, C, D)
	# 8 = material =
	# (mat_idx, is_add, diffR, diffG, diffB, diffA, specR, specG, specB) = core.unpack(IDX_MAT+"b 4f 3f", raw)
	# (specpower, ambR, ambG, ambB, edgeR, edgeG, edgeB, edgeA, edgesize) = core.unpack("f 3f 4f f", raw)
	# (texR, texG, texB, texA, sphR, sphG, sphB, sphA, toonR, toonG, toonB, toonA) = core.unpack("4f 4f 4f", raw)
	# 9 = flip = (morph_idx, influence)  (pmx v2.1 only)
	# 10 = impulse = (rb_idx, is_local, movX, movY, movZ, rotX, rotY, rotZ)   (pmx v2.1 only)
	GROUP =    0
	VERTEX =   1
	BONE =     2
	UV =       3
	# note: UV_EXT1 thru UV_EXT4 follow a similar idea to UV morphs, but they modify the "addl_vec4" items instead of
	# modifying the UV coordinates when used in a model. I've never seen a model that usefully uses them tho.
	UV_EXT1 =  4
	UV_EXT2 =  5
	UV_EXT3 =  6
	UV_EXT4 =  7
	MATERIAL = 8
	FLIP =     9  # (only in pmx v2.1)
	IMPULSE =  10  # (only in pmx v2.1)
class RigidBodyShape(enum.Enum):
	# shape: 0=sphere, 1=box, 2=capsule
	SPHERE =  0
	BOX =     1
	CAPSULE = 2
class RigidBodyPhysMode(enum.Enum):
	# phys_mode: 0=follow bone, 1=physics, 2=physics rotate only (pivot on bone)
	BONE =               0
	PHYSICS =            1
	PHYSICS_ROTATEONLY = 2
class JointType(enum.Enum):
	# jointtype: 0=spring6DOF, all others are v2.1 only!!!! 1=6dof, 2=p2p, 3=conetwist, 4=slider, 5=hinge
	SPRING_SIXDOF = 0
	SIXDOF =        1  # (only in pmx v2.1)
	P2P =           2  # (only in pmx v2.1)
	CONETWIST =     3  # (only in pmx v2.1)
	SLIDER =        4  # (only in pmx v2.1)
	HINGE =         5  # (only in pmx v2.1)
class MaterialFlags(enum.Flag):
	DOUBLE_SIDED =       (1 << 0)
	CAST_GROUND_SHADOW = (1 << 1)
	CAST_SHADOW =        (1 << 2)
	RECEIVE_SHADOW =     (1 << 3)
	USE_EDGING =         (1 << 4)
	USE_VERTEX_COLOR =   (1 << 5)  # (only in pmx v2.1)
	DRAW_AS_POINTS =     (1 << 6)  # (only in pmx v2.1)
	DRAW_AS_LINES =      (1 << 7)  # (only in pmx v2.1)
	# def includes(self, f: 'MaterialFlags') -> bool:
	# 	"""
	# 	This is a synonym for "f in this"
	# 	"""
	# 	return f in self
	def add(self, f: 'MaterialFlags') -> 'MaterialFlags':
		"""
		Return a new flags object with the new flag added into it. DOES NOT MODIFY THE ORIGINAL.
		You need to use "m = m.add(thing)" or just use "m = m | thing"
		:param f: a MaterialFlags item
		:return: this, but with f added to it
		"""
		s = self | f
		return s
	def remove(self, f: 'MaterialFlags') -> 'MaterialFlags':
		"""
		Return a new flags object with the flag deleted from it. DOES NOT MODIFY THE ORIGINAL.
		You need to use "m = m.remove(thing)" or just use "m = m & ~thing"
		:param f: a MaterialFlags item
		:return: this, but with f removed from it
		"""
		s = self & ~f
		return s
	
	
class PmxHeader(_BasePmx):
	# [ver, name_jp, name_en, comment_jp, comment_en]
	def __init__(self, 
				 ver: float, 
				 name_jp: str,
				 name_en: str,
				 comment_jp: str,
				 comment_en: str):
		self.ver = ver
		self.name_jp = name_jp
		self.name_en = name_en
		self.comment_jp = comment_jp
		self.comment_en = comment_en
	def list(self):
		return [self.ver, self.name_jp, self.name_en, self.comment_jp, self.comment_en]
	def _validate(self, parentlist=None):
		""" This performs type-checking and input validation on the item, as a way to protect against bad code
		assigning invalid values or incorrect datatypes into my structures. If it fails it will raise an Exception
		of some kind and probably print a stack trace I guess?"""
		# ver: should always be either 2 or 2.1
		assert (self.ver == 2.0) or (self.ver == 2.1)
		# name_jp, name_en, comment_jp, comment_en: all strings
		assert isinstance(self.name_jp, str)
		assert isinstance(self.name_en, str)
		assert isinstance(self.comment_jp, str)
		assert isinstance(self.comment_en, str)

class PmxVertex(_BasePmx):
	# note: this block is the order of args in the old system, does not represent order of args in .list() member
	# [posX, posY, posZ, normX, normY, normZ, u, v, addl_vec4s, weighttype, weights, edgescale]
	def __init__(self,
				 pos: List[float],
				 norm: List[float],
				 uv: List[float],
				 edgescale: float,
				 weighttype: WeightMode,
				 weight: List[List[float]],
				 # optional/conditional
				 weight_sdef: List[List[float]]=None,
				 addl_vec4s: List[List[float]]=None,
				 ):
		self.pos = pos
		self.norm = norm
		self.uv = uv
		self.edgescale = edgescale
		# weighttype: see WeightMode for more info
		self.weighttype = weighttype
		# weight: this is an ordered list of boneidx-weight pairs
		# the list can be 1 to 4 pairs depending on weighttype
		self.weight = weight
		# weight_sdef = [[c1, c2, c3], [r01, r02, r03], [r11, r12, r13]]
		# this is used/valid if and only if weighttype is SDEF
		self.weight_sdef = weight_sdef
		self.addl_vec4s = addl_vec4s
	def list(self) -> list:
		return [self.pos, self.norm, self.uv, self.edgescale,
				self.weighttype, self.weight, self.weight_sdef, self.addl_vec4s]
	def _validate(self, parentlist=None):
		""" This performs type-checking and input validation on the item, as a way to protect against bad code
		assigning invalid values or incorrect datatypes into my structures. If it fails it will raise an Exception
		of some kind and probably print a stack trace I guess?"""
		# pos: XYZ position of object, list (or tuple) of 3 floats
		assert is_good_vector(3, self.pos)
		# norm: XYZ normal vector, list (or tuple) of 3 floats
		assert is_good_vector(3, self.norm)
		# uv: UV coordinates, list (or tuple) of 2 floats
		# should usually be [0.0 - 1.0] but i'm not gonna strictly enforce that
		assert is_good_vector(2, self.uv)
		# edgescale: single float
		assert isinstance(self.edgescale, (int,float))
		# weighttype: WeightMode enum, if attempting to create from an invalid number then the enum will raise an error
		assert isinstance(self.weighttype, WeightMode)
		# weight_sdef: extra parameters only used in SDEF mode, so only check when in SDEF mode
		if self.weighttype == WeightMode.SDEF:
			# format is 3 lists of 3 floats
			# [[c1, c2, c3], [r01, r02, r03], [r11, r12, r13]]
			assert isinstance(self.weight_sdef, (list,tuple))
			assert len(self.weight_sdef) == 3
			for rc in self.weight_sdef:
				assert is_good_vector(3, rc)
		# weight: this is an ordered list of boneidx-weight pairs
		# the list can be 1 to 4 pairs depending on weighttype, when written it will be padded out to fill as needed
		assert isinstance(self.weight, (list,tuple))
		assert 1 <= len(self.weight) <= 4
		for pair in self.weight:
			assert isinstance(pair, (list,tuple))
			assert len(pair) == 2
			# the boneidx MUST be a nonnegative int but i'm not gonna enforce that
			assert isinstance(pair[0], int)
			# assert pair[0] >= 0
			# the weight can be any float, should be [0.0 - 1.0] but i'm not gonna enforce that
			assert isinstance(pair[1], (int,float))
		# addl_vec4: an unknown number of vec4s. most models have none.
		if self.addl_vec4s is not None:
			assert isinstance(self.addl_vec4s, (list,tuple))
			for vec4 in self.addl_vec4s:
				assert is_good_vector(4, vec4)

# face is just a list of ints, no struct needed

# tex is just a string, no struct needed

class PmxMaterial(_BasePmx):
	def __init__(self, name_jp: str, name_en: str, diffRGB: List[float], specRGB: List[float], ambRGB: List[float],
				 alpha: float, specpower: float, edgeRGB: List[float], edgealpha: float, edgesize: float, tex_path: str,
				 toon_path: str, sph_path: str, sph_mode: SphMode, comment: str, faces_ct: int,
				 matflags: MaterialFlags):
		self.name_jp = name_jp
		self.name_en = name_en
		self.diffRGB = diffRGB
		self.specRGB = specRGB
		self.ambRGB = ambRGB
		self.alpha = alpha
		self.specpower = specpower
		self.edgeRGB = edgeRGB
		self.edgealpha = edgealpha
		self.edgesize = edgesize
		self.tex_path = tex_path
		self.toon_path = toon_path
		self.sph_path = sph_path
		# sph_mode: see SphMode definition
		self.sph_mode = sph_mode
		self.comment = comment
		self.faces_ct = faces_ct
		# flaglist: see MaterialFlags definition
		self.matflags = matflags
	def list(self) -> list:
		return [self.name_jp, self.name_en, self.diffRGB, self.specRGB, self.ambRGB, self.alpha, self.specpower,
				self.edgeRGB, self.edgealpha, self.edgesize,
				self.tex_path, self.toon_path, self.sph_path, self.sph_mode,
				self.comment, self.faces_ct, self.matflags,
				]
	def _validate(self, parentlist=None):
		""" This performs type-checking and input validation on the item, as a way to protect against bad code
		assigning invalid values or incorrect datatypes into my structures. If it fails it will raise an Exception
		of some kind and probably print a stack trace I guess?"""
		# name_jp, name_en: strings
		assert isinstance(self.name_jp, str)
		assert isinstance(self.name_en, str)
		# diffRGB: diffuse RGB color, list of 3 floats
		assert is_good_vector(3, self.diffRGB)
		# specRGB: specular RGB color, list of 3 floats
		assert is_good_vector(3, self.specRGB)
		# ambRGB: ambient RGB color, list of 3 floats
		assert is_good_vector(3, self.ambRGB)
		# alpha: single float, alpha or opacity
		assert isinstance(self.alpha, (int,float))
		# specpower: specular exponent, "shininess", normally positive but not gonna strictly enforce that
		assert isinstance(self.specpower, (int,float))
		# edgeRGB: edge RGB color, list of 3 floats
		assert is_good_vector(3, self.edgeRGB)
		# edgealpha: single float, alpha or opacity for the edging
		assert isinstance(self.edgealpha, (int,float))
		# edgesize: thickness of edging effect
		assert isinstance(self.edgesize, (int,float))
		# tex_idx: str filepath to texture
		assert isinstance(self.tex_path, str)
		# sph_idx: str filepath to SPH
		assert isinstance(self.sph_path, str)
		# toon_idx: str filepath to toon
		assert isinstance(self.toon_path, str)
		# sph_mode: SphMode enum
		assert isinstance(self.sph_mode, SphMode)
		# comment: comment
		assert isinstance(self.comment, str)
		# faces_ct: int, MUST be nonnegative
		assert isinstance(self.faces_ct, int)
		assert self.faces_ct >= 0
		# matflags: MaterialFlags enum
		assert isinstance(self.matflags, MaterialFlags)

class PmxBoneIkLink(_BasePmx):
	# NOTE: to represent "no limits", the min and max should be None or omitted
	def __init__(self,
				 idx: int,
				 # optional/conditional
				 limit_min: List[float]=None,
				 limit_max: List[float]=None,
				 ):
		self.idx = idx
		# list of limits in degrees, or none
		self.limit_min = limit_min
		# list of limits in degrees, or none
		self.limit_max = limit_max
	def list(self) -> list:
		return [self.idx, self.limit_min, self.limit_max]
	def _validate(self, parentlist=None):
		""" This performs type-checking and input validation on the item, as a way to protect against bad code
		assigning invalid values or incorrect datatypes into my structures. If it fails it will raise an Exception
		of some kind and probably print a stack trace I guess?"""
		# idx: bone index, must be int
		assert isinstance(self.idx, int)
		# limit_min, limit_max: either both are None or both are good vec3
		# if not None, realistic values would be -360 to +360 but i wont enforce that
		assert (self.limit_min is None and self.limit_max is None) \
			   or (is_good_vector(3, self.limit_min) and is_good_vector(3, self.limit_max))

class PmxBone(_BasePmx):
	# note: this block is the order of args in the old system, does not represent order of args in .list() member
	# thisbone = [name_jp, name_en, posX, posY, posZ, parent_idx, deform_layer, deform_after_phys,  # 0-7
	# 			rotateable, translateable, visible, enabled,  # 8-11
	# 			tail_usebonelink, maybe_tail, inherit_rot, inherit_trans, maybe_inherit, fixed_axis, maybe_fixed_axis,  # 12-18
	# 			local_axis, maybe_local_axis, external_parent, maybe_external_parent, ik, maybe_ik]  # 19-24
	def __init__(self,
				 name_jp: str, name_en: str,
				 pos: List[float],
				 parent_idx: int,
				 deform_layer: int,
				 deform_after_phys: bool,
				 has_rotate: bool,
				 has_translate: bool,
				 has_visible: bool,
				 has_enabled: bool,
				 has_ik: bool,
				 tail_usebonelink: bool,
				 tail: Union[int, List[float]],  # NOTE: either int or list of 3 float, but always exists, never None
				 inherit_rot: bool,
				 inherit_trans: bool,
				 has_fixedaxis: bool,
				 has_localaxis: bool,
				 has_externalparent: bool,
				 # optional/conditional
				 inherit_parent_idx: int=None,
				 inherit_ratio: float=None,
				 fixedaxis: List[float]=None,
				 localaxis_x: List[float]=None,
				 localaxis_z: List[float]=None,
				 externalparent: int=None,
				 ik_target_idx: int=None,
				 ik_numloops: int=None,
				 ik_angle: float=None,
				 ik_links: List[PmxBoneIkLink]=None,
				 ):
		self.name_jp = name_jp
		self.name_en = name_en
		self.pos = pos
		self.parent_idx = parent_idx
		self.deform_layer = deform_layer
		self.deform_after_phys = deform_after_phys
		self.has_rotate = has_rotate
		self.has_translate = has_translate
		self.has_visible = has_visible
		self.has_enabled = has_enabled
		
		# tail_usebonelink: true = point-at mode, false = offset mode
		self.tail_usebonelink = tail_usebonelink
		self.tail = tail  # if tail_usebonelink = true, this is [x y z]. otherwise, this is int.
		
		self.inherit_rot = inherit_rot
		self.inherit_trans = inherit_trans
		self.inherit_parent_idx = inherit_parent_idx
		self.inherit_ratio = inherit_ratio
		
		self.has_fixedaxis = has_fixedaxis
		self.fixedaxis = fixedaxis
		
		self.has_localaxis = has_localaxis
		self.localaxis_x = localaxis_x
		self.localaxis_z = localaxis_z
		
		self.has_externalparent = has_externalparent
		self.externalparent = externalparent
		
		self.has_ik = has_ik
		self.ik_target_idx = ik_target_idx
		self.ik_numloops = ik_numloops
		self.ik_angle = ik_angle
		self.ik_links = ik_links
		
	def list(self) -> list:
		return [self.name_jp, self.name_en, self.pos, self.parent_idx, self.deform_layer, self.deform_after_phys,
				self.has_rotate, self.has_translate, self.has_visible, self.has_enabled,
				self.tail_usebonelink, self.tail,
				self.inherit_rot, self.inherit_trans, self.inherit_parent_idx, self.inherit_ratio,
				self.has_fixedaxis, self.fixedaxis,
				self.has_localaxis, self.localaxis_x, self.localaxis_z,
				self.has_externalparent, self.externalparent,
				self.has_ik, self.ik_target_idx, self.ik_numloops, self.ik_angle,
				None if self.ik_links is None else [i.list() for i in self.ik_links],
				]
	def _validate(self, parentlist=None):
		""" This performs type-checking and input validation on the item, as a way to protect against bad code
		assigning invalid values or incorrect datatypes into my structures. If it fails it will raise an Exception
		of some kind and probably print a stack trace I guess?"""
		# name_jp, name_en: strings
		assert isinstance(self.name_jp, str)
		assert isinstance(self.name_en, str)
		# pos: XYZ position of object, list (or tuple) of 3 floats
		assert is_good_vector(3, self.pos)
		# parent_idx: int reference to another bone
		assert isinstance(self.parent_idx, int)
		# deform_layer: int, should always be nonnegative but i won't enforce that
		assert isinstance(self.deform_layer, int)
		# deform_after_phys: bool flag
		assert is_good_flag(self.deform_after_phys)
		# has_rotate: bool flag
		assert is_good_flag(self.has_rotate)
		# has_translate: bool flag
		assert is_good_flag(self.has_translate)
		# has_visible: bool flag
		assert is_good_flag(self.has_visible)
		# has_enabled: bool flag
		assert is_good_flag(self.has_enabled)
		# tail_usebonelink: bool flag
		assert is_good_flag(self.tail_usebonelink)
		# tail: if use_bonelink == 1, it's a refernce to a bone, so must be int
		# if use_bonelink == 0, it's a vec3 offset
		if self.tail_usebonelink:
			assert isinstance(self.tail, int)
		else:
			assert is_good_vector(3, self.tail)
		# inherit_rot, inherit_trans: bool flag
		assert is_good_flag(self.inherit_rot)
		assert is_good_flag(self.inherit_trans)
		if self.inherit_rot or self.inherit_trans:
			# inherit_parent_idx, inherit_ratio: only matter if either inherit_rot or inherit_trans are enabled!
			# inherit_parent_idx: reference to a bone, so must be int
			assert isinstance(self.inherit_parent_idx, int)
			# inherit_ratio: float
			assert isinstance(self.inherit_ratio, (int,float))
		# has_fixedaxis: bool flag
		assert is_good_flag(self.has_fixedaxis)
		if self.has_fixedaxis:
			# fixedaxis: vec3 indicates the direction of the axis it is constrained to
			assert is_good_vector(3, self.fixedaxis)
		# has_localaxis: bool flag
		assert is_good_flag(self.has_localaxis)
		if self.has_localaxis:
			# localaxis_x: vec3 indicates the direction of X axis in new coordinate system
			assert is_good_vector(3, self.localaxis_x)
			# localaxis_z: vec3 indicates the direction of Z axis in new coordinate system
			assert is_good_vector(3, self.localaxis_z)
		# has_externalparent: bool flag
		assert is_good_flag(self.has_externalparent)
		if self.has_externalparent:
			# externalparent: int, normally nonnegative, but idk how this is actually used
			assert isinstance(self.externalparent, int)
		# has_ik: bool flag
		assert is_good_flag(self.has_ik)
		if self.has_ik:
			# ik_target_idx: bone index
			assert isinstance(self.ik_target_idx, int)
			# ik_numloops: int
			assert isinstance(self.ik_numloops, int)
			# ik_angle: float, degrees
			assert isinstance(self.ik_angle, (int,float))
			# ik_links: any-length list of PmxBoneIkLink objects
			assert isinstance(self.ik_links, (list,tuple))
			for a in self.ik_links:
				assert isinstance(a, PmxBoneIkLink)
				# call the validate member of this sub-object
				assert a.validate(parentlist=self.ik_links)


class PmxMorphItemGroup(_BasePmxMorphItem):
	def __init__(self, morph_idx: int, value: float):
		self.morph_idx = morph_idx
		self.value = value
	def list(self) -> list:
		return [self.morph_idx, self.value]
	def _validate(self, parentlist=None):
		# morph_idx: must be int
		assert isinstance(self.morph_idx, int)
		# value: must be float
		assert isinstance(self.value, (int,float))

class PmxMorphItemVertex(_BasePmxMorphItem):
	def __init__(self, vert_idx: int, move: List[float]):
		self.vert_idx = vert_idx
		self.move = move
	def list(self) -> list:
		return [self.vert_idx, self.move]
	def _validate(self, parentlist=None):
		# vert_idx: must be int
		assert isinstance(self.vert_idx, int)
		# move: must be vec3
		assert is_good_vector(3, self.move)

class PmxMorphItemBone(_BasePmxMorphItem):
	def __init__(self, bone_idx: int, move: List[float], rot: List[float]):
		self.bone_idx = bone_idx
		self.move = move
		self.rot = rot
	def list(self) -> list:
		return [self.bone_idx, self.move, self.rot]
	def _validate(self, parentlist=None):
		# bone_idx: must be int
		assert isinstance(self.bone_idx, int)
		# move: must be vec3
		assert is_good_vector(3, self.move)
		# rot: must be vec3
		assert is_good_vector(3, self.rot)


class PmxMorphItemUV(_BasePmxMorphItem):
	def __init__(self, vert_idx: int, move: List[float]):
		self.vert_idx = vert_idx
		self.move = move
	def list(self) -> list:
		return [self.vert_idx, self.move]
	def _validate(self, parentlist=None):
		# vert_idx: must be int
		assert isinstance(self.vert_idx, int)
		# move: must be vec4
		# NOTE: for a "normal" uv morph the last 2 elements are zeros
		# TODO: make separate logic for "normal" uv?
		assert is_good_vector(4, self.move)


class PmxMorphItemMaterial(_BasePmxMorphItem):
	def __init__(self, mat_idx: int, is_add: int,
				 diffRGB: List[float],
				 specRGB: List[float],
				 ambRGB: List[float],
				 alpha: float,
				 specpower: float,
				 edgeRGB: List[float],
				 edgealpha: float,
				 edgesize: float,
				 texRGBA: List[float],
				 sphRGBA: List[float],
				 toonRGBA: List[float],
				 ):
		self.mat_idx = mat_idx
		# is_add: if true, this is "additive" mode, if false, this is "multiply" mode
		self.is_add = is_add
		self.diffRGB = diffRGB
		self.specRGB = specRGB
		self.ambRGB = ambRGB
		self.alpha = alpha
		self.specpower = specpower
		self.edgeRGB = edgeRGB
		self.edgealpha = edgealpha
		self.edgesize = edgesize
		self.texRGBA = texRGBA
		self.sphRGBA = sphRGBA
		self.toonRGBA = toonRGBA
		# note: this order of args matches the current .list() order, except that it's grouped into sublists
		# (mat_idx, is_add, diffR, diffG, diffB, diffA, specR, specG, specB) = core.unpack(IDX_MAT+"b 4f 3f", raw)
		# (specpower, ambR, ambG, ambB, edgeR, edgeG, edgeB, edgeA, edgesize) = core.unpack("f 3f 4f f", raw)
		# (texR, texG, texB, texA, sphR, sphG, sphB, sphA, toonR, toonG, toonB, toonA) = core.unpack("4f 4f 4f", raw)
	def list(self) -> list:
		return [self.mat_idx, self.is_add,
				self.diffRGB, self.specRGB, self.ambRGB, self.alpha, self.specpower,
				self.edgeRGB, self.edgealpha, self.edgesize,
				self.texRGBA, self.sphRGBA, self.toonRGBA,
				]
	def _validate(self, parentlist=None):
		# mat_idx: must be int
		assert isinstance(self.mat_idx, int)
		# is_add: bool flag
		assert is_good_flag(self.is_add)
		# diffRGB: diffuse RGB color, list of 3 floats
		assert is_good_vector(3, self.diffRGB)
		# specRGB: specular RGB color, list of 3 floats
		assert is_good_vector(3, self.specRGB)
		# ambRGB: ambient RGB color, list of 3 floats
		assert is_good_vector(3, self.ambRGB)
		# alpha: single float, alpha or opacity
		assert isinstance(self.alpha, (int,float))
		# specpower: specular exponent, "shininess", normally positive
		assert isinstance(self.specpower, (int,float))
		# edgeRGB: edge RGB color, list of 3 floats
		assert is_good_vector(3, self.edgeRGB)
		# edgealpha: single float, alpha or opacity for the edging
		assert isinstance(self.edgealpha, (int,float))
		# edgesize: thickness of edging effect
		assert isinstance(self.edgesize, (int,float))
		# texRGBA: vec4 that modifies the texture
		assert is_good_vector(4, self.texRGBA)
		# sphRGBA: vec4 that modifies the SPH
		assert is_good_vector(4, self.sphRGBA)
		# toonRGBA: vec4 that modifies the toon
		assert is_good_vector(4, self.toonRGBA)


class PmxMorphItemFlip(_BasePmxMorphItem):
	def __init__(self, morph_idx: int, value: float):
		self.morph_idx = morph_idx
		self.value = value
	def list(self) -> list:
		return [self.morph_idx, self.value]
	def _validate(self, parentlist=None):
		# morph_idx: must be int
		assert isinstance(self.morph_idx, int)
		# value: must be float
		assert isinstance(self.value, (int,float))


class PmxMorphItemImpulse(_BasePmxMorphItem):
	def __init__(self, rb_idx: int, is_local: bool, move: List[float], rot: List[float]):
		self.rb_idx = rb_idx
		self.is_local = is_local
		self.move = move
		self.rot = rot
	def list(self) -> list:
		return [self.rb_idx, self.is_local, self.move, self.rot]
	def _validate(self, parentlist=None):
		# rb_idx: must be int
		assert isinstance(self.rb_idx, int)
		# is_local: bool flag I think? never used this one
		assert is_good_flag(self.is_local)
		# move: must be vec3
		assert is_good_vector(3, self.move)
		# rot: must be vec3
		assert is_good_vector(3, self.rot)


class PmxMorph(_BasePmx):
	# thismorph = [name_jp, name_en, panel, morphtype, these_items]
	def __init__(self,
				 name_jp: str, name_en: str,
				 panel: MorphPanel,
				 morphtype: MorphType,
				 items: List[_BasePmxMorphItem],
				 ):
		self.name_jp = name_jp
		self.name_en = name_en
		# panel: see MorphPanel enum definition for more info
		self.panel = panel
		# morphtype: see MorphType enum definition for more info
		self.morphtype = morphtype
		self.items = items
	def list(self) -> list:
		return [self.name_jp, self.name_en, self.panel, self.morphtype,
				[i.list() for i in self.items],
				]
	def _validate(self, parentlist=None):
		""" This performs type-checking and input validation on the item, as a way to protect against bad code
		assigning invalid values or incorrect datatypes into my structures. If it fails it will raise an Exception
		of some kind and probably print a stack trace I guess?"""
		# name_jp, name_en: strings
		assert isinstance(self.name_jp, str)
		assert isinstance(self.name_en, str)
		# panel: MorphPanel enum
		assert isinstance(self.panel, MorphPanel)
		# morphtype: MorphType enum
		assert isinstance(self.morphtype, MorphType)
		# items: list of "pmx morph item" objects, specific to the morphtype
		assert isinstance(self.items, (list,tuple))
		# validate that it is the RIGHT KIND of member, that corresponds to the self.morphtype value!
		DICT_MORPHTYPE_T0_CLASS = {
			MorphType.VERTEX:   PmxMorphItemVertex,
			MorphType.GROUP:    PmxMorphItemGroup,
			MorphType.BONE:     PmxMorphItemBone,
			MorphType.UV:       PmxMorphItemUV,
			MorphType.UV_EXT1:  PmxMorphItemUV,
			MorphType.UV_EXT2:  PmxMorphItemUV,
			MorphType.UV_EXT3:  PmxMorphItemUV,
			MorphType.UV_EXT4:  PmxMorphItemUV,
			MorphType.MATERIAL: PmxMorphItemMaterial,
			MorphType.FLIP:     PmxMorphItemFlip,
			MorphType.IMPULSE:  PmxMorphItemImpulse,
		}
		expected_item_class = DICT_MORPHTYPE_T0_CLASS[self.morphtype]
		for a in self.items:
			assert isinstance(a, (expected_item_class,))
			a : _BasePmxMorphItem  # will this make pycharm shut up?
			assert a.validate(parentlist=self.items)

class PmxFrameItem(_BasePmx):
	def __init__(self, is_morph: bool, idx: int):
		# is_morph: if true, this index references a morph. if false, this index references a bone.
		self.is_morph = is_morph
		# idx: int, references a bone or a morph.
		self.idx = idx
	def list(self) -> list:
		return [self.is_morph, self.idx]
	def _validate(self, parentlist=None):
		# is_morph: bool flag
		assert is_good_flag(self.is_morph)
		# idx: reference to a bone or morph
		assert isinstance(self.idx, int)


class PmxFrame(_BasePmx):
	# thisframe = [name_jp, name_en, is_special, these_items]
	def __init__(self, 
				 name_jp: str, name_en: str, 
				 is_special: bool, 
				 items: List[PmxFrameItem],
				 ):
		self.name_jp = name_jp
		self.name_en = name_en
		# "special" frames are "root" and "facials". exactly those 2 should be marked as special, no more no less.
		# if special, name/position cannot be edited in PMXE, but they're otherwise ordinary frames.
		self.is_special = is_special
		# "items" is a list of PmxFrameItem objects
		self.items = items
	def list(self) -> list:
		return [self.name_jp, self.name_en, self.is_special, [a.list() for a in self.items]]
	def _validate(self, parentlist=None):
		""" This performs type-checking and input validation on the item, as a way to protect against bad code
		assigning invalid values or incorrect datatypes into my structures. If it fails it will raise an Exception
		of some kind and probably print a stack trace I guess?"""
		# name_jp, name_en: strings
		assert isinstance(self.name_jp, str)
		assert isinstance(self.name_en, str)
		# is_special: bool flag
		assert is_good_flag(self.is_special)
		# items: call validate member of each thing in the list
		assert isinstance(self.items, (list,tuple))
		for a in self.items:
			assert isinstance(a, PmxFrameItem)
			assert a.validate(parentlist=self.items)

class PmxRigidBody(_BasePmx):
	# note: this block is the order of args in the old system, does not represent order of args in .list() member
	# thisbody = [name_jp, name_en, bone_idx, group, nocollide_mask, shape, sizeX, sizeY, sizeZ, posX, posY, posZ,
	# 			rotX, rotY, rotZ, mass, move_damp, rot_damp, repel, friction, physmode]
	def __init__(self, name_jp: str, name_en: str, bone_idx: int, pos: List[float], rot: List[float], size: List[float],
				 shape: RigidBodyShape, group: int, nocollide_set: Set[int], phys_mode: RigidBodyPhysMode,
				 phys_mass: float = 1.0, phys_move_damp: float = 0.5, phys_rot_damp: float = 0.5,
				 phys_repel: float = 0.0, phys_friction: float = 0.5):
		self.name_jp = name_jp
		self.name_en = name_en
		self.bone_idx = bone_idx
		self.pos = pos
		self.rot = rot
		# todo: explain what size means for each shape type, its always 3 floats but they're used for different things
		self.size = size
		# shape: see RigidBodyShape for more info
		self.shape = shape
		# group is int [1-16], same way its shown in PMXE
		self.group = group
		# nocollide_set is a SET containing ints [1-16], same as shown in PMXE
		self.nocollide_set = nocollide_set
		# phys_mode: see RigidBodyPhysMode for more info
		self.phys_mode = phys_mode
		self.phys_mass = phys_mass
		self.phys_move_damp = phys_move_damp
		self.phys_rot_damp = phys_rot_damp
		self.phys_repel = phys_repel
		self.phys_friction = phys_friction
	def list(self) -> list:
		return [self.name_jp, self.name_en, self.bone_idx,
				self.pos, self.rot, self.size, self.shape,
				self.group, sorted(list(self.nocollide_set)), self.phys_mode,
				self.phys_mass, self.phys_move_damp, self.phys_rot_damp, self.phys_repel, self.phys_friction,
				]
	def _validate(self, parentlist=None):
		""" This performs type-checking and input validation on the item, as a way to protect against bad code
		assigning invalid values or incorrect datatypes into my structures. If it fails it will raise an Exception
		of some kind and probably print a stack trace I guess?"""
		# name_jp, name_en: strings
		assert isinstance(self.name_jp, str)
		assert isinstance(self.name_en, str)
		# bone_idx: int references a bone
		assert isinstance(self.bone_idx, int)
		# pos: X Y Z position vec3
		assert is_good_vector(3, self.pos)
		# rot: X Y Z rotation vec3
		assert is_good_vector(3, self.rot)
		# size: X Y Z size vec3
		assert is_good_vector(3, self.size)
		# shape: RigidBodyShape enum
		assert isinstance(self.shape, RigidBodyShape)
		# group: int [1 - 16]
		assert isinstance(self.group, int)
		assert 1 <= self.group <= 16
		# nocollide_set: SET of ints each [1 - 16]
		assert isinstance(self.nocollide_set, set)
		for a in self.nocollide_set:
			assert isinstance(a, int)
			assert 1 <= a <= 16
		# phys_mode: RigidBodyPhysMode enum 
		assert isinstance(self.phys_mode, RigidBodyPhysMode)
		# phys_mass: float
		assert isinstance(self.phys_mass, (int,float))
		# phys_move_damp, phys_rot_damp, phys_repel, phys_friction: float range [0.0 - 1.0]
		assert isinstance(self.phys_move_damp, (int,float))
		assert isinstance(self.phys_rot_damp, (int,float))
		assert isinstance(self.phys_repel, (int,float))
		assert isinstance(self.phys_friction, (int,float))
		# assert 0.0 <= self.phys_move_damp <= 1.0
		# assert 0.0 <= self.phys_rot_damp <= 1.0
		# assert 0.0 <= self.phys_repel <= 1.0
		# assert 0.0 <= self.phys_friction <= 1.0


class PmxJoint(_BasePmx):
	# note: this block is the order of args in the old system, does not represent order of args in .list() member
	# thisjoint = [name_jp, name_en, jointtype, rb1_idx, rb2_idx, posX, posY, posZ,
	# 			 rotX, rotY, rotZ, posminX, posminY, posminZ, posmaxX, posmaxY, posmaxZ,
	# 			 rotminX, rotminY, rotminZ, rotmaxX, rotmaxY, rotmaxZ,
	# 			 springposX, springposY, springposZ, springrotX, springrotY, springrotZ]
	def __init__(self,
				 name_jp: str, name_en: str,
				 jointtype: JointType,
				 rb1_idx: int, rb2_idx: int,
				 pos: List[float],
				 rot: List[float],
				 movemin: List[float],
				 movemax: List[float],
				 movespring: List[float],
				 rotmin: List[float],
				 rotmax: List[float],
				 rotspring: List[float],
				 ):
		self.name_jp = name_jp
		self.name_en = name_en
		# jointtype: 0=spring6DOF, all others are v2.1 only!!!! 1=6dof, 2=p2p, 3=conetwist, 4=slider, 5=hinge
		self.jointtype = jointtype
		self.rb1_idx = rb1_idx
		self.rb2_idx = rb2_idx
		self.pos = pos
		self.rot = rot
		self.movemin = movemin
		self.movemax = movemax
		self.movespring = movespring
		self.rotmin = rotmin
		self.rotmax = rotmax
		self.rotspring = rotspring
	def list(self) -> list:
		return [self.name_jp, self.name_en, self.jointtype, self.rb1_idx, self.rb2_idx,
				self.pos, self.rot,
				self.movemin, self.movemax, self.movespring,
				self.rotmin, self.rotmax, self.rotspring,
				]
	def _validate(self, parentlist=None):
		""" This performs type-checking and input validation on the item, as a way to protect against bad code
		assigning invalid values or incorrect datatypes into my structures. If it fails it will raise an Exception
		of some kind and probably print a stack trace I guess?"""
		# name_jp, name_en: strings
		assert isinstance(self.name_jp, str)
		assert isinstance(self.name_en, str)
		# jointtype: JointType enum
		assert isinstance(self.jointtype, JointType)
		# rb1_idx, rb2_idx: rigid body index, int
		assert isinstance(self.rb1_idx, int)
		assert isinstance(self.rb2_idx, int)
		# pos: X Y Z position vec3
		assert is_good_vector(3, self.pos)
		# rot: X Y Z rotation vec3
		assert is_good_vector(3, self.rot)
		# movemin: X Y Z minimum movement limits, vec3
		# movemax: X Y Z maximum movement limits, vec3
		# movespring: X Y Z movement springiness, vec3
		assert is_good_vector(3, self.movemin)
		assert is_good_vector(3, self.movemax)
		assert is_good_vector(3, self.movespring)
		# rotmin: X Y Z minimum rotation limits, vec3
		# rotmax: X Y Z maximum rotation limits, vec3
		# rotspring: X Y Z rotation springiness, vec3
		assert is_good_vector(3, self.rotmin)
		assert is_good_vector(3, self.rotmax)
		assert is_good_vector(3, self.rotspring)


class PmxSoftBody(_BasePmx):
	# i don't plan to support v2.1 so I'm not gonna try to hard to understand the meaning of these data fields
	# this is mostly to consume the data so there are no bytes left over when done parsing a file to trigger warnings
	# note: this is also untested because i dont care about it lol
	# note: this block is the order of args in the old system, does not represent order of args in .list() member
	# thissoft = [name_jp, name_en, shape, idx_mat, group, nocollide_mask, flags,
	# 			b_link_create_dist, num_clusters, total_mass, collision_marign, aerodynamics_model,
	# 			vcf, dp, dg, lf, pr, vc, df, mt, rch, kch, sch, ah,
	# 			srhr_cl, skhr_cl, sshr_cl, sr_splt_cl, sk_splt_cl, ss_splt_cl,
	# 			v_it, p_it, d_it, c_it, mat_lst, mat_ast, mat_vst, anchors_list, vertex_pin_list]
	def __init__(self, name_jp, name_en, shape, idx_mat, group, nocollide_mask, flags,
				 b_link_create_dist, num_clusters, total_mass, collision_margin, aerodynamics_model,
				 vcf, dp, dg, lf, pr, vc, df, mt, rch, kch, sch, ah,
				 srhr_cl, skhr_cl, sshr_cl, sr_splt_cl, sk_splt_cl, ss_splt_cl,
				 v_it, p_it, d_it, c_it, mat_lst, mat_ast, mat_vst,
				 anchors_list: List[List[int]], vertex_pin_list: List[int]):
		self.name_jp = name_jp
		self.name_en = name_en
		self.shape = shape
		self.idx_mat = idx_mat
		self.group = group
		self.nocollide_mask = nocollide_mask
		self.flags = flags
		self.b_link_create_dist = b_link_create_dist
		self.num_clusters = num_clusters
		self.total_mass = total_mass
		self.collision_margin = collision_margin
		self.aerodynamics_model = aerodynamics_model
		self.vcf = vcf
		self.dp = dp
		self.dg = dg
		self.lf = lf
		self.pr = pr
		self.vc = vc
		self.df = df
		self.mt = mt
		self.rch = rch
		self.kch = kch
		self.sch = sch
		self.ah = ah
		self.srhr_cl = srhr_cl
		self.skhr_cl = skhr_cl
		self.sshr_cl = sshr_cl
		self.sr_splt_cl = sr_splt_cl
		self.sk_splt_cl = sk_splt_cl
		self.ss_splt_cl = ss_splt_cl
		self.v_it = v_it
		self.p_it = p_it
		self.d_it = d_it
		self.c_it = c_it
		self.mat_lst = mat_lst
		self.mat_ast = mat_ast
		self.mat_vst = mat_vst
		self.anchors_list = anchors_list
		self.vertex_pin_list = vertex_pin_list
	def list(self) -> list:
		return [self.name_jp, self.name_en, self.shape, self.idx_mat, self.group, self.nocollide_mask, self.flags,
				self.b_link_create_dist, self.num_clusters, self.total_mass, self.collision_margin,
				self.aerodynamics_model, self.vcf, self.dp, self.dg, self.lf, self.pr, self.vc, self.df, self.mt,
				self.rch, self.kch, self.sch, self.ah,
				self.srhr_cl, self.skhr_cl, self.sshr_cl, self.sr_splt_cl, self.sk_splt_cl, self.ss_splt_cl,
				self.v_it, self.p_it, self.d_it, self.c_it,
				self.mat_lst, self.mat_ast, self.mat_vst,
				self.anchors_list, self.vertex_pin_list]
	def _validate(self, parentlist=None):
		# i don't give a flying fuck about the softbodies
		pass


class Pmx(_BasePmx):
	# [A, B, C, D, E, F, G, H, I, J, K]
	def __init__(self,
				 header: PmxHeader,
				 verts: List[PmxVertex],
				 faces: List[List[int]],
				 # texes: List[str],
				 mats: List[PmxMaterial],
				 bones: List[PmxBone],
				 morphs: List[PmxMorph],
				 frames: List[PmxFrame],
				 rbodies: List[PmxRigidBody],
				 joints: List[PmxJoint],
				 sbodies: List[PmxSoftBody]=None
				 ):
		if sbodies is None:
			assert header.ver == 2.0
			sbodies = []
		self.header = header
		self.verts = verts
		self.faces = faces
		# self.textures = texes
		self.materials = mats
		self.bones = bones
		self.morphs = morphs
		self.frames = frames
		self.rigidbodies = rbodies
		self.joints = joints
		self.softbodies = sbodies
	def list(self) -> list:
		return [self.header.list(),						#0
				[i.list() for i in self.verts],			#1
				self.faces,								#2
				# self.textures,							#3
				[i.list() for i in self.materials],		#4
				[i.list() for i in self.bones],			#5
				[i.list() for i in self.morphs],		#6
				[i.list() for i in self.frames],		#7
				[i.list() for i in self.rigidbodies],	#8
				[i.list() for i in self.joints],		#9
				[i.list() for i in self.softbodies],	#10
				]
	def _validate(self, parentlist=None):
		# header: PmxHeader object
		assert isinstance(self.header, PmxHeader)
		assert self.header.validate()
		# verts: list of PmxVertex objects
		assert isinstance(self.verts, (list,tuple))
		for v in self.verts:
			assert isinstance(v, PmxVertex)
			assert v.validate(parentlist=self.verts)
		# faces: list of faces, where each face is a list of 3 ints (vertex references)
		assert isinstance(self.faces, (list,tuple))
		for f in self.faces:
			assert isinstance(f, (list,tuple))
			for ff in f:
				assert isinstance(ff, int)
		# # textures: list of strings
		# assert isinstance(self.textures, (list,tuple))
		# for t in self.textures:
		# 	assert isinstance(t, str)
		# materials: list of PmxMaterial objects
		assert isinstance(self.materials, (list,tuple))
		for v in self.materials:
			assert isinstance(v, PmxMaterial)
			assert v.validate(parentlist=self.materials)
		# bones: list of PmxBone objects
		assert isinstance(self.bones, (list,tuple))
		for v in self.bones:
			assert isinstance(v, PmxBone)
			assert v.validate(parentlist=self.bones)
		# morphs: list of PmxMorph objects
		assert isinstance(self.morphs, (list,tuple))
		for v in self.morphs:
			assert isinstance(v, PmxMorph)
			assert v.validate(parentlist=self.morphs)
		# frames: list of PmxFrame objects
		assert isinstance(self.frames, (list,tuple))
		for v in self.frames:
			assert isinstance(v, PmxFrame)
			assert v.validate(parentlist=self.frames)
		# rigidbodies: list of PmxRigidBody objects
		assert isinstance(self.rigidbodies, (list,tuple))
		for v in self.rigidbodies:
			assert isinstance(v, PmxRigidBody)
			assert v.validate(parentlist=self.rigidbodies)
		# softbodies: list of PmxSoftBody objects, or None
		if self.softbodies is not None:
			assert isinstance(self.softbodies, (list,tuple))
			for v in self.softbodies:
				assert isinstance(v, PmxSoftBody)
				assert v.validate(parentlist=self.softbodies)
		pass

		
if __name__ == '__main__':
	print(_SCRIPT_VERSION)
	core.pause_and_quit("you are not supposed to directly run this file haha")


