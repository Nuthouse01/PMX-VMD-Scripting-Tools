import os

try:
    from . import nuthouse01_core as core
    from . import nuthouse01_pmx_parser as pmxlib
    from . import nuthouse01_pmx_struct as pmxstruct
    from . import file_sort_textures
    from ._prune_unused_vertices import newval_from_range_map, delme_list_to_rangemap
except ImportError as eee:
    try:
        import nuthouse01_core as core
        import nuthouse01_pmx_parser as pmxlib
        import nuthouse01_pmx_struct as pmxstruct
        import file_sort_textures
        from _prune_unused_vertices import newval_from_range_map, delme_list_to_rangemap
    except ImportError as eee:
        print(eee.__class__.__name__, eee)
        print(
            "ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
        print("...press ENTER to exit...")
        input()
        exit()
        core = pmxlib = pmxstruct = None
        newval_from_range_map = delme_list_to_rangemap = None

caution_message: str = '''
This will not 100% make your model work with your motion or work as intended.
'''

instructions: str = '''
This is not a a full plug-and-play script. You still need to work a little to finalize all the bones and names.

After you are done with the script, open `yourfilename_sourcetrans.pmx`, find the 4 bones ordered from top to bottom:
全ての親, センター, グルーブ, 腰 (They are in the "Bone" tab)
Shift select them, move all of them to the top by tediously clicking the uparrow button or the very bottom left button.
Merge similar bone by names through menu Edit (E), Bone (B), Merge bone with similar name (M).
Finally, have "腰" as parent of "上半身" and "下半身" by clicking on those two bones and set parent to that singular bone.

Since this is not plug-and-play, your model weight and UV won't always work perfectly with the motions, try to
move the bones around and merge unused bones to avoid animation glitches.
'''

known_issues: str = '''
* Running the script without changes at
File "/PMX-VMD-Scripting-Tools/python/nuthouse01_pmx_parser.py", line 745, in encode_pmx_bones
Will result in object/list error where struct does not pass on an object attribute

* If run the same file again with this script, 
`TypeError: 'PmxBoneIkLink' object is not subscriptable` will show up at that same line
'''

# This takes PMX output from Crowbar
# New BIP
new_finger_dict = {
    "ValveBiped.Bip01_R_Finger4": "右小指１",
    "ValveBiped.Bip01_R_Finger41": "右小指２",
    "ValveBiped.Bip01_R_Finger42": "右小指３",
    "ValveBiped.Bip01_R_Finger3": "右薬指１",
    "ValveBiped.Bip01_R_Finger31": "右薬指２",
    "ValveBiped.Bip01_R_Finger32": "右薬指３",
    "ValveBiped.Bip01_R_Finger2": "右中指１",
    "ValveBiped.Bip01_R_Finger21": "右中指２",
    "ValveBiped.Bip01_R_Finger22": "右中指３",
    "ValveBiped.Bip01_R_Finger1": "右人指１",
    "ValveBiped.Bip01_R_Finger11": "右人指２",
    "ValveBiped.Bip01_R_Finger12": "右人指３",
    "ValveBiped.Bip01_R_Finger0": "右親指１",
    "ValveBiped.Bip01_R_Finger01": "右親指２",
    "ValveBiped.Bip01_R_Finger02": "右親指３",  # no bone for the second joint here

    "ValveBiped.Bip01_L_Finger4": "左小指１",
    "ValveBiped.Bip01_L_Finger41": "左小指２",
    "ValveBiped.Bip01_L_Finger42": "左小指３",
    "ValveBiped.Bip01_L_Finger3": "左薬指１",
    "ValveBiped.Bip01_L_Finger31": "左薬指２",
    "ValveBiped.Bip01_L_Finger32": "左薬指３",
    "ValveBiped.Bip01_L_Finger2": "左中指１",
    "ValveBiped.Bip01_L_Finger21": "左中指２",
    "ValveBiped.Bip01_L_Finger22": "左中指３",
    "ValveBiped.Bip01_L_Finger1": "左人指１",
    "ValveBiped.Bip01_L_Finger11": "左人指２",
    "ValveBiped.Bip01_L_Finger12": "左人指３",
    "ValveBiped.Bip01_L_Finger0": "左親指１",
    "ValveBiped.Bip01_L_Finger01": "左親指２",
    "ValveBiped.Bip01_L_Finger02": "左親指３"
}
new_arm_dict = {
    "ValveBiped.Bip01_R_Clavicle": "右肩",
    "ValveBiped.Bip01_R_UpperArm": "右腕",
    "ValveBiped.Bip01_R_Forearm": "右ひじ",
    "ValveBiped.Bip01_R_Hand": "右手捩",

    "ValveBiped.Bip01_L_Clavicle": "左肩",
    "ValveBiped.Bip01_L_UpperArm": "左腕",
    "ValveBiped.Bip01_L_Forearm": "左ひじ",
    "ValveBiped.Bip01_L_Hand": "左手捩"
}
new_leg_dict = {
    "ValveBiped.Bip01_R_Thigh": "右足",
    "ValveBiped.Bip01_R_Calf": "右ひざ",
    "ValveBiped.Bip01_R_Foot": "右足首",
    "ValveBiped.Bip01_R_Toe0": "右つま先",

    "ValveBiped.Bip01_L_Thigh": "左足",
    "ValveBiped.Bip01_L_Calf": "左ひざ",
    "ValveBiped.Bip01_L_Foot": "左足首",
    "ValveBiped.Bip01_L_Toe0": "左つま先"
}
new_body_dict = {
    "ValveBiped.Bip01_Pelvis": "下半身",
    "ValveBiped.Bip01_Spine": "下半身",
    "ValveBiped.Bip01_Spine1": "上半身",
    "ValveBiped.Bip01_Spine2": "上半身2",
    "ValveBiped.Bip01_Spine4": "首",  # this is at the base of the neck, we can combine it
    "ValveBiped.Bip01_Neck1": "首",
    "ValveBiped.Bip01_Head1": "頭"
}

# Old BIP
old_finger_dict = {
    "bip_index_0_R": "右親指１",
    "bip_index_1_R": "右親指２",
    "bip_index_2_R": "右親指３",
    "bip_thumb_0_R": "右人指１",
    "bip_thumb_1_R": "右人指２",
    "bip_thumb_2_R": "右人指３",
    "bip_middle_0_R": "右中指１",
    "bip_middle_1_R": "右中指２",
    "bip_middle_2_R": "右中指３",
    "bip_ring_0_R": "右薬指１",
    "bip_ring_1_R": "右薬指２",
    "bip_ring_2_R": "右薬指３",
    "bip_pinky_0_R": "右小指１",
    "bip_pinky_1_R": "右小指２",
    "bip_pinky_2_R": "右小指３",

    "bip_index_0_L": "左親指１",
    "bip_index_1_L": "左親指２",
    "bip_index_2_L": "左親指３",
    "bip_thumb_0_L": "左人指１",
    "bip_thumb_1_L": "左人指２",
    "bip_thumb_2_L": "左人指３",
    "bip_middle_0_L": "左中指１",
    "bip_middle_1_L": "左中指２",
    "bip_middle_2_L": "左中指３",
    "bip_ring_0_L": "左薬指１",
    "bip_ring_1_L": "左薬指２",
    "bip_ring_2_L": "左薬指３",
    "bip_pinky_0_L": "左小指１",
    "bip_pinky_1_L": "左小指２",
    "bip_pinky_2_L": "左小指３"
}
old_arm_dict = {
    "bip_collar_R": "右肩",
    "bip_upperArm_R": "右腕",
    "bip_lowerArm_R": "右ひじ",
    "bip_hand_R": "右手捩",

    "bip_collar_L": "左肩",
    "bip_upperArm_L": "左腕",
    "bip_lowerArm_L": "左ひじ",
    "bip_hand_L": "左手捩"
}
old_leg_dict = {
    "bip_hip_R": "右足",
    "bip_knee_R": "右ひざ",
    "bip_foot_R": "右足首",
    "bip_toe_R": "右つま先",

    "bip_hip_L": "左足",
    "bip_knee_L": "左ひざ",
    "bip_foot_L": "左足首",
    "bip_toe_L": "左つま先"
}
old_body_dict = {
    "bip_pelvis": "下半身",
    "bip_spine_0": "下半身",
    "bip_spine_1": "上半身",
    "bip_spine_2": "上半身2",
    "bip_spine_3": "首",
    "bip_neck": "首",
    "bip_head": "頭"
}

# base order: 上半身, 下半身, 腰, グルーブ, センター, 全ての親
# the rest of the work should be done in pmxeditor instead, jsut one click away


def main():
    # copied codes
    core.MY_PRINT_FUNC("Please enter name of PMX model file:")
    input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")

    moreinfo = False

    input_filename_pmx_abs = os.path.normpath(os.path.abspath(input_filename_pmx))
    startpath, input_filename_pmx_rel = os.path.split(input_filename_pmx_abs)

    # object
    retme: pmxstruct.Pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)

    # since there is an update to Valve Bip tools (I guess?), there is different bone names: the old and new one
    # only prefixes are changed along with order, thus there is a little bit scripting here to find the last leg
    big_dict: dict
    is_old: bool = False

    if "bip_" in retme.bones[0].name_jp:
        big_dict = {**old_body_dict,
                    **old_arm_dict,
                    **old_leg_dict,
                    **old_finger_dict}
        is_old = True

    else:
        big_dict = {**new_body_dict,
                    **new_arm_dict,
                    **new_leg_dict,
                    **new_finger_dict}

    # checking for last leg item so the code could be scalable
    last_leg_item: int
    last_leg_name: str
    last_leg_name_cmp_r: str = ""
    last_leg_name_cmp_l: str = ""

    # the last `index` method was not scalable, this one is
    r_l_index: int = 0
    r_k_index: int = 0
    r_a_index: int = 0
    r_t_index: int = 0
    l_l_index: int = 0
    l_k_index: int = 0
    l_a_index: int = 0
    l_t_index: int = 0

    # lol this is a mess but it works just fine okay
    for index, i in enumerate(retme.bones):
        # usually, the toes are the last parts of the legs, from there, we can interject the IK bones
        if i.name_jp == "bip_toe_R" or i.name_jp == "ValveBiped.Bip01_R_Toe0":
            r_t_index = index
            last_leg_name_cmp_r = i.name_jp
        elif i.name_jp == "bip_toe_L" or i.name_jp == "ValveBiped.Bip01_L_Toe0":
            l_t_index = index
            last_leg_name_cmp_l = i.name_jp

        # without this, the pelvis will start as "green"
        elif i.name_jp == "ValveBiped.Bip01_Pelvis" or i.name_jp == "bip_pelvis":
            retme.bones[index].has_translate = False

        elif i.name_jp == "ValveBiped.Bip01_R_Foot" or i.name_jp == "bip_foot_R":
            r_a_index = index
        elif i.name_jp == "ValveBiped.Bip01_L_Foot" or i.name_jp == "bip_foot_L":
            l_a_index = index
        elif i.name_jp == "ValveBiped.Bip01_R_Calf" or i.name_jp == "bip_knee_R":
            r_k_index = index
        elif i.name_jp == "ValveBiped.Bip01_L_Calf" or i.name_jp == "bip_knee_L":
            l_k_index = index
        elif i.name_jp == "ValveBiped.Bip01_R_Thigh" or i.name_jp == "bip_hip_R":
            r_l_index = index
        elif i.name_jp == "ValveBiped.Bip01_L_Thigh" or i.name_jp == "bip_hip_L":
            l_l_index = index

    if r_t_index > l_t_index:
        # last_leg_item = r_t_index  # consider unnecessary since the for loop is over an enumerate
        last_leg_name = last_leg_name_cmp_r
    else:
        # last_leg_item = l_t_index
        last_leg_name = last_leg_name_cmp_l
    # print(f"This is last leg item {old_last_leg_item}")

    # base bone section
    # base order: 上半身, 下半身, 腰 (b_1), グルーブ, センター, 全ての親
    b1_name = "腰"
    b2_name = "グルーブ"
    b3_name = "センター"
    b4_name = "全ての親"

    # IK bone section
    leg_left_ik_name = "左足ＩＫ"
    leg_left_toe_ik_name = "左つま先ＩＫ"
    leg_right_ik_name = "右足ＩＫ"
    leg_right_toe_ik_name = "右つま先ＩＫ"

    knee_limit_1 = [-3.1415927410125732, 0.0, 0.0]
    knee_limit_2 = [-0.008726646192371845, 0.0, 0.0]

    # for some reasons, this value will always be the same
    # pelvis_pos = [-4.999999873689376e-06, 38.566917419433594, -0.533614993095398]

    for key in big_dict:
        for index, name in enumerate(retme.bones):
            if name.name_jp == key:
                # sometiems it is at the end, sometimes it is not
                if name.name_jp == last_leg_name:
                    # adding IK and such
                    # leg_left_obj = retme.bones[index + l_l]
                    # leg_left_knee_obj = retme.bones[index + l_k]
                    leg_left_ankle_obj = retme.bones[l_a_index]
                    leg_left_toe_obj = retme.bones[l_t_index]
                    # leg_right_obj = retme.bones[index + r_l]
                    # leg_right_knee_obj = retme.bones[index + r_k]
                    leg_right_ankle_obj = retme.bones[r_a_index]
                    leg_right_toe_obj = retme.bones[r_t_index]

                    leg_left_ankle_pos = leg_left_ankle_obj.pos
                    leg_left_toe_pos = leg_left_toe_obj.pos
                    leg_right_ankle_pos = leg_right_ankle_obj.pos
                    leg_right_toe_pos = leg_right_toe_obj.pos

                    # toe /// places of some value wont match with the struct /// taken from hololive's korone model
                    # name, name, [-0.823277473449707, 0.2155265510082245, -1.8799238204956055], 112, 0, False,
                    # True, True, True, True,
                    # False, [0.0, -1.3884940147399902, 1.2653569569920364e-07] /// This is offset, False, False, None,
                    # None, False, None, False, None, None, False, None, True,
                    # 111, 160, 1.0, [[110, None, None]]

                    # leg
                    # 右足ＩＫ, en_name, [-0.8402935862541199, 1.16348397731781, 0.3492986857891083], 0, 0, False,
                    # True, True, True, True,
                    # False, [0.0, -2.53071505085245e-07, 1.3884940147399902], False, False, None,
                    # None, False, None, False, None, None, False, None, True,
                    # 110, 85, 1.9896754026412964, [[109, [-3.1415927410125732, 0.0, 0.0], [-0.008726646192371845, 0.0, 0.0]]
                    # /// These ik_links are in radians /// , [108, None, None]]
                    # if name == "ValveBiped.Bip01_R_Toe0":
                    #     retme.bones.insert(index + 1, )

                    leg_left_ik_obj = pmxstruct.PmxBone(leg_left_ik_name, "", leg_left_ankle_pos, index + 5, 0, False,
                                                        True, True, True, True, True,
                                                        False, [0.0, 0.0, 0.0], False, False, False,
                                                        False, False, None, None, None, None, None, None,
                                                        l_a_index, 85, 114.6149,
                                                        [[l_k_index, knee_limit_1, knee_limit_2],
                                                         [l_l_index, None, None]])
                    retme.bones.insert(index + 1, leg_left_ik_obj)

                    leg_left_toe_ik_obj = pmxstruct.PmxBone(leg_left_toe_ik_name, "", leg_left_toe_pos, index + 1, 0,
                                                            False,
                                                            True, True, True, True, True,
                                                            False, [0, 0, 0], False, False, False,
                                                            False, False, None, None, None, None, None, None,
                                                            l_t_index, 160, 1, [[l_a_index, None, None]])
                    retme.bones.insert(index + 2, leg_left_toe_ik_obj)

                    leg_right_ik_obj = pmxstruct.PmxBone(leg_right_ik_name, "", leg_right_ankle_pos, index + 5, 0,
                                                         False,
                                                         True, True, True, True, True,
                                                         False, [0.0, 0.0, 0.0], False, False, False,
                                                         False, False, None, None, None, None, None, None,
                                                         r_a_index, 85, 114.6149,
                                                         [[r_k_index, knee_limit_1, knee_limit_2],
                                                          [r_l_index, None, None]])
                    retme.bones.insert(index + 3, leg_right_ik_obj)

                    leg_right_toe_ik_obj = pmxstruct.PmxBone(leg_right_toe_ik_name, "", leg_right_toe_pos, index + 3, 0,
                                                             False,
                                                             True, True, True, True, True,
                                                             False, [0, 0, 0], False, False, False,
                                                             False, False, None, None, None, None, None, None,
                                                             r_t_index, 160, 1, [[r_a_index, None, None]])
                    retme.bones.insert(index + 4, leg_right_toe_ik_obj)

                    # base part
                    b4_pos = [0, 0, 0]

                    # for some reasons, if we pass value from pelvis_pos to b3_pos, pelvis_pos will change as well?
                    b3_pos = [-4.999999873689376e-06, 21, -0.533614993095398]
                    b2_pos = b3_pos
                    b1_pos = [-4.999999873689376e-06, 32, -0.533614993095398]

                    # 全ての親, name_en, [0.0, 0.0, -0.4735046625137329], -1, 0, False,
                    # True, True, True, True,
                    # False, [0.0, 0.0, 0.0], False, False, None,
                    # None, False, None, False, None, None, False, None, False,
                    # None, None, None, None

                    # base order: 上半身, 下半身, 腰 (b_1), グルーブ, センター, 全ての親
                    # the parents would be fixed later
                    b4_obj = pmxstruct.PmxBone(b4_name, "", b4_pos, -1, 0, False,
                                               True, True, True, True, False,
                                               False, [0, 0, 0], False, False, None,
                                               None, False, None, None, None, None, None, None,
                                               None, None, None, None
                                               )
                    retme.bones.insert(index + 5, b4_obj)

                    b3_obj = pmxstruct.PmxBone(b3_name, "", b3_pos, index + 5, 0, False,
                                               True, True, True, True, False,
                                               False, [0, 0, 0], False, False, None,
                                               None, False, None, None, None, None, None, None,
                                               None, None, None, None
                                               )
                    retme.bones.insert(index + 6, b3_obj)

                    b2_obj = pmxstruct.PmxBone(b2_name, "", b2_pos, index + 6, 0, False,
                                               True, True, True, True, False,
                                               False, [0, 0, 0], False, False, None,
                                               None, False, None, None, None, None, None, None,
                                               None, None, None, None
                                               )
                    retme.bones.insert(index + 7, b2_obj)

                    b1_obj = pmxstruct.PmxBone(b1_name, "", b1_pos, index + 7, 0, False,
                                               True, False, True, True, False,
                                               False, [0, 0, 0], False, False, None,
                                               None, False, None, None, None, None, None, None,
                                               None, None, None, None
                                               )
                    retme.bones.insert(index + 8, b1_obj)

                # have to check and add everything before changing the anchor's name
                retme.bones[index].name_jp = big_dict[key]

    output_filename_pmx = input_filename_pmx[0:-4] + "_sourcetrans.pmx"
    pmxlib.write_pmx(output_filename_pmx, retme, moreinfo=moreinfo)


if __name__ == "__main__":
    main()
