import os
import re
import emoji
from utils2 import ToolGeneral
import time

pwd = os.path.dirname(os.path.abspath(__file__))
tool = ToolGeneral()

class NameExtract(object):
    """ 基于词典和规则提取人名
    Return: 人名， flag
        人名： string
        flag： int: 0，无确切的名字；1，有人名；2.不恰当的名字； 3.姓； 4.骂人的话
        0，无确切的名字，如经去空格、去表情符等预处理后为空；随便；不想说；你好等。
    """
    def __init__(self):
        self.dict_zanghua = tool.load_dict(os.path.join(pwd,'dict','dict_zanghua_name_extract.txt'))  # 3. 仅有脏话
        self.dict_name_uncertain = tool.load_dict(os.path.join(pwd, 'dict', 'dict_name_uncertain.txt')) # 0，无确切的名字
        self.dict_name_improper = tool.load_dict(os.path.join(pwd, 'dict', 'dict_name_improper.txt'))  # 2.不恰当的名字
        # self.dict_yuqici = tool.load_dict(os.path.join(pwd, 'dict', 'dict_yuqici.txt'))  # 仅有语气词
        self.num_ori_text = 0

    def name_extract(self, text):
        # print("ori: ", text)
        if len(text) == 0:
            return '', 0
        self.num_ori_text = len(text)

        # 1. 文本预处理
        # 1）去除多余的空格和回车
        text_1 = loss_space_return(text)
        len_no_space = len(text_1)
        # 2）去除标点（通过查询标点词典的方式）
        text_1 = loss_othercharactor(text_1)
        text_1 = loss_space_return(text_1)
        # 3）去除emoji（需要一个emoji检测的方法）
        text_1 = remove_emoji(text_1)
        text_1 = loss_2more_biaodian(text_1)
        # 4）去掉句子末尾的标点
        text_1 = loss_text_end_biaodian(text_1)
        print('text_1: ', text_1)

        # 2. 整句判断
        # 1）预处理后的文本只有空格或回车，判为 < 无意义 >
        if len(text_1) == 0:
            return text_1, 0
        # 2）预处理后的文本是骂人的话（查词典，要考虑重复的情况），判为 < 骂人 >
        if text_1 in self.dict_zanghua:
            return text_1, 4   # '', 4
        if len(text_1) > 3:
            if text_1[0:3] == '你好，' or text_1[0:3] == '你好,' or text_1[0:3] == '你好 ' or text_1[0:3] == '你好 ':
                if text_1[3:] in self.dict_zanghua:
                    return text_1, 4  # '', 4
        # 3）flag = 0, 无确切的名字
        if text_1 in self.dict_name_uncertain:
            return text_1, 0
        # 4）提取名字
        res_name, flag = name(text_1)
        res_name = del_jia(res_name)
        # 5）flag = 2, 不恰当的名字
        if res_name in self.dict_name_improper:
            return res_name, 2
        if res_name in self.dict_zanghua:
            return res_name, 4   # '', 4

        if flag==1 and len(res_name)==0:
            res_name = text_1
        return res_name, flag

def name(text):
    # 我叫夏雨，请问怎么称呼你呢
    res = re.findall(r'(.*?)(请问怎么称呼你呢)(.*?)', text)
    if len(res):
        res_list = []
        res_list.append(res[0][0])
        res_list.append(res[0][2])
        text = "".join(res_list)

    # 陈哥叫我
    text_list = list(text)
    if len(text_list)>2 and text_list[-2] == '叫' and text_list[-1] == '我':
        return "".join(text_list[:-2]), 1
    # 大名齐梓晨，小名涛涛%
    text_list = list(text)
    text_list.append('%')
    text = "".join(text_list)

    # 我小名叫耀就行
    res = re.findall(r'(小名叫)(.*?)(吧|叭|就好|就可以|就可以了|就行|就OK|就ok|好了|就好啦|好吗|,|，|\.|。|!|！|谢谢|%)', text)
    if len(res):
        return res[-1][1], 1

    # '我叫徐涛！叫我小徐就行'
    res = re.findall(r'(叫我|称呼我|称我为|加我|称|我就叫|我叫|我是|本人姓名|我也叫|我讲|是|本人|名叫|大名|小名|小名叫|改为|可以是)(.*?)(吧|叭|就好|就可以|就可以了|就行|就OK|就ok|好了|就好啦|好吗|,|，|\.|。|!|！|谢谢|%)',
                     text)
    if len(res):
        text2 = res[0][1]
        text_list2 = list(text2)
        text_list2.append('%')
        text2 = "".join(text_list2)
        res2 = re.findall(r'(我姓|免贵姓|姓|我性|本人姓)(.*)(吧|叭|就好|就可以|就可以了|就行|就OK|就ok|好了|就好啦|好吗|,|，|\.|。|!|！|谢谢|%)', text2)
        if len(res2):
            return list(res2[0][1])[0], 3
        return res[-1][1], 1

    res = re.findall(r'(叫我|称呼我|称我为|加我|称|我就叫|我叫|我是|本人姓名|我也叫|我讲|是|本人|名叫|大名|小名|改为|可以是)(.*?)(好啦|%)', text)
    if len(res):
        text2 = res[0][1]
        text_list2 = list(text2)
        text_list2.append('%')
        text2 = "".join(text_list2)
        res2 = re.findall(r'(我姓|免贵姓|姓|我性|本人姓)(.*)(吧|叭|就好|就可以|就可以了|就行|就OK|就ok|好了|就好啦|好吗|,|，|\.|。|!|！|谢谢|%)', text2)
        if len(res2):
            return list(res2[0][1])[0], 3
        return res[-1][1], 1

    res = re.findall(r'(叫我|称呼我|称我为|加我|称|我就叫|我叫|我是|本人姓名|我也叫|我讲|是|本人|名叫|大名|小名|改为|可以是)(.*)(%)', text)
    if len(res):
        text2 = res[0][1]
        text_list2 = list(text2)
        text_list2.append('%')
        text2 = "".join(text_list2)
        res2 = re.findall(r'(我姓|免贵姓|姓|我性|本人姓)(.*)(吧|叭|就好|就可以|就可以了|就行|就OK|就ok|好了|就好啦|好吗|,|，|\.|。|!|！|谢谢|%)', text2)
        if len(res2):
            return list(res2[0][1])[0], 3
        return res[-1][1], 1

    res = re.findall(r'(.*?)(吧|叭|就好|就可以|就可以了|就行|就OK|就ok|好了|就好啦|好吗|谢谢)', text)
    if len(res):
        return res[0][0], 1

    res = re.findall(r'(.*)(好啦)', text)
    if len(res):
        return res[0][0], 1

    res = re.findall(r'(我姓|免贵姓|姓|我性|本人姓)(.*)(吧|叭|就好|就可以|就可以了|就行|就OK|就ok|好了|就好啦|好吗|,|，|\.|。|!|！|谢谢|%)', text)
    if len(res):
        return list(res[0][1])[0], 3

    # 你好，小张
    res = re.findall(r'(你好,|你好，|你好！|你好.|你好。)(.*)(%)', text)
    if len(res):
        return res[-1][1], 1

    # res = re.findall(r'(我)(.*)', text)  # 我老董     # 我今年58岁    # 我高兴
    # if len(res):
    #     print(res[0][1])
    #     return res[0][1]
    # print('ori: ')

    text_list = list(text)
    text_list.pop()
    text = "".join(text_list)

    return text, 1

def del_jia(text):
    res = re.findall(r'叫(.*)', text)
    if res:
        return res[-1]
    return text

# 匹配正常字符
def loss_othercharactor(text):
    l = list(text)
    for i in range(1, len(l) - 1):
        if len(re.findall(r'[\u4e00-\u9fa5\w,，。 \.;\'：/\\:\/!！？?\'\"\”\“\’\‘\；；……——<>《》\[\]{}【】、-]', l[i])) == 0:
            if len(re.findall(r'[0-9a-zA-Z]', l[i - 1])) > 0 and len(re.findall(r'[0-9a-zA-Z]', l[i + 1])) > 0:
                l[i] = ' '
    res = "".join(l)

    res = re.findall(r'[\u4e00-\u9fa5\w,，。 \.;\'：/\\:\/!！？?\'\"\”\“\’\‘\；；……——<>《》\[\]{}【】、-]', res)
    res = "".join(res)
    # print("loss_othercharactor: ", res)
    return res

def loss_othercharactor2(text):
    res = re.findall(r'[\u4e00-\u9fa5\w,，。 \.;\'：/\\:\/!！？?\'\"\”\“\’\‘\；；……——<>《》\[\]{}【】、-]', text)
    res = "".join(res)
    # print("loss_othercharactor: ", res)
    return res

# 去掉连续多余2个的标点
def loss_2more_biaodian(text):
    if text == u'...' or text == u'......':
        return text
    flag = 1
    while flag:
        text_list = list(text)
        res = re.search(r'[,，。 \.;\'：/\\:\/!！？?\'\"\”\“\’\‘\；；……——<>《》\[\]{}【】、-]{3,}', text) # <re.Match object; span=(2, 4), match='“”'>
        if res is not None:
            s, e = res.span()[0], res.span()[1]
            text = "".join(text_list[:s+2] + text_list[e:])
        else:
            flag = 0
    # # print("loss_2more_biaodian: ", res)
    return text

# 去掉句子末尾的标点
def loss_text_end_biaodian(text):
    text_list = list(text)
    for i in range(len(text)):
        res = re.search(r'[,，。 \.;\'：/\\:\/!！？?\'\"\”\“\’\‘\；；……——<>《》\[\]{}【】、-]',text_list[-1])
        if res:
            text_list.pop()
        else:
            break
    res = "".join(text_list)
    # print("loss_text_end_biaodian: ", res)
    return res

# 匹配正常标点
def loss_biaodian(text):
    pattern_no_biaodian = re.compile(r'[,，。 \.;\'：/\\:\/!！？?\'\"\”\“\’\‘\；；……——<>《》\[\]{}【】、-]')
    text_no_biaodian = re.sub(pattern=pattern_no_biaodian, repl='', string=str(text))
    # # print(text_no_biaodian)
    return text_no_biaodian

# 匹配空格回车
def loss_space_return2(text):
    pattern_no_space_return = re.compile(r'[\n]')
    text_space_return = re.sub(pattern=pattern_no_space_return, repl=' ', string=str(text))
    return text_space_return

def loss_space_return(text):
    if len(text) == 0:
        return text
    if text == ' ':
        return ''
    if len(re.findall(r'\S', text)) == 0:
        return ''
    rule = re.compile('\s')
    text2 = re.sub(pattern=rule, repl=' ', string=str(text))
    rule = re.compile('^\s+|\s+$')
    text2 = re.sub(pattern=rule, repl='', string=str(text2))
    rule = re.compile(' {2,}')
    text2 = re.sub(pattern=rule, repl=' ', string=str(text2))
    l = list(text2)
    l_res = []
    for i in range(len(l) - 1):
        if l[i] == ' ' and len(re.findall(r'[\u4e00-\u9fa5]', l[i + 1])) > 0:
            # # print('find')
            pass
        else:
            l_res.append(l[i])
    l_res.append(l[-1])
    res = "".join(l_res)
    # print('loss_space_return: ', res)
    return res

def remove_emoji(text):
    for x in emoji.UNICODE_EMOJI:
        if x in ['en', 'es', 'pt', 'it', 'fr', 'de']:
            continue
        if x in text:
            text = text.replace(x, "")
    # print('remove_emoji: ', text)
    return text

def predict_to_file():
    gs = NameExtract()
    path_in = './data/name_text_sample_order02.txt'
    path_out = './data/name_text_sample_order02_res.txt'
    f_in = open(path_in, 'r', encoding='utf-8')
    f_out = open(path_out, 'w', encoding='utf-8')
    count = 1
    for line in f_in.readlines():
        if line == None or line == '\n' or len(line) == 0:
            continue
        res, flag = gs.name_extract(line)
        # print('res: ', res)
        # print('################################### ', count)
        count += 1
        # f_out.write(line[:-1] + '   RESULT: ' + str(res) + '\n')
        f_out.write(line[:-1] + '   RESULT: ' + str(res) + '   FLAG: ' + str(flag) + '\n')
    f_in.close()
    f_out.close()


if __name__ == '__main__':
    gs = NameExtract()
    gs = NameExtract()
    start_time = time.time()
    # s5 = u'你好屌丝'
    # s5 = u'你好我叫杨雨☔️，，，，'
    s5 = u'你好，我叫风云'
    # s5 = u'叫我梅，我有乳腺增生和甲状腺低下，能打针'
    # s5 = u'我叫赵莲英，可以叫我莲英'
    # s5 = u'我姓蒲，名叫蒲鲜眉'
    # s5 = u'我今年58岁，就叫我蒋女士好吗'
    # s5 = u'我叫徐涛！叫我小徐就行'
    # s5 = u'我叶天'
    s8 = u'我姓常65岁'
    # s5 = u'陈哥叫我'
    # s5 = u'大名齐梓晨，小名涛涛'
    # s5 = u'我小名叫耀就行'
    # s5 = u'我姓卢，男，1979年生，属羊'
    # s5 = u'我叫夏雨，请问怎么称呼你呢'
    # s5 = u'改叫小明'
    # s5 = u'那改为小明'
    # s5 = u'还是叫小明'
    s7 = u'也可以是小明'
    # s5 = u'小明'
    # s5 = u'叫我   喂'
    s6 = u'`姐'
    # gs.name_extract(s5)
    res, flag = gs.name_extract(s5)
    print(time.time() - start_time)
    print('res: ', res)
    print('flag: ', flag)

    start_time = time.time()
    res, flag = gs.name_extract(s6)
    print(time.time() - start_time)
    print('res: ', res)
    print('flag: ', flag)

    start_time = time.time()
    res, flag = gs.name_extract(s7)
    print(time.time() - start_time)
    print('res: ', res)
    print('flag: ', flag)

    start_time = time.time()
    res, flag = gs.name_extract(s8)
    print(time.time() - start_time)
    print('res: ', res)
    print('flag: ', flag)

    print('done')

    # predict_to_file()

