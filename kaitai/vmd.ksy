meta:
  id: vmd
  file-extension: vmd
  endian: le
  
# NOTE: all "strings" are fixed-size but null terminated, anything after null is garbage
# also, proper encoding is shift-jis(?) but multi-byte chars might be cut off mid-char! that makes encoding crash!

# depending on the system that created the VMD, if it should end with "no lightframes, no shadowframes, no ikdispframes" it might just omit some/all of those trailing zeros
# this causes the stream to end before its "done"
# but it's so common that it must be handled gracefully
# that's what all the "if: not _io.eof" lines are doing!

# several things need to be computed, like the quaternions need to convert to euler, etc
# basically kaitai will slurp up the bytestream into memory and get everything i need
# but then i need a 2nd pass to re-process things in specific ways and get the data into the fields I want
# so i still need to have my own oodles of class definitions and whatnot

# also kaitai doesnt support WRITING anything :( only READING
# so there's no point swapping over from my custom-built system yet, maybe not ever

# TODO: boneframe interpolation shit
# TODO: camframe interpocation shit


seq:
  - id: header
    type: t_header
  - id: num_boneframes
    if: not _io.eof
    type: u4
  - id: boneframes
    if: not _io.eof
    type: t_boneframe
    repeat: expr
    repeat-expr: num_boneframes
  - id: num_morphframes
    if: not _io.eof
    type: u4
  - id: morphframes
    if: not _io.eof
    type: t_morphframe
    repeat: expr
    repeat-expr: num_morphframes
  - id: num_camframes
    if: not _io.eof
    type: u4
  - id: camframes
    if: not _io.eof
    type: t_camframe
    repeat: expr
    repeat-expr: num_camframes
  - id: num_lightframes
    if: not _io.eof
    type: u4
  - id: lightframes
    if: not _io.eof
    type: t_lightframe
    repeat: expr
    repeat-expr: num_lightframes
  - id: num_shadowframes
    if: not _io.eof
    type: u4
  - id: shadowframes
    if: not _io.eof
    type: t_shadowframe
    repeat: expr
    repeat-expr: num_shadowframes
  - id: num_ikdispframes
    if: not _io.eof
    type: u4
  - id: ikdispframes
    if: not _io.eof
    type: t_ikdispframe
    repeat: expr
    repeat-expr: num_ikdispframes
  - id: tail
    size-eos: true
	# absorb all remaining data

    

types:
  t_vec3:
    seq:
      - id: vec3
        type: f4
        repeat: expr
        repeat-expr: 3
  t_vec4:
    seq:
      - id: vec4
        type: f4
        repeat: expr
        repeat-expr: 4
  t_header:
    seq:
      - id: magic
        contents: ['Vocaloid Motion Data ']
        # contents: [0x56, 0x6f, 0x63, 0x61, 0x6c, 0x6f, 0x69, 0x64, 0x20, 0x4d, 0x6f, 0x74, 0x69, 0x6f, 0x6e, 0x20, 0x44, 0x61, 0x74, 0x61, 0x20]
      - id: verstring
        size: 4
        type: str
        encoding: shift-jis
        # if verstring == "0002" then this is "version 2" and the model name str is 20 chars
        # if verstring == "file" then this is "version 1" and the model name str is 10 chars
      - size: 5
        # this just skips 5 bytes
      - id: modelname
        type: str
        encoding: shift-jis
        size: verstring == 'file' ? 10 : 20
        # i want to cast this to a string but it's not guaranteed to succeed :(
  t_boneframe:
    seq:
      - id: name
        size: 15
        # i want to cast this to a string but it's not guaranteed to succeed :(
        # the name of the bone this is applied to
      - id: framenum
        type: u4
      - id: pos_xyz
        type: t_vec3
      - id: rot_xyzw
        type: t_vec4
      - id: interp
        size: 64
        # TODO: unpack this different/better
  t_morphframe:
    seq:
      - id: name
        size: 15
        # i want to cast this to a string but it's not guaranteed to succeed :(
        # the name of the bone this is applied to
      - id: framenum
        type: u4
      - id: value
        type: f4
  t_camframe:
    seq:
      - id: framenum
        type: u4
      - id: dist
        type: f4
      - id: pos_xyz
        type: t_vec3
      - id: rot_xyz
        type: t_vec3
        # rotation in euler angles, NOT QUATERNION
      - id: interp
        size: 24
        # TODO: unpack this different/better
      - id: fov
        type: u4
      - id: is_perspective
        type: u1
        # BUG: when this is set to 'b1' for boolean it sometimes doesn't move the readpoint!!
  t_lightframe:
    seq:
      - id: framenum
        type: u4
      - id: color_rgb
		# each component is [0.0-1.0]
        type: t_vec3
      - id: pos_xyz
		# each component is [-1.0 to 1.0]
        type: t_vec3
  t_shadowframe:
    seq:
      - id: framenum
        type: u4
      - id: mode
        type: u1
        # TODO: enum? (0=off, 1=mode1, 2=mode2)
      - id: dist
        type: f4
        # NOTE: displayed as [0,9999] but stored as [0.1-0.0]
        # range-inverted, only to .1
  t_ikdispframe:
    seq:
      - id: framenum
        type: u4
      - id: visible
        type: u1
        # BUG: when this is set to 'b1' for boolean it sometimes doesn't move the readpoint!!
        # note: called "disp" in many places
      - id: num_ikbones
        type: u4
      - id: ikbones
        type: t_ikbone
        repeat: expr
        repeat-expr: num_ikbones
  t_ikbone:
    seq:
      - id: bname
        size: 20
        # i want to cast this to a string but it's not guaranteed to succeed :(
        # the name of the bone this is applied to
      - id: ik_enable
        type: u1
        # BUG: when this is set to 'b1' for boolean it sometimes doesn't move the readpoint!!

