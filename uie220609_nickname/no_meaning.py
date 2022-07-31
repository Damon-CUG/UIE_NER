import os
import csv
import re
import jieba
import emoji
from emotion_classification.utils import ToolGeneral

pwd = os.path.dirname(os.path.abspath(__file__))
tool = ToolGeneral()

jieba.load_userdict(os.path.join(pwd,'dict','dict_my_cut.txt'))

class MeaningClassification(object):
    """ 基于词典和规则判断句子有无意义
    Return:
        int: 0，无意义；1，有意义；2.骂人的话
    """
    def __init__(self):
        self.dict_zanghua = tool.load_dict(os.path.join(pwd,'dict','dict_zanghua.txt'))  # 仅有脏话
        self.dict_rencheng = tool.load_dict(os.path.join(pwd, 'dict', 'dict_rencheng.txt'))  # 仅有人称
        self.dict_yuqici = tool.load_dict(os.path.join(pwd, 'dict', 'dict_yuqici.txt'))  # 仅有语气词
        self.dict_ch = tool.load_dict(os.path.join(pwd, 'dict', 'dict_ch.txt'))  # 中文词典
        self.dict_en = tool.load_dict(os.path.join(pwd, 'dict', 'dict_en.txt'))  # 英文词典
        self.num_ori_text = 0

    def is_yuqici(self, text):
        if len(re.findall(r'[0-9{1:}\.]', text)) == len(text) and len(re.findall(r'[\.]', text)) == 1 and text != '.':
            return 0
        if len(text) == 0:
            return 0
        if len(re.findall(r'[\u4e00-\u9fa5,，。 \.;\'：/\\:\/!！？?\'\"\”\“\’\‘\；；……——<>《》\[\]{}【】、-]', text)) == 0:
            return 0
        if len(text) == 3 and text in self.dict_yuqici:
            return 1
        if len(text) == 2 and text in self.dict_yuqici:
            return 1
        if len(text) == 1 and text in self.dict_yuqici:
            return 1
        if len(re.findall(r'[,，。 \.;\'：/\\:\/!！？?\'\"\”\“\’\‘\；；……——<>《》\[\]{}【】、-]', text)) > 0:
            return 1
        n = len(text)
        res3 = self.is_yuqici(text[:n - 3]) and self.is_yuqici(text[n - 3:])
        res2 = self.is_yuqici(text[:n - 2]) and self.is_yuqici(text[n - 2:])
        res1 = self.is_yuqici(text[:n - 1]) and self.is_yuqici(text[n - 1:])
        res = res3 or res2 or res1
        return res

    def loss_4more_ch(self, text):
        text_list = list(text)
        num_text_list = len(text_list)
        meaning_list = [1]*num_text_list
        i = 0
        while i < num_text_list:
            if text_list[i] in self.dict_ch and meaning_list[i] == 1 and len(text_list[i]) == 1:
                j = i + 1
                while j < num_text_list and text_list[i] == text_list[j]:
                    j = j + 1
                # # print('i, j: ', i, j)
                if j - i >= 4:
                    meaning_list[i+1:j] = [0] * (j-i-1)
                i = j
            else:
                i += 1
        # # print('修改后的meaning_list: ', meaning_list)
        for i in range(num_text_list-1, -1, -1):
            if meaning_list[i] == 0:
                text_list.pop(i)
        # # print('修改后的text_list: ', text_list)
        # # print('修改后的text_list: ', "".join(text_list))
        return "".join(text_list)

    def meaning_judge(self, text):
        # print("ori: ", text)
        if len(text) == 0:
            return 0
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
        # print('text_1: ', text_1)

        # 2. 整句判断
        # 1）预处理后的文本只有空格或回车，判为 < 无意义 >
        if len(text_1) == 0:
            return 0
        # 2）预处理后的文本是骂人的话（查词典，要考虑重复的情况），判为 < 骂人 >
        if text_1 in self.dict_zanghua:
            return 2
        if len(text_1)>3:
            if text_1[0:3] == '你好，' or text_1[0:3] == '你好,' or text_1[0:3] == '你好 ' or text_1[0:3] == '你好 ':
                if text_1[3:] in self.dict_zanghua:
                    return 2
        # 3）只有非中文字符（句中可能有空格），且空格隔开的每个字符串在英文词典中查询不到，判为 < 无意义 >   [@@@@@@@@@@@@@@@@@@]
        if len(re.findall(r'[\w]', text_1)) == 1 and len(re.findall(r'[\u4e00-\u9fa5]', text_1)) == 0: #\0-9a-zA-Z_
            # # print('单个字符 return 0', text_1)
            return 0
        # # print('单个字符 NOT return 0', text_1)
        if len(re.findall(r'[\u4e00-\u9fa5]', text_1)) == 0:
            text_1_list = text_1.split(' ')
            flag_en_wrong_list = [0] * len(text_1_list)
            for i in range(len(text_1_list)):
                if text_1_list[i].lower() in self.dict_en:
                    flag_en_wrong_list[i] = 1
            if sum(flag_en_wrong_list) == 0:
                return 0

        # 4）是中文字符，但只有一个字或单字的重复，判为 < 无意义 >  [@@@@@@@@@@@@@@@@@@  单字的重复]
        if len(text_1)==1 and text_1 in self.dict_ch:
            return 0
        # 5）是中文字符，但属于人称词典（要考虑重复的情况），判为 < 无意义 >
        if text_1 in self.dict_rencheng:
            return 0
        # 6）是中文字符，但属于语气助词词典（要考虑重复的情况），判为 < 无意义 >
        if text_1 in self.dict_yuqici:
            return 0

        # 3. 分词
        # 经过整句判断后的句子，调用分词模块进行分词。
        text2 = loss_othercharactor(text)
        text2 = remove_emoji(text2)
        text2 = loss_space_return(text2)
        text2 = loss_2more_biaodian(text2)
        text2 = self.loss_4more_ch(text2)
        # drop_num = len(text) - len(text2)
        drop_num = len_no_space - len(text2)
        # text2 = loss_2more_biaodian(text2)
        text_list = list(jieba.cut(text2))
        for i in range(len(text_list)-1, -1, -1):
            if text_list[i] == ' ':
                text_list.pop(i)
        # print('fenci: ', text_list)
        num_text_list = len(text_list)
        len_fenci = 0
        for i in range(num_text_list):
            len_fenci += len(text_list[i])
        # print('len_fenci: ', len_fenci)

        # 4. 逐个词打标签
        # 对分词后的字符串数组，对其中每个元素（记录字符串长度n）做判断（以下判断为互斥关系，从1到7命中一种则不再做后续的判断）：
        biaodian_list = [0] * num_text_list
        for i in range(num_text_list):
            if len(re.findall(r'[,，。 \.;\'：/\\:\/!！？?\'\"\”\“\’\‘\；；……——<>《》\[\]{}【】、-]', text_list[i])) == 1:
                biaodian_list[i] = 1
        # print('biaodian: ', biaodian_list)
        
        # 1）存在于骂人词典，判断为骂人（标记 < n, 骂人 >）
        maren_list = [0] * num_text_list
        for i in range(num_text_list):
            for j in range(i, num_text_list):
                tmp = "".join(text_list[i:j+1])
                # # print(tmp)
                if tmp in self.dict_zanghua:
                    for k in range(i, j+1):
                        maren_list[k] = 1
        # print('maren: ', maren_list)

        # 2）存在于人称词典，判断为人称（标记 < n, 人称 >）
        rencheng_list = [0] * num_text_list
        for i in range(num_text_list):
            for j in range(i, num_text_list):
                tmp = "".join(text_list[i:j + 1])
                # # print(tmp)
                if tmp in self.dict_rencheng:
                    for k in range(i, j + 1):
                        rencheng_list[k] = 1
        # print('rencheng: ', rencheng_list)

        # 3）存在于语气词典，判断为语气（标记 < n, 语气词 >）
        yuqici_list = [0] * num_text_list
        for i in range(num_text_list):
            yuqici_list[i] = self.is_yuqici(text_list[i])
        # print('yuqici: ',yuqici_list )

        # 4）全部为阿拉伯数字，判断为有意义（标记 < n, 有意义 >）
        meaning_list = [0] * num_text_list
        for i in range(num_text_list):
            # if text_list[i].isdigit():
            #     meaning_list[i] = 1
            if len(re.findall(r'[0-9{1:}\.]', text_list[i])) == len(text_list[i]) and len(re.findall(r'[\.]', text_list[i])) == 1 and text_list[i] != '.':
                meaning_list[i] = 1
        # print('阿拉伯数字: ', meaning_list)

        # 5）存在于英文词典中，该元素判为有意义（标记 < n, 有意义 >）
        for i in range(num_text_list):
            if text_list[i].lower() in self.dict_en:
                meaning_list[i] = 1
        # print('存在于英文meaning_list中: ', meaning_list)

        # 6）存在于中文词典中，该元素判为有意义（标记 < n, 有意义 >）
        for i in range(num_text_list):
            if text_list[i] in self.dict_ch:
                meaning_list[i] = 1
        # print('存在于中文meaning_list中: ', meaning_list)
        # 7）该元素判为无意义，标记 < n, 无意义 >

        # 5. 统计
        # 对打完标签的数组进行统计：
        # 1）所有标签均为骂人，则判为 < 骂人 >；
        if sum(maren_list) == num_text_list:
            # # print('sum(maren_list): ', sum(maren_list))
            return 2
            # # print('sum(maren_list): ', sum(maren_list))
        merge_maren_biaodian_list = [0] * num_text_list
        for i in range(num_text_list):
            merge_maren_biaodian_list[i] = maren_list[i] or biaodian_list[i]
        if sum(merge_maren_biaodian_list) == num_text_list:
            # # print('sum(merge_maren_biaodian_list): ', sum(merge_maren_biaodian_list))
            return 2
        # # print('sum(merge_maren_biaodian_list): ', sum(merge_maren_biaodian_list))

        # if sum(maren_list) == num_text_list:
        #     # print('sum(maren_list): ', sum(maren_list))
        #     return 2
        # # print('sum(maren_list): ', sum(maren_list))
        # merge_maren_biaodian_list = [0] * num_text_list
        # # for 骂人 ？?
        # for i in range(num_text_list):
        #     if len(re.findall(r'[,，。 \.;\'：/\\:\/!！？?\'\"\”\“\’\‘\；；……——<>《》\[\]{}【】、-]', text_list[i])) == 1:
        #         merge_maren_biaodian_list[i] = maren_list[i] or biaodian_list[i]
        # if sum(merge_maren_biaodian_list) == num_text_list:
        #     # print('sum(merge_maren_biaodian_list): ', sum(merge_maren_biaodian_list))
        #     return 2
        # # print('sum(merge_maren_biaodian_list): ', sum(merge_maren_biaodian_list))

        # 2）所有标签均为人称，则判为 < 无意义 >；
        if sum(rencheng_list) == num_text_list:
            # print('sum(rencheng_list): ', sum(rencheng_list))
            return 0
        # print('sum(rencheng_list): ', sum(rencheng_list))
        merge_rencheng_meaning_list  = [0] * num_text_list
        for i in range(num_text_list):
            if rencheng_list[i]==1 and meaning_list[i]==1:
                merge_rencheng_meaning_list[i] = 1
            elif rencheng_list[i]==0 and meaning_list[i]==0:
                merge_rencheng_meaning_list[i] = 1
        if sum(merge_rencheng_meaning_list) == num_text_list:
            # print('sum(merge_rencheng_meaning_list): ', sum(merge_rencheng_meaning_list))
            return 0
        # print('sum(merge_rencheng_meaning_list): ', sum(merge_rencheng_meaning_list))

        # 3）所有标签均为语气词，则判为 < 无意义 >；
        if sum(yuqici_list) == num_text_list:
            # print('sum(yuqici_list): ', sum(yuqici_list))
            return 0
        # print('sum(yuqici_list): ', sum(yuqici_list))

        # 4）数组元素标签置换： < 语气词 > 改为 < 无意义 >， < 骂人 > 改为 < 有意义 >， < 人称 > 改为 < 有意义 >；
        # print('before数组元素标签置换: ', meaning_list)

        for i in range(num_text_list):
            if yuqici_list[i]:
                meaning_list[i] = 0
            elif maren_list[i] or rencheng_list[i]:
                meaning_list[i] = 1
        # print('数组元素标签置换: ', meaning_list)

        # 5）有意义的长度之和n1和无意义的长度之和n2，如果n2 / (n1 + n2) > 0.66，则判为 < 无意义 >；
        sum_meaning = 0
        for i in range(num_text_list):
            if meaning_list[i]:
                sum_meaning += len(text_list[i])
        # print('sum_meaning: ', sum_meaning)

        num_tongji = drop_num + len_fenci
        ratio = sum_meaning / 1.0 / num_tongji
        # print('num_tongji: ', num_tongji)
        # print('ratio: ', ratio)
        if ratio <= 0.34:
            return 0

        if len_fenci==2 and sum(biaodian_list)==1:
            for i in range(2):
                if biaodian_list[i] == 0 and len(re.findall(r'[\u4e00-\u9fa5]', text_list[i])) == 1:
                    # print('this this')
                    return 0

        # 6）否则判为 < 有意义 >。
        return 1

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
    # for x in emoji.UNICODE_EMOJI:
    #     if x in text:
    #         text = text.replace(x, "")
    # # print('remove_emoji: ', text)
    return text

def predict_to_file():
    gs = MeaningClassification()
    # path_in = './data/AI边界值2.txt'
    # path_out = './data/AI边界值2_add_flag.txt'
    # path_in = './data/表情.txt'
    # path_out = './data/表情_add_flag.txt'
    # path_in = './data/对话.txt'
    # path_out = './data/对话_add_flag.txt'
    path_in = './data/标注数据0302b.txt'
    path_out = './data/标注数据0302b_add_flag.txt'  #
    # if not os.path.exists(path_out):
    #     os.mkdir(path_out)
    f_in = open(path_in, 'r', encoding='utf-8')
    f_out = open(path_out, 'w', encoding='utf-8')
    count = 1
    for line in f_in.readlines():
        if line == None or line == '\n' or len(line) == 0:
            continue
        # print('fenci: ', list(jieba.cut(line)))
        res = gs.meaning_judge(line)
        # print('res: ', res)
        # print('################################### ', count)
        count += 1
        f_out.write(line[:-1] + '   RESULT: ' + str(res) + '\n')
    f_in.close()
    f_out.close()


if __name__ == '__main__':
    gs = MeaningClassification()
    # s5 = u'丫尺王一博陈总(⊙o⊙)啥？二蛋贼你妈'
    # s5 = u'♫§◎卐'
    # s5 = u'卐♋@◪'
    # s5 = u'弎弎々凵丄'
    # s5 = u'卜了。·'
    s5 = u'你好屌丝'
    res = gs.meaning_judge(s5)
    # print('res: ', res)

    # predict_to_file()
