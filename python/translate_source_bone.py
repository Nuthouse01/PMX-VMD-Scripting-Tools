import os

try:
    from . import nuthouse01_core as core
    from . import nuthouse01_pmx_parser as pmxlib
    from . import nuthouse01_pmx_struct as pmxstruct
    from . import file_sort_textures
    from ._prune_unused_vertices import newval_from_range_map, delme_list_to_rangemap
    from ._prune_unused_bones import insert_single_bone
except ImportError as eee:
    try:
        import nuthouse01_core as core
        import nuthouse01_pmx_parser as pmxlib
        import nuthouse01_pmx_struct as pmxstruct
        import file_sort_textures
        from _prune_unused_bones import insert_single_bone
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
finger_dict = {
    ["ValveBiped.Bip01_R_Finger4", "bip_pinky_0_R"]: "右小指１",
    ["ValveBiped.Bip01_R_Finger41", "bip_pinky_1_R"]: "右小指２",
    ["ValveBiped.Bip01_R_Finger42", "bip_pinky_2_R"]: "右小指３",
    ["ValveBiped.Bip01_R_Finger3", "bip_ring_0_R"]: "右薬指１",
    ["ValveBiped.Bip01_R_Finger31", "bip_ring_1_R"]: "右薬指２",
    ["ValveBiped.Bip01_R_Finger32", "bip_ring_2_R"]: "右薬指３",
    ["ValveBiped.Bip01_R_Finger2", "bip_middle_0_R"]: "右中指１",
    ["ValveBiped.Bip01_R_Finger21", "bip_middle_1_R"]: "右中指２",
    ["ValveBiped.Bip01_R_Finger22", "bip_middle_2_R"]: "右中指３",
    ["ValveBiped.Bip01_R_Finger1", "bip_index_0_R"]: "右人指１",
    ["ValveBiped.Bip01_R_Finger11", "bip_index_1_R"]: "右人指２",
    ["ValveBiped.Bip01_R_Finger12", "bip_index_2_R"]: "右人指３",
    ["ValveBiped.Bip01_R_Finger0", "bip_thumb_0_R"]: "右親指１",
    ["ValveBiped.Bip01_R_Finger01", "bip_thumb_1_R"]: "右親指２",
    ["ValveBiped.Bip01_R_Finger02", "bip_thumb_2_R"]: "右親指３",  # no bone for the second joint here but anyway

    ["ValveBiped.Bip01_L_Finger4", "bip_pinky_0_L"]: "左小指１",
    ["ValveBiped.Bip01_L_Finger41", "bip_pinky_1_L"]: "左小指２",
    ["ValveBiped.Bip01_L_Finger42", "bip_pinky_2_L"]: "左小指３",
    ["ValveBiped.Bip01_L_Finger3", "bip_ring_0_L"]: "左薬指１",
    ["ValveBiped.Bip01_L_Finger31", "bip_ring_1_L"]: "左薬指２",
    ["ValveBiped.Bip01_L_Finger32", "bip_ring_2_L"]: "左薬指３",
    ["ValveBiped.Bip01_L_Finger2", "bip_middle_0_L"]: "左中指１",
    ["ValveBiped.Bip01_L_Finger21", "bip_middle_1_L"]: "左中指２",
    ["ValveBiped.Bip01_L_Finger22", "bip_middle_2_L"]: "左中指３",
    ["ValveBiped.Bip01_L_Finger1", "bip_index_0_L"]: "左人指１",
    ["ValveBiped.Bip01_L_Finger11", "bip_index_1_L"]: "左人指２",
    ["ValveBiped.Bip01_L_Finger12", "bip_index_2_L"]: "左人指３",
    ["ValveBiped.Bip01_L_Finger0", "bip_thumb_0_L"]: "左親指１",
    ["ValveBiped.Bip01_L_Finger01", "bip_thumb_1_L"]: "左親指２",
    ["ValveBiped.Bip01_L_Finger02", "bip_thumb_2_L"]: "左親指３"
}
arm_dict = {
    ["ValveBiped.Bip01_R_Clavicle", "bip_collar_R"]: "右肩",
    ["ValveBiped.Bip01_R_UpperArm", "bip_upperArm_R"]: "右腕",
    ["ValveBiped.Bip01_R_Forearm", "bip_lowerArm_R"]: "右ひじ",
    ["ValveBiped.Bip01_R_Hand", "bip_hand_R"]: "右手捩",

    ["ValveBiped.Bip01_L_Clavicle", "bip_collar_L"]: "左肩",
    ["ValveBiped.Bip01_L_UpperArm", "bip_upperArm_L"]: "左腕",
    ["ValveBiped.Bip01_L_Forearm", "bip_lowerArm_L"]: "左ひじ",
    ["ValveBiped.Bip01_L_Hand", "bip_hand_L"]: "左手捩"
}
leg_dict = {
    ["ValveBiped.Bip01_R_Thigh", "bip_hip_R"]: "右足",
    ["ValveBiped.Bip01_R_Calf", "bip_knee_R"]: "右ひざ",
    ["ValveBiped.Bip01_R_Foot", "bip_foot_R"]: "右足首",
    ["ValveBiped.Bip01_R_Toe0", "bip_toe_R"]: "右つま先",

    ["ValveBiped.Bip01_L_Thigh", "bip_hip_L"]: "左足",
    ["ValveBiped.Bip01_L_Calf", "bip_knee_L"]: "左ひざ",
    ["ValveBiped.Bip01_L_Foot", "bip_foot_L"]: "左足首",
    ["ValveBiped.Bip01_L_Toe0", "bip_toe_L"]: "左つま先"
}
body_dict = {
    ["ValveBiped.Bip01_Pelvis", "bip_pelvis"]: "下半身",
    ["ValveBiped.Bip01_Spine", "bip_spine_0"]: "下半身",
    ["ValveBiped.Bip01_Spine1", "bip_spine_1"]: "上半身",
    ["ValveBiped.Bip01_Spine2", "bip_spine_2"]: "上半身2",
    ["ValveBiped.Bip01_Spine4", "bip_spine_3"]: "首",  # this is at the base of the neck, we can combine it
    ["ValveBiped.Bip01_Neck1", "bip_neck"]: "首",
    ["ValveBiped.Bip01_Head1", "bip_head"]: "頭"
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
    big_dict: dict = {**body_dict, **leg_dict, **arm_dict, **finger_dict}

    # for some reasons, we can find item in a list with a boolean index, it is unused anyway
    is_old: bool = False

    old_bip_key = "bip_"
    # just to make sure with many instances
    if old_bip_key in retme.bones[0].name_jp or old_bip_key in retme.bones[1].name_jp or old_bip_key in retme.bones[2].name_jp:
        is_old = True

    # checking for last leg item so the code could be scalable
    last_leg_item: int
    last_leg_name: str

    r_l_index: int = 0
    r_k_index: int = 0
    r_a_index: int = 0
    r_t_index: int = 0
    l_l_index: int = 0
    l_k_index: int = 0
    l_a_index: int = 0
    l_t_index: int = 0

    last_bone_index = len(retme.bones) - 1

    # lol this is a mess but it works just fine okay
    for key in big_dict:
        for index, i in enumerate(retme.bones):
            # usually, the toes are the last parts of the legs, from there, we can interject the IK bones
            if i.name_jp in ["ValveBiped.Bip01_R_Toe0", "bip_toe_R"]:
                r_t_index = index
            elif i.name_jp in ["ValveBiped.Bip01_L_Toe0", "bip_toe_L"]:
                l_t_index = index

            # without this, the pelvis will show as "green"
            elif i.name_jp in ["ValveBiped.Bip01_Pelvis", "bip_pelvis"]:
                retme.bones[index].has_translate = False

            elif i.name_jp in ["ValveBiped.Bip01_R_Foot", "bip_foot_R"]:
                r_a_index = index
            elif i.name_jp in ["ValveBiped.Bip01_L_Foot", "bip_foot_L"]:
                l_a_index = index
            elif i.name_jp in ["ValveBiped.Bip01_R_Calf", "bip_knee_R"]:
                r_k_index = index
            elif i.name_jp in ["ValveBiped.Bip01_L_Calf", "bip_knee_L"]:
                l_k_index = index
            elif i.name_jp in ["ValveBiped.Bip01_R_Thigh", "bip_hip_R"]:
                r_l_index = index
            elif i.name_jp in ["ValveBiped.Bip01_L_Thigh", "bip_hip_L"]:
                l_l_index = index

            # the part that replaces texts
            if i.name_jp in key:
                retme.bones[index].name_jp = big_dict[key]

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

    # adding IK and such

    leg_left_ankle_obj = retme.bones[l_a_index]
    leg_left_toe_obj = retme.bones[l_t_index]
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
    #     retme.bones.insert(last_leg_item + 1, )

    leg_left_ik_obj = pmxstruct.PmxBone(leg_left_ik_name, "", leg_left_ankle_pos, last_bone_index + 5, 0, False,
                                        True, True, True, True, True,
                                        False, [0.0, 0.0, 0.0], False, False, False,
                                        False, False, None, None, None, None, None, None,
                                        l_a_index, 40, 114.5916,
                                        [pmxstruct.PmxBoneIkLink(idx=l_k_index, limit_min=knee_limit_1, limit_max=knee_limit_2),
                                         pmxstruct.PmxBoneIkLink(idx=l_l_index)])
    insert_single_bone()
    retme.bones.insert(last_bone_index + 1, leg_left_ik_obj)

    leg_left_toe_ik_obj = pmxstruct.PmxBone(leg_left_toe_ik_name, "", leg_left_toe_pos, last_bone_index + 1, 0,
                                            False,
                                            True, True, True, True, True,
                                            False, [0, 0, 0], False, False, False,
                                            False, False, None, None, None, None, None, None,
                                            l_t_index, 3, 229.1831, [pmxstruct.PmxBoneIkLink(idx=l_a_index)])
    retme.bones.insert(last_bone_index + 2, leg_left_toe_ik_obj)

    leg_right_ik_obj = pmxstruct.PmxBone(leg_right_ik_name, "", leg_right_ankle_pos, last_bone_index + 5, 0,
                                         False,
                                         True, True, True, True, True,
                                         False, [0.0, 0.0, 0.0], False, False, False,
                                         False, False, None, None, None, None, None, None,
                                         r_a_index, 40, 114.5916,
                                         [pmxstruct.PmxBoneIkLink(idx=r_k_index, limit_min=knee_limit_1, limit_max=knee_limit_2),
                                          pmxstruct.PmxBoneIkLink(idx=r_l_index)])
    retme.bones.insert(last_bone_index + 3, leg_right_ik_obj)

    leg_right_toe_ik_obj = pmxstruct.PmxBone(leg_right_toe_ik_name, "", leg_right_toe_pos, last_bone_index + 3, 0,
                                             False,
                                             True, True, True, True, True,
                                             False, [0, 0, 0], False, False, False,
                                             False, False, None, None, None, None, None, None,
                                             r_t_index, 3, 229.1831, [pmxstruct.PmxBoneIkLink(idx=r_a_index)])
    retme.bones.insert(last_bone_index + 4, leg_right_toe_ik_obj)

    # # base part
    b4_pos = [0, 0, 0]

    b3_pos = [-4.999999873689376e-06, 21, -0.533614993095398]
    b2_pos = b3_pos
    b1_pos = [-4.999999873689376e-06, 32, -0.533614993095398]
    #
    # # 全ての親, name_en, [0.0, 0.0, -0.4735046625137329], -1, 0, False,
    # # True, True, True, True,
    # # False, [0.0, 0.0, 0.0], False, False, None,
    # # None, False, None, False, None, None, False, None, False,
    # # None, None, None, None
    #
    # # base order: 上半身, 下半身, 腰 (b_1), グルーブ, センター, 全ての親
    # # the parents would be fixed later
    b4_obj = pmxstruct.PmxBone(b4_name, "", b4_pos, -1, 0, False,
                               True, True, True, True, False,
                               False, [0, 0, 0], False, False, None,
                               None, False, None, None, None, None, None, None,
                               None, None, None, None
                               )
    retme.bones.insert(last_bone_index + 5, b4_obj)

    b3_obj = pmxstruct.PmxBone(b3_name, "", b3_pos, last_bone_index + 5, 0, False,
                               True, True, True, True, False,
                               False, [0, 0, 0], False, False, None,
                               None, False, None, None, None, None, None, None,
                               None, None, None, None
                               )
    retme.bones.insert(last_bone_index + 6, b3_obj)

    b2_obj = pmxstruct.PmxBone(b2_name, "", b2_pos, last_bone_index + 6, 0, False,
                               True, True, True, True, False,
                               False, [0, 0, 0], False, False, None,
                               None, False, None, None, None, None, None, None,
                               None, None, None, None
                               )
    retme.bones.insert(last_bone_index + 7, b2_obj)

    b1_obj = pmxstruct.PmxBone(b1_name, "", b1_pos, last_bone_index + 7, 0, False,
                               True, False, True, True, False,
                               False, [0, 0, 0], False, False, None,
                               None, False, None, None, None, None, None, None,
                               None, None, None, None
                               )
    retme.bones.insert(last_bone_index + 8, b1_obj)

    output_filename_pmx = input_filename_pmx[0:-4] + "_sourcetrans.pmx"
    pmxlib.write_pmx(output_filename_pmx, retme, moreinfo=moreinfo)


if __name__ == "__main__":
    main()
