import json
import nltk
import regex
import re


def cal_score(triple, q, a):
    '''
    calculate if the triple(entity, relation, something) appears in the questions and answer
    '''
    qa = q + ' ' + a
    score = 1 if triple[0] in qa else 0  # left entity appears
    score += 1 if triple[1] in qa else 0  # relation appears
    if triple[2] in qa:  # something directly appears
        score += 2
    else:
        if '评论' != triple[1]:
            common_words = [word for word in triple[3] if (word in qa and word not in ['', ' '])]  # match by word
        else:
            common_words = [word for word in triple[3] if (word in a and word not in ['', ' '])]  # match by sub sentences
        if len(common_words) / len(triple[3]) > 0.4 or (len(common_words) > 0 and triple[1] in ['评论', '出生地']):  # comments and birth places are more loose
            score += 2
        else:
            score -= 2

    return score

with open('train.json', 'r') as f:
    x = f.readlines()


src = open('dialog_with_knowledge.src', 'w')
tgt = open('dialog_with_knowledge.tgt', 'w')
len_src = 0
len_tgt = 0

for i in x:
    i = json.loads(i)
    conversation = i['conversation']
    goal = i['goal'].split('-->')
    user_first = True if 'User 主动' in goal[0] else False
    bot_hello = False
    if '寒暄' in goal[0]:
        bot_hello = True
        hello_info = ['寒暄', i['situation']]
        if '带 User 名字' in goal[0]:
            hello_info.append(i['user_profile']['姓名'])
            hello_info.append(i['user_profile']['性别'])
            if '年龄区间' in str(i['user_profile']):
                hello_info.append(i['user_profile']['年龄区间'])
        print(hello_info, file=src)
        len_src += 1
    kg = i['knowledge']
    for j in range(len(kg)):
        if kg[j][1] == '评论':
            kg[j].append(re.split('[！？，。]', kg[j][2]))  # result example ["高中 时候 很 喜欢 他 的 歌 ", " 后面 就 只是 关注 他 的 生活 了 。"]
        else:
            if kg[j][1] == '出生地':
                kg[j].append(kg[j][2].split('   '))  # input example ["谢娜", "出生地", "中国   四川   德阳   中 江"]
            else:
                kg[j].append(kg[j][2].split(' '))  # match by words

        for k in kg[j][3]:
            if k in ['', ' ', '，', '。', '！', '。', '~', '-', '好 的 '
                                                            '', '啊', '哦', '']:  # unhelpful in matching
                kg[j][3].remove(k)

    if len(goal) == 0:
        continue

    used_k = set()  # used string-format knowledge tuple in previous conversation

    for j in range(len(conversation)-1):
        using_k = set()  # bot need these knowledge tuples to answer
        user_round = user_first ^ (j & 1)  # True if it were user speaking
        qa = conversation[j].strip() + ' ' + conversation[j + 1].strip()
        history = ' '.join(conversation[:j])
        for k in kg:
            if str(k) in used_k:  # assume that no knowledge will be used twice
                continue
            score = cal_score(k, history + ' ' + conversation[j].strip(), conversation[j+1].strip())


            if score > max(1, cal_score(k, history, conversation[j].strip())):  # this knowledge might appear and not appear before
                if user_round:  # we only need simulate bot
                    using_k.add(str(k[:3]))  # using sest to remove redundant tuple such as multiple celebrity birthday
                    if score > 2:
                        used_k.add(str(k[:3]))  # the knowledge is fully explored
                        #  consider the celebrity birthday cases.
                        #  First, the date today is asked and answered. However,
                        #  the celebrity birthday tuple would also be partially matched.
                        #  So the tuple cannot be treated as used knowledge.
        if len(using_k) != 0 and user_round:
            print(*using_k, end='\t', file=src)  # knowledge at the beginning of user question
        print(conversation[j], file=src if user_round else tgt)
        if user_round:
            len_src += 1
        else:
            len_tgt += 1
    if len_tgt == len_src - 1:
        print(conversation[-1], file=tgt)  # when bot say goodbye first, user's goodbye would be ignored.
        len_tgt += 1
    assert len_src == len_tgt
