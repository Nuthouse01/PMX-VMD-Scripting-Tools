### This takes PMX output from Crowbar

finger_dict = {
    "ValveBiped.Bip01_R_Finger4" : "右小指１",
    "ValveBiped.Bip01_R_Finger41" : "右小指２",
    "ValveBiped.Bip01_R_Finger42" : "右小指３",
    "ValveBiped.Bip01_R_Finger3" : "右薬指１",
    "ValveBiped.Bip01_R_Finger31" : "右薬指２",
    "ValveBiped.Bip01_R_Finger32" : "右薬指３",
    "ValveBiped.Bip01_R_Finger2" : "右中指１",
    "ValveBiped.Bip01_R_Finger21" : "右中指２",
    "ValveBiped.Bip01_R_Finger22" : "右中指３",
    "ValveBiped.Bip01_R_Finger1" : "右人指１",
    "ValveBiped.Bip01_R_Finger11" : "右人指２",
    "ValveBiped.Bip01_R_Finger12" : "右人指３",
    "ValveBiped.Bip01_R_Finger0" : "右親指１",
    "ValveBiped.Bip01_R_Finger01" : "右親指２",
    "ValveBiped.Bip01_R_Finger02" : "",  # no bone for the second joint here

    "ValveBiped.Bip01_L_Finger4" :	"左小指１",
    "ValveBiped.Bip01_L_Finger41" :	"左小指２",
    "ValveBiped.Bip01_L_Finger42" :	"左小指３",
    "ValveBiped.Bip01_L_Finger3" :	"左薬指１",
    "ValveBiped.Bip01_L_Finger31" :	"左薬指２",
    "ValveBiped.Bip01_L_Finger32" :	"左薬指３",
    "ValveBiped.Bip01_L_Finger2" :	"左中指１",
    "ValveBiped.Bip01_L_Finger21" :	"左中指２",
    "ValveBiped.Bip01_L_Finger22" :	"左中指３",
    "ValveBiped.Bip01_L_Finger1" :	"左人指１",
    "ValveBiped.Bip01_L_Finger11" :	"左人指２",
    "ValveBiped.Bip01_L_Finger12" :	"左人指３",
    "ValveBiped.Bip01_L_Finger0" :	"左親指１",
    "ValveBiped.Bip01_L_Finger01" :	"左親指２",
    "ValveBiped.Bip01_L_Finger02" : ""
}

arm_dict = {
    "ValveBiped.Bip01_R_Clavicle" :	"右肩",
    "ValveBiped.Bip01_R_UpperArm" :	"右腕",
    "ValveBiped.Bip01_R_Forearm" :	"右ひじ",
    "ValveBiped.Bip01_R_Hand" :	"右手捩",

    "ValveBiped.Bip01_L_Clavicle" :	"左肩",
    "ValveBiped.Bip01_L_UpperArm" :	"左腕",
    "ValveBiped.Bip01_L_Forearm" :	"左ひじ",
    "ValveBiped.Bip01_L_Hand" :	"左手捩"
}

leg_dict = {
    "ValveBiped.Bip01_R_Thigh" :	"左足", 
    "ValveBiped.Bip01_R_Calf" :	"左ひざ", 
    "ValveBiped.Bip01_R_Foot" :	"左足首", 
    "ValveBiped.Bip01_R_Toe0" :	"右つま先",

    "ValveBiped.Bip01_L_Thigh" :	"右足", 
    "ValveBiped.Bip01_L_Calf" :	"右ひざ", 
    "ValveBiped.Bip01_L_Foot" :	"右足首",
    "ValveBiped.Bip01_L_Toe0" :	"左つま先"
}

body_dict = {
    "ValveBiped.Bip01_Pelvis" :	"センター",
    "ValveBiped.Bip01_Spine" :	"下半身",
    "ValveBiped.Bip01_Spine1" :	"上半身",
    "ValveBiped.Bip01_Spine2" :	"上半身2",
    "ValveBiped.Bip01_Spine4" :	"首",  # this is at the base of the neck, we can combine it
    "ValveBiped.Bip01_Neck1" :	"首",
    "ValveBiped.Bip01_Head1" :	"頭"

    # "腰" is parent of _Spine most of the times, then "グルーブ" and "センター" and "全ての親"
    # more testing I guess?
}