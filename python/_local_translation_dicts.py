
# this file simply contains commonly-used translation data
# most of these copied from PMXE's translation dict

# comments are what PMXE builtin translate actually translates them to, but i don't like those names

# NOTE: as of python 3.6, the order of dictionary items IS GUARANTEED. but before that it is not guaranteed.

# NEW: attempt piece-wise translation of the jp names!! (at bottom)

########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
# exact match dicts for semistandard or common bones

morph_dict = {
"▲": "^ open",
"△": "^ open2",
"∧": "^",
"ω": "w", # "omega"
"ω□": "w open",
"まばたき": "blink",
"笑い": "happy", # "smile"
"ウィンク": "wink",
"ウィンク右": "wink_R",
"ウィンク２": "wink2",
"ｳｨﾝｸ２右": "wink2_R",
"ウィンク２右": "wink2_R",
"ジト目": "doubt",
"じと目": "doubt",
"なごみ": "=.=", # "calm"
"びっくり": "surprise",
"驚き": "surprise",
"悲しい": "sad low",
"困る": "sadness",
"真面目": "serious",
"怒り": "anger",
"にこり": "cheerful",
"星目": "star eyes",
"しいたけ": "star eyes", # "shiitake"
"ハート目": "heart eyes",
"ハート": "heart eyes",
"ぐるぐる": "spinny eyes",
"笑い目": "happy eyes",
"カメラ目": "camera eyes", # for looking at the camera
"はぅ": ">.<",
"にやり": "grin",
"ニヤリ": "grin",  # these 2 are phonetically the same, "niyari"
"にっこり": "smile",
"ムッ": "upset",
"照れ": "blush", # "little blush"
"照れ２": "blush2", # "big blush"
"青ざめ": "pale", # literally "aozame"
"青ざめる": "pale",
"丸目": "O.O",
"はちゅ目": "O.O",
"はちゅ目縦潰れ": "O.O height",
"はちゅ目横潰れ": "O.O width",
"ハイライト消し": "highlight off",
"瞳小": "pupil small", # "pupil"
"恐ろしい子！": "white eye", # literally "scary child!" who the hell thought that was a good name?
"あ": "a",
"い": "i",
"う": "u",
"え": "e",
"お": "o",
"ワ": "wa",
"わ": "wa",
"□": "box",
"上": "brow up", # "go up"
"下": "brow down", # "go down"
"前": "brow fwd",
"涙": "tears",
"ん": "hmm", # wtf is this translation
}

bone_dict =  {
"操作中心": "view cnt",
"全ての親": "motherbone",
"センター": "center",
"グルーブ": "groove",
"腰": "waist",
"右足IK親": "leg IKP_R",
"右足ＩＫ": "leg IK_R",
"右つま先ＩＫ": "toe IK_R",
"左足IK親": "leg IKP_L",
"左足ＩＫ": "leg IK_L",
"左つま先ＩＫ": "toe IK_L",
"上半身": "upper body",
"上半身2": "upper body2",
"下半身": "lower body",
"首": "neck",
"頭": "head",
"右肩P": "shoulder_raise_R", # "raise shoulder_R"
"右肩": "shoulder_R",
"右肩C": "shoulder_hidden_R",
"右腕": "arm_R",
"右腕ＩＫ": "armIK_R",
"右腕捩": "arm twist_R",
"右腕捩1": "arm twist1_R", # "right arm rig1"
"右腕捩2": "arm twist2_R", # "right arm rig2"
"右腕捩3": "arm twist3_R", # "right arm rig3"
"右ひじ": "elbow_R",
"右手捩": "wrist twist_R",
"右手捩1": "wrist twist1_R", # "right elbow rig1"
"右手捩2": "wrist twist2_R", # "right elbow rig2"
"右手捩3": "wrist twist3_R", # "right elbow rig3"
"右手首": "wrist_R",
"右手先": "wrist_end_R",
"右ダミー": "dummy_R",
"右親指０": "thumb0_R",
"右親指１": "thumb1_R",
"右親指２": "thumb2_R",
"右親指先": "thumb_end_R",
"右小指１": "little1_R",
"右小指２": "little2_R",
"右小指３": "little3_R",
"右小指先": "little_end_R",
"右薬指１": "third1_R",
"右薬指２": "third2_R",
"右薬指３": "third3_R",
"右薬指先": "third_end_R",
"右中指１": "middle1_R",
"右中指２": "middle2_R",
"右中指３": "middle3_R",
"右中指先": "middle_end_R",
"右人指１": "fore1_R",
"右人指２": "fore2_R",
"右人指３": "fore3_R",
"右人指先": "fore_end_R",
"左肩P": "shoulder_raise_L", # "raise shoulder_L"
"左肩": "shoulder_L",
"左肩C": "shoulder_hidden_L",
"左腕": "arm_L",
"左腕ＩＫ": "armIK_L",
"左腕捩": "arm twist_L",
"左腕捩1": "arm twist1_L", # "left arm rig1"
"左腕捩2": "arm twist2_L", # "left arm rig2"
"左腕捩3": "arm twist3_L", # "left arm rig3"
"左ひじ": "elbow_L",
"左手捩": "wrist twist_L",
"左手捩1": "wrist twist1_L", # "left elbow rig1"
"左手捩2": "wrist twist2_L", # "left elbow rig2"
"左手捩3": "wrist twist3_L", # "left elbow rig3"
"左手首": "wrist_L",
"左手先": "wrist_end_L",
"左ダミー": "dummy_L",
"左親指０": "thumb0_L",
"左親指１": "thumb1_L",
"左親指２": "thumb2_L",
"左親指先": "thumb_end_L",
"左小指１": "little1_L",
"左小指２": "little2_L",
"左小指３": "little3_L",
"左小指先": "little_end_L",
"左薬指１": "third1_L",
"左薬指２": "third2_L",
"左薬指３": "third3_L",
"左薬指先": "third_end_L",
"左中指１": "middle1_L",
"左中指２": "middle2_L",
"左中指３": "middle3_L",
"左中指先": "middle_end_L",
"左人指１": "fore1_L",
"左人指２": "fore2_L",
"左人指３": "fore3_L",
"左人指先": "fore_end_L",
"右目": "eye_R",
"左目": "eye_L",
"両目": "eyes",
"メガネ": "glasses",
"眼鏡": "glasses",
"腰キャンセル右": "waist_cancel_R",
"腰キャンセル左": "waist_cancel_L",
"右足": "leg_R",  # standard leg-bones
"右ひざ": "knee_R",
"右足首": "foot_R",
"右つま先": "toe_R",
"左足": "leg_L",
"左ひざ": "knee_L",
"左足首": "foot_L",
"左つま先": "toe_L",
"右足D": "leg_RD",      # "right thigh_D"
"右ひざD": "knee_RD",   # "right knee_D"
"右足首D": "foot_RD",   # "right foot_D"
"右足先EX": "toe_R EX", # "right toes_EX"
"左足D": "leg_LD",      # "left thigh_D"
"左ひざD": "knee_LD",   # "left knee_D"
"左足首D": "foot_LD",   # "left foot_D"
"左足先EX": "toe_L EX", # "left toes_EX"
"胸": "breast",
"胸親": "breast_ctrl",
"おっぱい調整": "breast_adjust",
"左胸": "breast_L",
"右胸": "breast_R",
"乳": "breast",  # chinese symbol for breast, sometimes used
"左乳": "breast_L",
"右乳": "breast_R",
}

frame_dict = {
"センター": "Center",
"ＩＫ": "IK",
"体(上)": "Upper Body",
"髪": "Hair",
"腕": "Arms",
"指": "Fingers",
"体(下)": "Lower Body",
"足": "Legs",
"スカート": "Skirt",
"その他": "Other",
"服": "Clothes",
"ケープ": "Cape",
"外套": "Mantle",
"握り・拡散": "Grip / Spread",
}


########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
# partial-match dicts for piecewise translation

words_dict = {
# words
"モーフ": "morph",
"ネクタイ": "necktie",
"スカーフ": "scarf",
"スカート": "skirt",
"ｽｶｰﾄ": "skirt",
"ﾄﾞﾚｽ": "dress",
"ドレス": "dress",
"リボン": "ribbon",
"ワンピース": "one-piece", # as in a one-piece dress
"ピン": "pin",
"シャツ": "shirt",
"パンティー" : "panties",
"パンツ": "panties",
"ﾊﾟﾝﾂ": "panties",
"ぱんつ": "panties",
"ビキニ": "bikini",
"もみあげ": "sideburn",
"尻尾": "tail",
"おっぱい": "boobs", # literally "oppai"
"ヘッドセット": "headset",
"センター": "center",
"グルーブ": "groove",
"タイツ": "tights",
"あほ毛": "ahoge", # the cutesy little hair curl on top
"アホ毛": "ahoge",
"腰": "waist",
"舌": "tongue",
"胸": "breast",
"乳": "breast",
"ブラ": "bra",
"耳": "ear",
"みみ": "ear",
"ヘアー": "hair",
"髪の毛": "hair", # this literally means hair of hair??? odd
"毛": "hair",
"髪": "hair",
"髮": "hair", # this is actually somehow different from the line above???
"ヘア": "hair",
"新規": "new",
"材質": "material",
"なみだ": "tears",
"尻": "butt",
"目": "eye",
"瞳": "pupil",
"着地": "landing",
"水着": "swimsuit",
"服": "clothes",
"着": "clothes",
"ケープ": "cape",
"外套": "mantle",
"物理": "phys",
"カット": "cut",
"切る": "cut",
"飾り": "decoration", # either decoration or ornament
"補助": "helper",
"ブロック": "block", # literally burroku, not sure why he picked this name
"花": "flower",
"鳥": "bird",
"弓": "bow",
"その他": "other",
"他": "other",
"ハイライト": "highlight",
"ﾊｲﾗｲﾄ": "highlight",
"靴": "shoe",
"くつ": "shoe",
"顔": "face",
"足首": "foot",  # this must be high priority, otherwise its components will be individually (wrongly) translated
"手首": "wrist",  # this must be high priority, otherwise its components will be individually (wrongly) translated
"足": "leg",
"脚部": "leg",
"脚": "leg",
"腿": "thigh",
"手袋": "glove",
"グローブ": "glove",
"ベルト": "belt",
"手": "hand",
"首": "neck",
"親指": "thumb",  # this must be high priority, otherwise its components will be individually (wrongly) translated
"人差指": "fore",  # this must be high priority, otherwise its components will be individually (wrongly) translated
"人指": "fore",  # this must be high priority, otherwise its components will be individually (wrongly) translated
"中指": "middle",  # this must be high priority, otherwise its components will be individually (wrongly) translated
"薬指": "third",  # this must be high priority, otherwise its components will be individually (wrongly) translated
"小指": "little",  # this must be high priority, otherwise its components will be individually (wrongly) translated
"指": "finger",
"ひざ": "knee",
"膝": "knee",
"つま先": "toe",
"肩": "shoulder",
"腕": "arm",
"ひじ": "elbow",
"ヒジ": "elbow",
"腹黒": "dark",
"腹部": "abdomen",
"腹": "belly",
"頭": "head",
"帽子": "hat",
"金属": "metal",
"紐": "string",  # or cord
"ダミー": "dummy",
"ﾀﾞﾐ": "dummy",
"半": "half",
"身": "body",
"体": "body",
"ボディ": "body",
"肌": "skin",
"裙": "skirt",
"輪": "round",
"武器": "weapon",
"釦": "button",
"連動": "interlock",
"捩": "twist",
"捻り": "twist",
"メガネ": "glasses",
"眼鏡": "glasses",
"星": "star",
"パーツ": "parts",
"筋": "muscle",
"帶": "band",
"そで": "sleeve",
"袖": "sleeve",
"歯": "teeth",
"牙": "fang",
"犬": "dog",
"猫": "cat",
"ねこ": "cat",
"獣": "animal",
"口": "mouth",
"まぶた": "eyelid",
"瞼": "eyelid",
"睫毛": "eyelash",
"睫": "eyelash",
"よだれ": "drool",
"眉毛": "brow",
"眉": "brow",
"光": "light",
"影": "shadow",
"鼻": "nose",
"表情": "expression",
"襟": "collar",
"頂点": "vertex",
"式": "model",
"甲": "armor",
"鎧": "armor",
"胴": "torso",


# modifiers
"先": "end",
"親": "parent",
"中": "mid",
"右": "right",
"左": "left",
"上げ": "raise", # motion
"下げ": "lower", # motion
"上": "upper", # relative position
"下": "lower", # relative position
"前": "front",
"フロント": "front",
"後ろ": "back", # not sure about this one
"背": "back",
"裏": "back",
"後": "rear",
"后": "rear",
"横": "side", # or horizontal
"縦": "vert",
"両": "both",
"内": "inner",
"外": "outer",
"角": "corner",
"法線": "normal",
"調整": "adjust",
"出し": "out", # out as in takeout???
"全": "all",
"・": "-",
"握り": "grip",
"握": "grip",
"拡散": "spread",
"拡": "spread",
"基": "base", # either group or base

# morphs
"ずらし": "shift",
"短": "short",
"長": "long",
"穏やか": "calm",
"螺旋": "spiral",
"回転": "rotate",
"移動": "move",
"食込無": "none",
"無し": "none",
"なし": "none",
"消えて": "disappear", # as in whole model disappear
"消える": "disappear", 
"透明": "transparent",
"広げ": "wide", # literally "spread"
"広い": "wide",
"広": "wide",
"潰れ": "shrink",  # literally "collapse"
"狭": "narrow",
"細": "thin",  # literally "fine"
"粗": "coarse",
"大": "big",
"巨": "big",
"暗い": "dark",
"黒": "black",
"青ざめ": "pale",
"白": "white",
"を隠す": "hide",
"非表示": "hide",
"追従": "follow",
"開く": "open",
"開け": "open",
"まばたき": "blink",
"笑い": "happy",
"ウィンク": "wink",
"ｳｨﾝｸ": "wink",
"睨み": "glare",
"ｷﾘｯ": "kiri", # not sure what this means
"ジト": "doubt", # jito
"じと": "doubt", # jito
"なごみ": "=.=", # "calm"
"びっくり": "surprise",
"驚き": "surprise",
"悲しい": "sad low",
"困る": "sadness",
"真面": "serious",
"怒り": "anger",
"怒": "anger",
"にこり": "cheerful",
"しいたけ": "star", # "shiitake"
"ハート": "heart",
"はぁと": "heart",
"ぐるぐる": "dizzy", # perhaps "spinny"
"グルグル": "dizzy", # perhaps "spinny"
"カメラ": "camera", # for looking at the camera
"はぅ": ">.<",
"にやり": "grin",
"にっこり": "smile",
"ムッ": "upset",
"照れ": "blush",
"赤面": "blush",
"黄": "yellow",
"赤": "red",
"蒼": "blue",
"金": "gold",
"銀": "silver",
"汗": "sweat",
"円": "circle",
"表": "front", # not sure about this one, front as in outward-facing geometry, opposite of backward-facing geometry. literally means "table" tho lol
"縁": "edge",
"丸": "round",
"はちゅ": "round",
"縮小": "small",
"小さく": "small",
"小": "small",
"消し": "erase",
"けし": "erase",
"消": "erase",
"裸": "bare", # or "naked" like bare legs
"あ": "a",
"ア": "a",
"い": "i",
"う": "u",
"え": "e",
"お": "o",
"ワ": "wa",
"わ": "wa",
"□": "box",
"涙": "tears",
"ん": "hmm",
"ω": "w", # "omega"
"○": "o",
"▲": "^ open",
"△": "^ open2",
"∧": "^",
"の": "of", # technically "A の B" translates more closely to "B of A" but I can't do that switcheroo without major changes
"ー": "--", # not sure what to do with this, often used to mean continuation of a sound/syllable...
"┗": "  ", # indentation for structure
"└": "  ",
}


# these get appended to the end instead of being replaced in order
prefix_dict = {
"中": "_M",
"右": "_R",
"左": "_L",
}


########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
# functions


TRANSLATE_JOINCHAR = ' '

DEBUG = False

# use the local dicts defined here to attempt intelligent translation without going to Google
# returns its best translation attempt, even if unsuccessful/incomplete
# takes JP string as input, assumes I have already checked for the case where JP name is already only english (copyable)
def translate_local(s: str) -> (None, str):
	if (not s) or s.isspace():
		return "NULL"
	# stage 1: look for exact matches
	for (key, val) in morph_dict.items():
		if s == key:
			if DEBUG:
				print("_ :: %s :: %s" % (s, val))
			return val
	for (key, val) in bone_dict.items():
		if s == key:
			if DEBUG:
				print("_ :: %s :: %s" % (s, val))
			return val
	for (key, val) in frame_dict.items():
		if s == key:
			if DEBUG:
				print("_ :: %s :: %s" % (s, val))
			return val
	
	# stage 2: fullwidth replacement, result might be unchanged
	# fullwidth chars like ０１２３ＩＫ are in range FF01–FF5E  and correspond to  21-7E, diff=(FEE0/‭65248‬)
	# to handle them, str[1] > ord() > ascii# > -0xfee0 > ascii# > chr() > str[1]
	out = ""
	for c in s:  # for each char c in string s,
		o = ord(c)  # get ascii value
		if 0xff01 <= o <= 0xff5e:  # if this is a fullwidth char,
			out += chr(o - 0xfee0)  # map it down to the normal version & append
		elif o == 0x3000: # if this is an "ideographic space" aka fullwidth space
			out += " "
		else:  # otherwise,
			out += c  # append the unmodified char
	
	# stage 3: left/right/mid replacement
	# turn the JP prefix into an EN suffix
	for (key, val) in prefix_dict.items():
		if out[0] == key:
			# rebuild the string minus the prefix plus the suffix
			out = out[1:] + val
			# only one prefix, don't check more
			break
	
	# stage 4: word replacement
	# goal: substrings that match keys of "words_dict" get replaced
	# BUT, ONLY adjacent substring replacements are separated by JOINCHAR
	# no JOINCHAR between replacement and english text
	for (key, val) in words_dict.items():
		begin = 0
		# while-loop is here to apply all instances of this translation
		while begin != -1:
			begin = out.find(key)
			if begin != -1:  # if it finds a match,
				newtrans = val
				# i am going to replace it, but first see if i need to put JOINCHAR before or after
				# the char after is begin+len(key) and the char before is begin-1
				# add JOINCHAR if the index exists and is not already a  "separator" text char: space,._-/
				if begin != 0 and out[begin-1] not in " ,._-/":  # can i put JOINCHAR at the start of the string
					newtrans = TRANSLATE_JOINCHAR + newtrans
				if begin+len(key) != len(out) and out[begin+len(key)] not in " ,._-/":  # can i put JOINCHAR at the end of the string
					newtrans = newtrans + TRANSLATE_JOINCHAR
				# now JOINCHAR is added, so now i substitute
				out = out[:begin] + newtrans + out[begin+len(key):]
	
	# pretty much done!
	if DEBUG:
		# did i translate the whole thing? check whether results are all "normal" characters
		complete = True
		for c in out:
			if ord(c) > 0x7f:
				complete = False
				break
		print("%d :: %s :: %s" % (complete, s, out))
	# return what it produced, even if not completely successful
	return out

# import nuthouse01_core as core
# import nuthouse01_pmx_parser as pmxlib
# import _translate_to_english
#
# def main():
# 	input_filename_pmx = core.prompt_user_filename(".pmx")
# 	pmx = pmxlib.read_pmx(input_filename_pmx)
#
# 	matnames = [x[0] for x in pmx[4]]
# 	bonenames = [x[0] for x in pmx[5]]
# 	morphnames = [x[0] for x in pmx[6]]
# 	dispnames = [x[0] for x in pmx[7]]
#
# 	numpass = 0
#
# 	print("")
# 	print("="*50)
# 	print("MATERIALS", len(matnames))
# 	print("="*50)
# 	for n in matnames:
# 		if not _translate_to_english.contains_jap_chars(translate_local(n)):
# 			numpass += 1
# 	print("")
# 	print("="*50)
# 	print("BONES", len(bonenames))
# 	print("="*50)
# 	for n in bonenames:
# 		if not _translate_to_english.contains_jap_chars(translate_local(n)):
# 			numpass += 1
# 	print("")
# 	print("="*50)
# 	print("MORPHS", len(morphnames))
# 	print("="*50)
# 	for n in morphnames:
# 		if not _translate_to_english.contains_jap_chars(translate_local(n)):
# 			numpass += 1
# 	print("")
# 	print("="*50)
# 	print("DISPFRAME", len(dispnames))
# 	print("="*50)
# 	for n in dispnames:
# 		if not _translate_to_english.contains_jap_chars(translate_local(n)):
# 			numpass += 1
#
# 	numtotal = len(matnames) + len(bonenames) + len(morphnames) + len(dispnames)
#
# 	print("Able to locally translate {} / {} = {:.1%} JP names".format(
# 		numpass, numtotal, numpass / numtotal))
#
# if __name__ == '__main__':
# 	core.MY_PRINT_FUNC("Nuthouse01 - 04/17/2020 - v4.04")
# 	main()
#
