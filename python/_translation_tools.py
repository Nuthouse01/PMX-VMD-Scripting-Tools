
# this file simply contains commonly-used translation data
# most of these copied from PMXE's translation dict

# comments are what PMXE builtin translate actually translates them to, but i don't like those names

# NOTE: as of python 3.6, the order of dictionary items IS GUARANTEED. but before that it is not guaranteed.
# and it is very, very important to how the translator functions.
# NOTE: filtering stage means that all exact-match dicts should NOT contain fullwidth latin letters/numbers.

########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################

import re
from typing import List, Union, Tuple

# this dict is added to both "words" and "morphs"... just in one place so I can keep thing straight
symbols_dict = {
"╱": "/",  # x2571 "box drawing" section.
"╲": "\\",  # x2572 "box drawing" section. NOTE backslash isn't MMD supported, find something better!
"╳": "X",  # x2573 "box drawing" section.
"×": "x",  # x0215 multiply symbol
"↑": "^", # x2191, NOTE: backslashes work poorly so /\ doesn't work right
"↓": "v", # x2193, NOTE: backslashes work poorly so \/ doesn't work right
"→": "->", # x2192
"←": "<-", # x2190
"ω": "w", # "omega"
"□": "box",  #x25a1
"■": "box",  #x25a0   less common than above
"▲": "^ open",  #x25b2
"△": "^ open",  #x25b3   less common than above
"∧": "^",  #x2227 "logical and"
"∨": "V",  #x2228 "logical or"
"〜": "~",  # x301C wave dash, not a "fullwidth tilde"
"○": "O",  #x25cb
"◯": "O",  #x25ef
"〇": "O",  # x3007
}


# searched for exact matches because many of these names break translation rules
morph_dict = {
"ω□": "w open",  # without this entry it translates to "w box", and i dont like that
"まばたき": "blink",
"笑い": "happy", # pmxe translates to "smile" but this is an eye morph
"ウィンク": "wink",
"ウィンク2": "wink2",
"ウィンク右2": "wink2_R",
"ｳｨﾝｸ": "wink",
"ｳｨﾝｸ2": "wink2",
"ｳｨﾝｸ右2": "wink2_R",
"ジト目": "doubt",
"じと目": "doubt",
"なごみ": "=.=", # "calm"
"びっくり": "surprise",
"驚き": "surprise",
"見開き": "wide eye",
"悲しい": "sad low",
"困る": "sadness",  # google translates to "troubled", but PMXE translates to "sadness"... maybe "worried" is best?
"困った": "sadness",  # same as above
"動揺": "upset",
"真面目": "serious",  # has the symbol for "eye" but is actually a brow morph, odd
"怒り": "anger",
"にこり": "cheerful",
"ｷﾘｯ": "serious eyes", # phonetically "kiri-tsu", might informally mean "confident"? kinda a meme phrase, a professional model translated this to 'serious' tho so idk
"星目": "star eyes",
"しいたけ": "star eyes", # "shiitake"
"ハート目": "heart eyes",
"ハート": "heart eyes",
"ぐるぐる": "dizzy eyes", # perhaps "spinny"
"ぐる": "dizzy eyes", # perhaps "spinny"
"グルグル": "dizzy eyes", # perhaps "spinny"
"グル": "dizzy eyes", # perhaps "spinny"
"笑い目": "happy eyes",
"カメラ目": "camera eyes", # for looking at the camera
"ｺｯﾁﾐﾝﾅ": "camera eyes",  # phonetically "Kotchiminna", might informally translate to "this guy" or "everyone" i guess? functionally same as "camera eyes" tho
"こっちみんな": "camera eyes", # phonetically "Kotchiminna", google translates to "don't look at me" maybe like "not my fault"?
"はぅ": ">.<",
"にやり": "grin",
"ニヤリ": "grin",  # these 2 are phonetically the same, "niyari"
"にっこり": "smile",  # phonetically "nikkori"
"スマイル": "smile",  # phonetically "sumairu" aka engrish for "smile"
"ムッ": "upset",
"照れ": "blush",  # "little blush", literally "shy"
"照れ2": "blush2",  # "big blush", literally "shy"
"照れ屋": "blush",  # another blush, literally "shy"
"赤面": "blush",  # literally "red face" but its just another blush
"青ざめる": "shock", # literally "aozomeru", translates to "pale", but the expression it represents is shock/horror
"青ざめ": "shock", # literally "aozame" translates to "pale", but the expression it represents is shock/horror
"丸目": "O.O",
"はちゅ目": "O.O",
"はちゅ目縦潰れ": "O.O height",
"はちゅ目横潰れ": "O.O width",
"ハイライト消し": "highlight off",
"瞳小": "pupil small", # "pupil"
"恐ろしい子!": "white eye", # literally "scary child!" who the hell thought that was a good name?
"ぺろっ": "tongue out",  # phonetically "perrow"
"べー": "beeeeh", # another way of doing "tongue out" but google likes to turn this into 'base'
"あ": "a",
"い": "i",
"う": "u",
"え": "e",
"お": "o",
"ワ": "wa",
"わ": "wa",
"上": "brow up", # "go up"
"下": "brow down", # "go down"
"前": "brow fwd",
"涙": "tears",
"ん": "hmm", # wtf is this translation
"ー": "--", # not sure what to do with this, often used to mean continuation of a sound/syllable...
}

# add the symbols into the morph dict
morph_dict.update(symbols_dict)


# searched for exact matches because many of these break piecewise translation rules
bone_dict =  {
"操作中心": "view cnt",
"全ての親": "motherbone",
"センター": "center",
"グルーブ": "groove",
"腰": "waist",
"足IK": "leg IK",
"つま先IK": "toe IK",
"上半身": "upper body",
"上半身2": "upper body2",
"下半身": "lower body",
"首": "neck",
"頭": "head",
"肩P": "shoulder_raise",  # "raise shoulder"
"肩": "shoulder",
"肩C": "shoulder_cancel",  # alternately "shoulder hidden"
"腕": "arm",
"腕IK": "armIK",
"腕捩": "arm twist",
"腕捩1": "arm twist1",  # "left arm rig1"
"腕捩2": "arm twist2",  # "left arm rig2"
"腕捩3": "arm twist3",  # "left arm rig3"
"ひじ": "elbow",
"手捩": "wrist twist",
"手捩1": "wrist twist1",  # "left elbow rig1"
"手捩2": "wrist twist2",  # "left elbow rig2"
"手捩3": "wrist twist3",  # "left elbow rig3"
"手首": "wrist",
"ダミー": "dummy",
"親指0": "thumb0",
"親指1": "thumb1",
"親指2": "thumb2",
"小指1": "little1",
"小指2": "little2",
"小指3": "little3",
"薬指1": "third1",
"薬指2": "third2",
"薬指3": "third3",
"中指1": "middle1",
"中指2": "middle2",
"中指3": "middle3",
"人指1": "fore1",
"人指2": "fore2",
"人指3": "fore3",
"目": "eye",
"両目": "eyes",  # literally "both eyes"
"メガネ": "glasses",
"眼鏡": "glasses",
"腰キャンセル": "waist_cancel",
"足": "leg",  # standard leg-bones
"ひざ": "knee",
"足首": "foot",  # "ankle" is technically a more accurate translation but w/e this is standard name
"つま先": "toe",
"足D": "leg_D",      # "left/right thigh_D"
"ひざD": "knee_D",   # "left/right knee_D"
"足首D": "foot_D",   # "left/right foot_D"
"足先EX": "toe_EX", # "left/right toes_EX"
"胸": "breast",  # translates to "chest" or "breast"
"乳": "breast",  # translates to "breast" or "milk"??? idk man language is wierd
}

# these should be nicely capitalized
frame_dict = {
"センター": "Center",
"ＩＫ": "IK",
"IK": "IK",
"体(上)": "Upper Body",
"髪": "Hair",
"腕": "Arms",
"指": "Fingers",
"体(下)": "Lower Body",
"足": "Legs",
"つま先": "Toes",
"スカート": "Skirt",
"その他": "Other",
"物理": "Physics",
"物理-その他": "Physics - Other",
"その他-物理": "Other - Physics",
"服": "Clothes",
"猫耳": "Nekomimi",
"ねこ耳": "Nekomimi",
"獣耳": "Kemonomimi",
"ケープ": "Cape",
"外套": "Mantle",
"握り・拡散": "Grip / Spread",
"握り-拡散": "Grip / Spread",
}


########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
# partial-match dicts for piecewise translation

words_dict = {
# words
"操作中心": "view cnt",
"全ての親": "motherbone",
"モーフ": "morph",
"ネクタイ": "necktie",
"スカーフ": "scarf",
"マフラー": "scarf",  # actually "muffler" but a muffler is basically a scarf
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
"ｺｯﾁﾐﾝﾅ": "camera eyes",  # phonetically "Kotchiminna", might informally translate to "this guy" or "everyone" i guess? functionally same as "camera eyes" tho
"こっちみんな": "camera eyes",  # phonetically "Kotchiminna", google translates to "don't look at me" maybe like "not my fault"?
"尻尾": "tail",
"おっぱい": "boobs",  # literally "oppai"
"ヘッドセット": "headset",
"ヘッドホン": "headphone",  # phonetically "heddoHon"
"ヘッドフォン": "headphone",  # phonetically "heddoFon"
"センター": "center",
"グルーブ": "groove",
"上半身": "upper body",
"下半身": "lower body",
"タイツ": "tights",
"あほ毛": "ahoge",  # the cutesy little hair curl on top
"アホ毛": "ahoge",
"腰": "waist",
"舌": "tongue",
"胸": "breast",  # translates to "chest" or "breast"
"乳": "breast",  # translates to "breast" or "milk"??? idk man language is wierd
"乳首": "nipple",
"乳輪": "areola",
"ブラ": "bra",
"耳": "ear",  # phonetically "mimi"
"みみ": "ear",  # phonetically "mimi"
"閉じ": "close",
"開く": "open",
"開け": "open",
"開き": "open",
"髪の毛": "hair", # this literally means hair of hair??? odd
"毛": "hair",
"髪": "hair",
"髮": "hair", # this is actually somehow different from the line above???
"ヘアー": "hair",
"ヘア": "hair",
"新規": "new",
"材質": "material",
"尻": "butt",
"鎖": "chain",
"目": "eye",
"眼": "eye",
"瞳": "pupil",
"瞳孔": "pupil",
"着地": "landing",
"水着": "swimsuit",
"服": "clothes",
"着": "clothes",
"衣": "clothes",  # this one is chinese? maybe?
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
"弓": "bow",  # as in bowtie not as in bending at the waist
"その他": "other",
"他": "other",
"ハイライト": "highlight",
"ﾊｲﾗｲﾄ": "highlight",
"艶": "gloss",
"靴": "shoe",  # phonetically "kutsu"
"くつ": "shoe",  # phonetically "kutsu"
"顔": "face",
"額": "forehead",
"ほほ": "cheek",  # phonetically "hoho"
"頬": "cheek",  # phonetically "hoho"
"あご": "chin",
"顎": "chin",
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
"親指": "thumb",
"人差指": "fore",
"人指": "fore",
"中指": "middle",
"薬指": "third",
"小指": "little",
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
"裙": "skirt",  # chinese for "skirt"
"輪": "ring",  # was "round", better translation is ring/loop/circle maybe?
"武器": "weapon",
"ボタン": "button",  # phonetically "botan"
"釦": "button",  # phonetically "botan"
"連動": "interlock",
"捩": "twist",
"捻り": "twist",
"メガネ": "glasses",  # phonetically "megane"
"眼鏡": "glasses",  # phonetically "megane"
"星": "star",
"パーツ": "parts",
"筋": "muscle",
"帶": "band",
"そで": "sleeve",
"袖": "sleeve",
"歯": "teeth",
"牙": "fang",
"爪": "nail",
"犬": "dog",
"猫": "cat",  # phonetically "neko"
"ねこ": "cat",  # phonetically "neko"
"獣": "animal",
"くち": "mouth",  # phonetically "kuchi"
"口": "mouth",  # phonetically "kuchi"
"唇": "lip",
"まぶた": "eyelid",  # phonetically "mabuta"
"瞼": "eyelid",  # phonetically "mabuta"
"まつげ": "eyelash",  # phonetically "matsuge"
"睫毛": "eyelash",  # phonetically "matsuge"
"睫": "eyelash",  # also somehow "matsuge"
"よだれ": "drool",
"まゆ": "brow",
"眉毛": "brow",
"眉": "brow",
"発光": "glow",
"発": "emit",
"光": "light",
"かげ": "shadow",  # phonetically "kage"
"影": "shadow",  # phonetically "kage"
"鼻": "nose",
"表情": "expression",
"襟": "collar",
"頂点": "vertex",
"テクスチャ": "texture",
"骨": "bone",
"式": "model",
"甲": "armor",
"鎧": "armor",
"胴": "torso",
"マーク": "mark",
"ﾏｰｸ": "mark",
"ネック": "neck",
"ｽｰﾂ": "suit",
"スーツ": "suit",
"フード": "hood",  # phonetically "fudo" so it could mean "food" but more models will have sweatshirts with hoods than will have food
"支": "support",


# modifiers
"先": "end",
"親": "parent",
"中": "mid",
"右": "right",
"左": "left",
"上げ": "raise",  # motion
"下げ": "lower",  # motion
"上": "upper",  # relative position
"下": "lower",  # relative position
"前": "front",
"フロント": "front",
"後ろ": "back",  # not sure about this one
"背": "back",
"裏": "back",
"後": "rear",
"后": "rear",
"横": "side",  # or horizontal
"縦": "vert",
"両": "both",
"内": "inner",
"外": "outer",
"角": "corner",
"法線": "normals",  # normals as in vertex normals not normal as in ordinary, i think?
"調整": "adjust",
"出し": "out",  # out as in takeout???
"全": "all",
"握り": "grip",
"握": "grip",
"拡散": "spread",
"拡": "spread",
"基部": "base",
"基": "base",  # either group or base
"錘": "weight",
"操作": "control",  # more closely translates to "operation" but w/e
"制御": "control",
"特殊": "special",

# morphs
"ジグザグ": "zigzag",
"ぺろっ": "tongue out",  # phonetically "perrow"
"べー": "beeeeh",  # another way of doing "tongue out"
"持ち": "hold",  # perhaps grab? holding? 手持ち = handheld
"ずらし": "shift",
"短": "short",
"長": "long",

"穏やか": "calm",
"螺旋": "spiral",
"回転": "rotate",
"移動": "move",
"動": "motion",
"食込無": "none",
"無し": "none",
"なし": "none",  # phonetically "nashi"
"ナシ": "none",  # phonetically "nashi"
"无": "none",
"消えて": "disappear", # as in whole model disappear
"消える": "disappear", 
"透明": "transparent",
"透過": "transparent",
"広げ": "wide", # literally "spread"
"広い": "wide",
"広": "wide",
"潰れ": "shrink",  # literally "collapse"
"狭く": "narrow",
"狭": "narrow",
"幅": "width",
"細い": "thin",
"細": "thin",  # literally "fine"
"太": "thick",
"粗": "coarse",
"逆": "reverse",
"大": "big",
"巨": "big",
"暗い": "dark",
"青ざめる": "shock", # literally "aozomeru", translates to "pale", but the expression it represents is shock/horror
"青ざめ": "shock", # literally "aozame" translates to "pale", but the expression it represents is shock/horror
"を隠す": "hide",
"非表示": "hide",
"追従": "follow",
"まばたき": "blink",
"笑い": "happy",
"ウィンク": "wink",
"ウインク": "wink",  # this is somehow different than above?
"ｳｨﾝｸ": "wink",
"睨み": "glare",
"ｷﾘｯ": "serious", # phonetically "kiri-tsu", might informally mean "confident"? kinda a meme phrase, a professional model translated this to 'serious' tho so idk
"ジト": "doubt", # jito
"じと": "doubt", # jito
"じど": "doubt", # jido but close enough that it probably means jito
"なごみ": "=.=", # "calm"
"びっくり": "surprise",
"驚き": "surprise",
"見開き": "spread",  # something closer to "wide eyes" but google says it's "spread" so idk
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
"ぐる": "dizzy", # perhaps "spinny"
"グルグル": "dizzy", # perhaps "spinny"
"グル": "dizzy", # perhaps "spinny"
"カメラ": "camera", # for looking at the camera
"はぅ": ">.<",
"にやり": "grin",
"ニヤリ": "grin",  # these 2 are phonetically the same, "niyari"
"にっこり": "smile",
"ムッ": "upset",
"照れ": "blush",
"赤面": "blush",
"黒": "black",
"白": "white",
"緑": "green",
"ピンク": "pink",
"黄": "yellow",
"紫": "purple",
"赤": "red",
"蒼": "blue",
"金": "gold",
"銀": "silver",
"色": "color",
"汗": "sweat",
"円": "circle",
"表": "front", # not sure about this one, front as in outward-facing geometry, opposite of backward-facing geometry. literally means "table" tho lol
"縁": "edge",
"エッジ": "edge",
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
"なみだ": "tears",  # phonetically "namida"
"涙": "tears",  # phonetically "namida"
"ん": "hmm",
"へ": "eeeh",
"の": "of", # backwards yoda-style grammar: technically "A の B" translates to "B of A" but I can't do that switcheroo without major changes
"用": "for",  # backwards yoda-style grammar: same
"ー": "--", # not sure what to do with this, often used to mean continuation of a sound/syllable...
}

# add the special symbols
words_dict.update(symbols_dict)
# after defining its contents, ensure that it is sorted with longest keys first. for tying items relative order is unchanged.
# fixes the "undershadowing" problem
words_dict = dict(sorted(list(words_dict.items()), reverse=True, key=lambda x: len(x[0])))


# these get appended to the end instead of being replaced in order
prefix_dict = {
"中": "_M",  # this one isn't truly standard but i like the left/right/middle symmetry
"右": "_R",
"左": "_L",
"親": " parent",
"先": " end",
}
prefix_dict_ord = dict({(ord(k), v) for k, v in prefix_dict.items()})



odd_punctuation_dict = {
"　": " ",  # x3000, just a fullwidth space aka "ideographic space"
"、": ",",  # x3001, some sorta fullwidth comma
"。": ".",  # x3002
"〈": "<",  # x3008
"〉": ">",  # x3009
"《": "<",  # x300a
"》": ">",  # x300b
"「": '"',  # x300c
"」": '"',  # x300d
"『": '"', # x300e
"』": '"', # x300f
"【": "[",  # x3010
"】": "]",  # x3011
"・": "-",  # x30fb, could map to 00B7 but i don't think MMD would display that either
"〜": "~",  # x301C wave dash, not a "fullwidth tilde"
"｟": "(",  # xff5f
"｠": ")",  # xff60
"｡": ".",  #xff61
"｢": '"',  # xff62
"｣": '"',  # xff63
"､": ",",  # xff64
"･": "-",  # xff65
}
# note: "ー" = "katakana/hiragana prolonged sound mark" = 0x30fc should !!!NOT!!! be treated as punctuation cuz it shows up in several "words"

# for use with 'translate' function, convert the keys to the unicode values instead of strings:
fullwidth_dict_ord = dict({(ord(k), v) for k, v in odd_punctuation_dict.items()})
# then add the fullwidth latin symbols:
# https://en.wikipedia.org/wiki/Halfwidth_and_Fullwidth_Forms_(Unicode_block)
# fullwidth chars like ０１２３ＩＫ are in range FF01–FF5E  and correspond to  21-7E, difference=(FEE0/‭65248‬)
for uni in range(0xff01, 0xff5f):
	fullwidth_dict_ord[uni] = uni - 0xfee0


########################################################################################################################
########################################################################################################################
# regular expression stuff
# indent: whitespace _ box, 2571/2572/2573 are exceptions!
indent_pattern = "^[\\s_\u2500-\u2570\u2574-\u257f]+"
indent_re = re.compile(indent_pattern)
# prefix: match 右|左|中 but not 中指
prefix_pattern = "^([右左]|中(?!指))+"
prefix_re = re.compile(prefix_pattern)
# suffix: match LRM and parent (but not motherbone) and end (but not toe)
suffix_pattern = "([右左中]|(?<!全ての)親|(?<!つま)先)+$"
suffix_re = re.compile(suffix_pattern)
# strip: whitespace _ . -
strip_pattern = "(^[\\s_.-]+)|([\\s_.-]+$)"
strip_re = re.compile(strip_pattern)

# TODO: maybe instead of finding unusal jap chars, i should just find anything not basic ASCII alphanumeric characters?
jp_pattern = "\u3040-\u30ff"  # "hiragana" block + "katakana" block
jp_pattern += "\u3000-\u303f"  # "cjk symbols and punctuation" block, fullwidth space, brackets, etc etc
jp_pattern += "\u3400-\u4dbf"  # "cjk unified ideographs extension A"
jp_pattern += "\u4e00-\u9fff"  # "cjk unified ideographs"
jp_pattern += "\uf900-\ufaff"  # "cjk compatability ideographs"
jp_pattern += "\uff66-\uffee"  # "halfwidth and fullwidth forms" halfwidth katakana and other stuff
needstranslate_pattern = jp_pattern  # copy this stuff, "needstranslate" is a superset of "is_jp"
jp_pattern = "[" + jp_pattern + "]"
jp_re = re.compile(jp_pattern)

needstranslate_pattern += "\u2190-\u21ff"  # "arrows" block
needstranslate_pattern += "\u2500-\u257f"  # "box drawing" block, used as indentation sometimes
needstranslate_pattern += "\u25a0-\u25ff"  # "geometric shapes", common morphs ▲ △ □ ■ come from here
needstranslate_pattern += "\uff01-\uff65"  # "halfwidth and fullwidth forms" fullwidth latin and punctuation aka ０１２３ＩＫ
needstranslate_pattern += "".join(symbols_dict.keys())  # add "symbol dict" just in case there are some outlyers... some overlap with ranges but w/e
needstranslate_pattern = "[" + needstranslate_pattern + "]"
needstranslate_re = re.compile(needstranslate_pattern)


########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
# functions


STANDARD_INDENT = "  "

DEBUG = False


# not 100% confident this is right, there are probably other characters that can display just fine in MMD like accents
# TODO: check for other chars that can display in MMD just fine, try accents maybe
def is_latin(text:str) -> bool:
	return all(ord(c) < 128 for c in text)

def is_jp(text:str) -> bool:
	""" is jp/cn and needs translation and can be plausibly translated """
	m = jp_re.search(text)
	# print(bool(m), str(text))
	return bool(m)

def needs_translate(text:str) -> bool:
	""" won't display right in MMD, either is jp/cn or is wierd unicode symbols """
	m = needstranslate_re.search(text)
	# print(bool(m), str(text))
	return bool(m)

def pre_translate(in_list: Union[List[str],str]) -> Union[Tuple[str,str,str],Tuple[List[str],List[str],List[str]]]:
	"""
	Handle common translation things like prefixes, suffixes, fullwidth alphanumeric characters, indents,
	and some types of punctuation. Returns 3-ple of EN indent, JP body, EN suffix. This way the translate can work on
	the important stuff and ignore the chaff.
	:param in_list: list of JP strings, or a single JP string
	:return: list of indent/body/suffix tuples, or a single tuple
	"""
	# input str breakdown: (indent) (L/R prefix) (padding) (((body))) (padding) (L/R suffix)
	
	input_is_str = isinstance(in_list, str)
	if input_is_str: in_list = [in_list]  # force it to be a list anyway so I don't have to change my structure
	indent_list = []  # list to build & return
	body_list = []  # list to build & return
	suffix_list = []  # list to build & return
	for s in in_list:
		# 1: subst JP/fullwidth alphanumeric chars -> standard EN alphanumeric chars
		# https://en.wikipedia.org/wiki/Halfwidth_and_Fullwidth_Forms_(Unicode_block)
		# fullwidth chars like ０１２３ＩＫ are in range FF01–FF5E  and correspond to  21-7E, difference=(FEE0/‭65248‬)
		# to handle them, use nifty str.translate() method, dict must have keys be ordinal unicode values tho
		out = s.translate(fullwidth_dict_ord)
		
		# 2. check for indent
		indent_prefix = ""
		# get the entire indent, regardless of what it is made of
		# re.search
		indent_match = indent_re.search(out)
		if indent_match is not None:
			# found a matching indent!
			if indent_match.end() == len(out):
				# the indent consumed the entire string... skip this stage, do nothing, leave as is
				pass
			else:
				# remove the indent from the orig str
				out = out[indent_match.end():]
				# decide what to replace it with
				# if it contains an underscore, use under prefix... otherwise use 2-space indent
				indent_prefix = "_" if "_" in indent_match.group() else STANDARD_INDENT
		
		# 3: remove known JP prefix/suffix, assemble EN suffix to be reattached later
		en_suffix = ""
		# get the prefix
		prefix_match = prefix_re.search(out)
		if prefix_match is not None:
			if prefix_match.end() == len(out):
				# if the prefix consumed the entire string, skip this stage
				pass
			else:
				# remove the prefix from the orig str
				out = out[prefix_match.end():]
				# generate a new EN suffix from the prefix I removed
				en_suffix += prefix_match.group().translate(prefix_dict_ord)
		# get the suffix
		suffix_match = suffix_re.search(out)
		if suffix_match is not None:
			if suffix_match.start() == 0:
				# if the suffix consumed the entire string, skip this stage
				pass
			else:
				# remove the suffix from the orig str
				out = out[:suffix_match.start()]
				# generate a new EN suffix from the suffix I removed
				en_suffix += suffix_match.group().translate(prefix_dict_ord)
				
		# 4: strip leading/ending spaces or whatever that might have been insulated by the prefix/suffix
		out_strip = strip_re.sub("", out)
		if out_strip == "":
			# if stripping whitespace removes the entire string, then skip/undo this step
			pass
		else:
			out = out_strip
		
		# 5: append all 3 to the list: return indent/suffix separate from the body
		indent_list.append(indent_prefix)
		body_list.append(out)
		suffix_list.append(en_suffix)
		
	if input_is_str:return indent_list[0], body_list[0], suffix_list[0]	 # if original input was a single string, then de-listify
	else:			return indent_list, body_list, suffix_list	# otherwise return as a list


def piecewise_translate(in_list: Union[List[str],str], in_dict: dict) -> Union[List[str],str]:
	"""
	Apply piecewise translation to inputs when given a mapping dict.
	Mapping dict will usually be the builtin comprehensive 'words_dict' or some results found from Google Translate.
	From each position in the string(ordered), check each map entry(ordered). Dict should have keys ordered from longest
	to shortest to avoid "undershadowing" problem.
	Always returns what it produces, even if not a complete translation. Outer layers are responsible for checking if
	the translation is "complete" before using it.
	
	:param in_list: list of JP strings, or a single JP string
	:param in_dict: dict of mappings from JP substrings to EN substrings
	:return: list of resulting strings, or a single resulting string
	"""
	input_is_str = isinstance(in_list, str)
	if input_is_str: in_list = [in_list]  # force it to be a list anyway so I don't have to change my structure
	outlist = []  # list to build & return
	
	dictitems = list(in_dict.items())
	
	for out in in_list:
		if (not out) or out.isspace():  # support bad/missing data
			outlist.append("JP_NULL")
			continue
		# goal: substrings that match keys of "words_dict" get replaced
		# NEW ARCHITECTURE: starting from each char, try to match against the contents of the dict. longest items are first!
		i = 0
		while i < len(out):  # starting from each char of the string,
			found_match = False
			for (key, val) in dictitems:  # try to find anything in the dict to match against,
				if out.startswith(key, i):  # and if something is found starting from 'i',
					found_match = True
					# i am going to replace it key->val, but first maybe insert space before or after or both.
					# note: letter/number are the ONLY things that use joinchar. all punctuation and all JP stuff do not use joinchar.
					# if 'begin-1' is a valid index and the char at that index is letter/number, then PREPEND a space
					before_space = " " if i != 0 and out[i-1].isalnum() else ""
					# if "begin+len(key)" is a valid index and the char at that index is letter/number, then APPEND a space
					after_space = " " if i+len(key) < len(out) and out[i+len(key)].isalnum() else ""
					# now JOINCHAR is added, so now i substitute it
					out = out[0:i] + before_space + val + after_space + out[i+len(key):]
					# i don't need to examine or try to replace on any of these chars, so skip ahead a bit
					i += len(val) + int(bool(before_space)) + int(bool(after_space))
					# nothing else will match here, since I just replaced the thing, so break out of iterating on dict keys
					break
			if found_match is False:
				i += 1
		# once all uses of all keys have been replaced, then append the result
		outlist.append(out)
	
	if input_is_str:	return outlist[0]	# if original input was a single string, then de-listify
	else:				return outlist		# otherwise return as a list


def local_translate(in_list: Union[List[str],str]) -> Union[List[str],str]:
	"""
	Simple wrapper func to run both pre_translate and local_translate using words_dict.
	With DEBUG=True, it prints before/after.
	Results are best-effort translations, even if incomplete.
	
	:param in_list: list of JP strings, or a single JP string
	:return: list of resulting strings, or a single resulting string
	"""
	input_is_str = isinstance(in_list, str)
	if input_is_str: in_list = [in_list]  # force it to be a list anyway so I don't have to change my structure
	
	# first, run pretranslate: take care of the standard stuff
	# things like prefixes, suffixes, fullwidth alphanumeric characters, etc
	indents, bodies, suffixes = pre_translate(in_list)
	
	# second, run piecewise translation with the hardcoded "words dict"
	outbodies = piecewise_translate(bodies, words_dict)
	
	# third, reattach the indents and suffixes
	outlist = [i + b + s for i,b,s in zip(indents, outbodies, suffixes)]
	
	# pretty much done! check whether it passed/failed outside this func
	if DEBUG:
		for s,o in zip(in_list, outlist):
			# did i translate the whole thing? check whether results are all "normal" characters
			print("%d :: %s :: %s" % (is_latin(o), s, o))
	
	if input_is_str:	return outlist[0]	# if original input was a single string, then de-listify
	else:				return outlist		# otherwise return as a list


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
# 	core.MY_PRINT_FUNC("Nuthouse01 - 07/13/2020 - v4.62")
# 	main()
#
