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

### This takes PMX output from Crowbar
finger_dict = {
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

arm_dict = {
    "ValveBiped.Bip01_R_Clavicle": "右肩",
    "ValveBiped.Bip01_R_UpperArm": "右腕",
    "ValveBiped.Bip01_R_Forearm": "右ひじ",
    "ValveBiped.Bip01_R_Hand": "右手捩",

    "ValveBiped.Bip01_L_Clavicle": "左肩",
    "ValveBiped.Bip01_L_UpperArm": "左腕",
    "ValveBiped.Bip01_L_Forearm": "左ひじ",
    "ValveBiped.Bip01_L_Hand": "左手捩"
}

leg_dict = {
    "ValveBiped.Bip01_R_Thigh": "右足",
    "ValveBiped.Bip01_R_Calf": "右ひざ",
    "ValveBiped.Bip01_R_Foot": "右足首",
    "ValveBiped.Bip01_R_Toe0": "右つま先",

    "ValveBiped.Bip01_L_Thigh": "左足",
    "ValveBiped.Bip01_L_Calf": "左ひざ",
    "ValveBiped.Bip01_L_Foot": "左足首",
    "ValveBiped.Bip01_L_Toe0": "左つま先"
}

body_dict = {
    # "ValveBiped.Bip01_Pelvis": "下半身",  # we only need 上半身 and 2 so these guys can be combined later in Pmxeditor
    "ValveBiped.Bip01_Pelvis": "下半身",
    "ValveBiped.Bip01_Spine": "下半身",
    "ValveBiped.Bip01_Spine1": "上半身",
    "ValveBiped.Bip01_Spine2": "上半身2",
    "ValveBiped.Bip01_Spine4": "首",  # this is at the base of the neck, we can combine it
    "ValveBiped.Bip01_Neck1": "首",
    "ValveBiped.Bip01_Head1": "頭"
}
# base order: 上半身, 下半身, 腰, グルーブ, センター, 全ての親
# the rest of the work should be done in pmxeditor instead, jsut one click away

big_dict = {**body_dict, **arm_dict, **leg_dict, **finger_dict}

caution_message: str = '''
This will not 100% make your model work with your motion or work as intended.
You probably still need to adjust your model through Transform View (F9).
'''


def main():
    # copied codes
    global b1_index
    core.MY_PRINT_FUNC("Please enter name of PMX model file:")
    input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")

    moreinfo = False

    input_filename_pmx_abs = os.path.normpath(os.path.abspath(input_filename_pmx))
    startpath, input_filename_pmx_rel = os.path.split(input_filename_pmx_abs)

    # object
    retme: pmxstruct.Pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)

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

    # index of leg items from left toe
    l_l = -3
    l_k = -2
    l_a = -1

    r_l = -7
    r_k = -6
    r_a = -5
    r_t = -4

    knee_limit_1 = [-3.1415927410125732, 0.0, 0.0]
    knee_limit_2 = [-0.008726646192371845, 0.0, 0.0]

    b1_index = 0

    for key in big_dict:
        for index, name in enumerate(retme.bones):
            if name.name_jp == key:
                if name.name_jp == "ValveBiped.Bip01_L_Toe0":
                    # adding IK and such
                    leg_left_obj = retme.bones[index + l_l]
                    leg_left_knee_obj = retme.bones[index + l_k]
                    leg_left_ankle_obj = retme.bones[index + l_a]
                    leg_left_toe_obj = retme.bones[index]
                    leg_right_obj = retme.bones[index + r_l]
                    leg_right_knee_obj = retme.bones[index + r_k]
                    leg_right_ankle_obj = retme.bones[index + r_a]
                    leg_right_toe_obj = retme.bones[index + r_t]

                    leg_left_ankle_pos = leg_left_ankle_obj.pos
                    leg_left_toe_pos = leg_left_toe_obj.pos
                    leg_right_ankle_pos = leg_right_ankle_obj.pos
                    leg_right_toe_pos = leg_right_toe_obj.pos

                    # thisbone = [name_jp, name_en, posX, posY, posZ, parent_idx, deform_layer, deform_after_phys,  # 0-7
                    # 			rotateable, translateable, visible, enabled,  # 8-11
                    # 			tail_type, maybe_tail, inherit_rot, inherit_trans, maybe_inherit, fixed_axis, maybe_fixed_axis,  # 12-18
                    # 			local_axis, maybe_local_axis, external_parent, maybe_external_parent, ik, maybe_ik]  # 19-24

                    leg_left_ik_obj = pmxstruct.PmxBone(leg_left_ik_name, "", leg_left_ankle_pos, index + 5, 0, False,
                                                        True, True, True, True, True,
                                                        False, [0.0, 0.0, 0.0], False, False, False,
                                                        False, False, None, None, None, None, None, None,
                                                        index + l_a, 85, 114.6149,
                                                        [[index + l_k, knee_limit_1, knee_limit_2],
                                                         [index + l_l, None, None]])
                    retme.bones.insert(index + 1, leg_left_ik_obj)

                    leg_left_toe_ik_obj = pmxstruct.PmxBone(leg_left_toe_ik_name, "", leg_left_toe_pos, index + 1, 0,
                                                            False,
                                                            True, True, True, True, True,
                                                            False, [0, 0, 0], False, False, False,
                                                            False, False, None, None, None, None, None, None,
                                                            index, 160, 1, [[index + l_a, None, None]])
                    retme.bones.insert(index + 2, leg_left_toe_ik_obj)

                    leg_right_ik_obj = pmxstruct.PmxBone(leg_right_ik_name, "", leg_right_ankle_pos, index + 5, 0, False,
                                                         True, True, True, True, True,
                                                         False, [0.0, 0.0, 0.0], False, False, False,
                                                         False, False, None, None, None, None, None, None,
                                                         index + r_a, 85, 114.6149,
                                                         [[index + r_k, knee_limit_1, knee_limit_2],
                                                          [index + r_l, None, None]])
                    retme.bones.insert(index + 3, leg_right_ik_obj)

                    leg_right_toe_ik_obj = pmxstruct.PmxBone(leg_right_toe_ik_name, "", leg_right_toe_pos, index + 3, 0,
                                                             False,
                                                             True, True, True, True, True,
                                                             False, [0, 0, 0], False, False, False,
                                                             False, False, None, None, None, None, None, None,
                                                             index + r_t, 160, 1, [[index + r_a, None, None]])
                    retme.bones.insert(index + 4, leg_right_toe_ik_obj)

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

                    # base part
                    pelvis_obj = retme.bones[0]
                    pelvis_pos: list = pelvis_obj.pos
                    print(pelvis_pos)

                    b4_pos = [0, 0, 0]

                    b3_pos = pelvis_pos
                    print(pelvis_pos)
                    print(b3_pos)
                    b3_pos[1] *= .55
                    b2_pos = b3_pos

                    b1_pos = pelvis_pos
                    b1_pos[1] *= .85


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

                    # pop this out for sorting after the loop
                    b1_index = index + 8

            # have to check and add everything before changing the anchor's name
                retme.bones[index].name_jp = big_dict[key]
    # else:
    #     for i in range(0, 4):
    #         retme.bones.insert(0, retme.bones.pop(b1_index))
    #     else:
    #         # fix the idx_parent offset due to pop up there.
    #         for index in range(4, len(retme.bones)):
    #             retme.bones[index].parent_idx += 4

    output_filename_pmx = input_filename_pmx[0:-4] + "_sourcetrans.pmx"
    pmxlib.write_pmx(output_filename_pmx, retme, moreinfo=moreinfo)


if __name__ == "__main__":
    main()
