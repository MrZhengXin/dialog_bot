import json
import nltk
import regex
import re
import datetime
import argparse
import goal_filling
import sacrebleu
import copy

parser = argparse.ArgumentParser(description='input delimiter. [ks]xxx[ks]xxx[ke]xxx[gs]xxx[gs]')
parser.add_argument('--knowledge_sep', type=str, default='φ')
parser.add_argument('--knowledge_end', type=str, default='φ')
parser.add_argument('--conversation_sep', type=str, default='φ')
parser.add_argument('--goal_stage_sep', type=str, default=' ')
parser.add_argument('--bot_in_history', type=bool, default=True, help='whether bot response appear in history')
parser.add_argument('--force_history', type=bool, default=True, help='normally if knowledges were found, no history \
would needed')
parser.add_argument('--max_history_length', type=int, default=128)
parser.add_argument('--max_goal_stage_in_history', type=int, default=2)
parser.add_argument('--train_json', type=str, default='train.json')
parser.add_argument('--train_source_file', type=str, default='train_with_knowledge.src')
parser.add_argument('--train_target_file', type=str, default='train_with_knowledge.zh_CN')

args = parser.parse_args()


eq_relations = {
    '星座': [],
    '血型': [],
    '属相': ['属 啥', '属 什么', ],
    '成就': [],
    '主演': ['谁 演 的'],
    '类型': ['什么 歌'],
    '评论': [],  # ['唱 的 咋样', '评价', '好听 吗'],
    '导演': ['谁 导 的'],
    '简介': ['介绍', '信息'],
    '演唱': ['谁 唱 的', '主唱', '谁 的 歌'],
    '身高': ['多高', '多 高'],
    '体重': ['多重'],
    '获奖': ['哪些 奖', '什么 成就'],
    '口碑': [],
    '生日': ['什么 时候 出生', '哪 年 出生', '哪年 出生', '哪一年 出生', '的 出生 ', '出生日期', '多会 出生', '生日 是 多会'],
    '出生地': ['哪里 的 人', '哪儿 的 人', '哪里 出生', '在 哪 出生', '哪儿 出生', '哪 的', '哪里 的 籍贯', '哪里 人', '出生 地区', '出生 在 哪里'],
    '国家地区': ['国家 地区', '哪个 国家'],
    '人均价格': ['人均 价格', '消费 怎么样', '人均 消费', '平均价格'],
    '地址': ['在 哪', '具体位置', '什么 地方'],
    '评分': ['多少 分'],
    '特色菜': [],
    '日期': [],  # '问 日期' in goal[0]
    '时间': [],  # '问 时间' in goal[0]
    '新闻': ['故事'],
    '天气': []
}
actors = {'范冰冰', '黄晓明', '谢娜', '吴亦凡', '王力宏', '黄渤', '林心如', '杨幂', '周迅', '成龙', '刘若英', '舒淇', '张学友', '张柏芝', '刘德华', '郭富城', '周杰伦', '张国荣', '林志颖', '何炅', '谢霆锋'}

difficult_info_mask = {'身高': 'height', '体重': 'weight', '评分': 'rating', '地址': 'address', '特色菜': 'special',
                       '人均价格': 'expense', '导演': 'director', '姓名': 'name', '星座': 'constellation',
                       '血型': 'bloodtype', '出生地': 'birthplace', '生日': 'birthday', '国家地区': 'region', '属相': 'zodiac'}


def validate_date(date_text):
    try:
        datetime.datetime.strptime(date_text, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def check_relation(rel, qa):
    possible_rel = (eq_relations[rel] if rel in eq_relations.keys() else []) + [rel]
    for r in possible_rel:
        if r in qa:
            return True
    return False


def cal_score(triple, q, a):
    """
    calculate if the triple(entity, relation, something) appears in the questions and answer
    """

    if len(triple[2]) == 0 or len(triple[3]) == 0:
        return 0  # something empty like ["异灵灵异-2002", "评论", ""]
    qa = q + ' ' + a
    score = 1 if (triple[0].replace(' ', '') in qa.replace(' ', '') or ('天气' == triple[1] and '天气' in q)) else 0  # left entity appears
    score += check_relation(triple[1], qa)  # relation appears
    if triple[1] == '出生地' and score < 2:
        score -= 4  # probably not use birthplace knowledege
    if triple[2] in a:  # something directly appears
        score += 2
    else:
        bleu = sacrebleu.corpus_bleu([a], [[triple[2]]]).score
        if bleu > 10:
            score += 2
        else:
            score -= 2

    return score


with open(args.train_json, 'r') as f:
    x = f.readlines()


src = open(args.train_source_file, 'w')
tgt = open(args.train_target_file, 'w')
len_src = 0
len_tgt = 0


news_response = dict()
news_chat = dict()
select_comments_dict = dict()
comments_score = dict()
problembatic_entity = dict()
line_no = 0
comment_recommends = dict()
celebrity_chat = dict()
dataset_bug_movies = set()
for i in x:
    line_no += 1
    i = json.loads(i)
    conversation = i['conversation']
    # conversation = [c + ' 。' if c[-1] not in ['！', '？', '。'] else c for c in conversation]
    conversation = [c.replace(i['user_profile']['姓名'], 'name') for c in conversation]  # replace user's name

    goal = i['goal'].split(' --> ')
    kg = i['knowledge']

    # fix bug when song contain "   "
    for j in range(len(kg)):
        if kg[j][1] != '评论' and '评论' in kg[j][1]:
            kg[j][0] += ' ' + kg[j][1].replace(' 评论', '')
            kg[j][1] = '评论'

    # entity replacement

    entity_cnt = 0
    entity_dict = dict()
    goal_info = [goal_filling.extract_info_from_goal(g) for g in goal] if '--> ...... -->' not in goal else goal_filling.fill_test(i)
    
    if len(set(re.findall('\[[1-9]\]', ''.join(conversation)))) != len(goal_info):  # bug at goal marks
        continue


    for gi in range(len(goal_info)):
        if goal_info[gi][1] in ['问 时间', '问 日期']:  # add time in goal
            goal_info[gi].append(i['situation'])
            continue

        if goal_info[gi][1] in ['天气 信息 推送', '问 天气']:  # add weather in goal
            for k in kg:
                city, thedate, weather = k
                if validate_date(thedate):
                    goal_info[gi].append(city)
                    goal_info[gi].append(weather)
                    break
            continue

        if len(goal_info[gi]) != 3 or goal_info[gi][1] not in ['美食 推荐', '兴趣点 推荐', '电影 推荐', '播放 音乐', '音乐 推荐', '音乐 点播']:
            continue

        if goal_info[gi][1] == '播放 音乐':  # play the last recommend song
            goal_info[gi][2] = entity_dict[goal_info[gi][2]]
            continue

        entities = goal_info[gi][2] if type(goal_info[gi][2]) is type(list()) else [goal_info[gi][2]]
        goal_info_enrich = []
        entity_cnt += len(entities)

        # solve recuresive　name like 欺诈 的 碎片 与 惊心 的 情感 ： 《 色 · 戒 》 纪实 and 色 · 戒
        for entity in entities[::-1]:
            # no redundant entity
            if entity in entity_dict.keys():
                continue
            entity_no = ''
            if '美食 推荐' == goal_info[gi][1]:
                entity_cnt -= 1
                entity_no = 'special_' + str(entity_cnt)
            if '兴趣点 推荐' == goal_info[gi][1]:
                entity_cnt -= 1
                entity_no = 'restaurant_' + str(entity_cnt)
            if '电影 推荐' == goal_info[gi][1]:
                entity_cnt -= 1
                entity_no = 'movie_' + str(entity_cnt)
                has_acting_knowledge = False
                for k in kg:
                    if k[2] == entity and k[1] == '主演':
                        has_acting_knowledge = True
                        break
                if not has_acting_knowledge:
                    # print(entity)
                    dataset_bug_movies.add(entity)
            if goal_info[gi][1] in ['音乐 推荐', '音乐 点播']:
                entity_cnt -= 1
                entity_no = 'song_' + str(entity_cnt)
            if entity_no == '':
                continue
            entity_dict[entity] = entity_no

            entity_appear = False
            for j in range(len(conversation)):
                if entity in conversation[j]:
                    entity_appear = True
                    conversation[j] = conversation[j].replace(entity, entity_no)
            if not entity_appear:
                if entity not in problembatic_entity.keys():
                    problembatic_entity[entity] = [line_no]
                else:
                    problembatic_entity[entity].append(line_no)

            comment_lists = list()
            info_lists = [entity_no]
            for j in range(len(kg)):
                if kg[j][0].replace(' ', '') == entity.replace(' ', ''):
                    if kg[j][0].replace(' ', '') + ':' == kg[j][2].replace(' ', ''):  # avoid comments like "["亚飞与亚基", "评论", "亚飞与亚基 :"]"
                        continue
                    kg[j][0] = entity_no
                    kg[j][2] = kg[j][2].replace(entity, entity_no)
                    if goal_info[gi][1] in ['音乐 推荐', '电影 推荐']:  # collect all comments to this entity
                        comment_lists.append(kg[j][2])
                        if kg[j][1] in ['主演', '类型', '口碑']:
                            info_lists.append(kg[j][1:])
            if type(goal_info[gi][2]) is type(str()):
                goal_info[gi][2] = entity_no
                continue
            # find which comment is used by calculate sacrebleu
            if goal_info[gi][1] in ['音乐 推荐', '电影 推荐']:
                used_comment = ''
                max_bleu = -1.0
                # but first, need to find which sentence this comment appear
                appear_response = ''
                for c in conversation:
                    if entity_no in c:
                        appear_response = c
                        break
                
                for c in comment_lists:
                    bleu = sacrebleu.corpus_bleu([appear_response], [[c]]).score
                    if bleu > max_bleu:
                        max_bleu = bleu
                        used_comment = c[:48]

                info_lists.append(['评价', used_comment])
                goal_info_enrich.append(info_lists)

                # print(entity_no, info_lists)
                # input()
        if len(goal_info_enrich) != 0:
            goal_info[gi][2] = goal_info_enrich[::-1]



        entity_cnt += len(entity_dict)

    # print(goal_info)
    # input()


    user_first = True if 'User 主动' in goal[0] else False
    bot_hello = False
    if '寒暄' in goal[0]:
        bot_hello = True
        hello_info = ['寒暄', i['situation']]
        if '带 User 名字' in goal[0]:
            hello_info.append('name')
            hello_info.append(i['user_profile']['性别'])
            if '年龄区间' in str(i['user_profile']):
                hello_info.append(i['user_profile']['年龄区间'])
        print(*hello_info, file=src, sep=args.knowledge_sep, end='')
        print(args.knowledge_end, file=src)
        len_src += 1

    # add reverse knowledge
    # for j in range(len(kg)):
        # if kg[j][1] in ['生日', '演唱', '导演', '主演', '星座']:
            # kg.append([kg[j][2], kg[j][1], kg[j][0]])

    for j in range(len(kg)):

        if validate_date(kg[j][1]):
            kg[j][1] = '天气'  # weather knowledge relation always in date form

        if kg[j][1] == '生日':
            digits = kg[j][2].split('-')
            kg[j][2] = digits[0] + '年' + digits[1] + '月' + digits[2]

        if kg[j][1] in ['评论']:
            kg[j].append(re.split('[！？，。]', kg[j][2]))  # result example ["高中 时候 很 喜欢 他 的 歌 ", " 后面 就 只是 关注 他 的 生活 了 。"]
        else:
            if kg[j][1] == '出生地':
                kg[j].append(kg[j][2].split('   '))  # input example ["谢娜", "出生地", "中国   四川   德阳   中 江"]
            else:
                kg[j].append(kg[j][2].split(' '))  # match by words

        for k in kg[j][3]:
            if k in ['', ' ', '，', '。', '！', '。', '~', '-'] or\
            (len(kg[j][2]) > 4 and len(k) < 4 and kg[j][1] in ['评论']):  # unhelpful in matching
                kg[j][3].remove(k)



    if len(goal) == 0:
        continue

    used_k = set()  # used string-format knowledge tuple in previous conversation

    goal_stage_milestone = set()
    for j in range(len(conversation)-1):
        if conversation[j][0] == '[':
            goal_stage_milestone.add(j)
            current_goal_stage = len(goal_stage_milestone)
            if current_goal_stage == len(goal_info):
                current_goal_stage -= 1
            # conversation[j] = conversation[j][4:]
        using_k = set()  # bot need these knowledge tuples to answer
        user_round = user_first ^ (j & 1)  # True if it were user speaking

        # if not user_round:
            # for k, v in zip(entity_dict.keys(), entity_dict.values()):
                # valid[0] = valid[0].replace(v, k)
            # print(valid[0].strip(), file=valid_entity)
            # valid = valid[1:]

        qa = conversation[j].strip() + ' ' + conversation[j + 1].strip()
        history = ' '.join(conversation[:j])

        

        # print(recommend_item, goal_info[current_goal_stage-1:current_goal_stage+1], entity_dict, qa)
        for k in kg:
            if str(k[:3]) in used_k or k[1] == '评论' or k[1] == '新闻':  # assume that no knowledge will be used twice
                continue

            if k[1] == '导演' and '   ' in k[2]:  # ["喜剧之王", "导演", "周星驰   李 力持"]
                k[2] = k[2].replace('   ', ' ， ')
            if k[1] == '出生地':
                k[2] = k[2].replace('   ', ' ')
            k[2] = k[2].replace('_ 金像奖 - ', '').replace(' _ ', '')  # ["张柏芝", "获奖", "香港电影 金像奖 _ 金像奖 - 最佳 原创 电影 歌曲 奖"], ["张柏芝", "获奖", "华语 电影 传媒 大奖 _ 最佳 女演员"]

            score = cal_score(k, history + ' ' + conversation[j].strip(), conversation[j+1].strip())


            if score > max(2, cal_score(k, history, conversation[j].strip())):  # this knowledge might appear and not appear before
                
                if k[1] == '新闻':  # collect how bot broadcast news
                    news_response[k[2]] = conversation[j+1]
                    # print(k[2], conversation[j+1])

                if k[1] in difficult_info_mask.keys() and user_round:
                    def matching_pattern(info):
                        return '(^'+info+')|( '+info + ' )|( ' + info + '$)'

                    replace_mask = ' ' + (k[0] if k[0] not in actors and 'restaurant' not in k[0] else '') + "'" + difficult_info_mask[k[1]] + ' '

                    conversation[j+1] = re.sub(matching_pattern(k[2]), replace_mask, conversation[j+1])
                    if k[1] == '生日':
                        conversation[j+1] = re.sub(matching_pattern(k[2]), replace_mask, conversation[j+1])
                        if replace_mask not in conversation[j+1]:
                            conversation[j + 1] = re.sub(matching_pattern(k[2][7:]), replace_mask, conversation[j + 1])
                            if replace_mask not in conversation[j + 1]:
                                print(k[2], conversation[j+1])
                    if k[1] == '出生地':
                        conversation[j+1] = re.sub(matching_pattern(k[2]), replace_mask, conversation[j+1])
                        if replace_mask not in conversation[j+1]:
                            conversation[j+1] = re.sub(matching_pattern(k[2].replace('中国 ', '')), replace_mask, conversation[j+1])
                        if replace_mask not in conversation[j+1]:
                            conversation[j+1] = re.sub(matching_pattern(k[2].replace(' ', '')), replace_mask, conversation[j+1])


                        if replace_mask not in conversation[j+1]:
                            print(k[2], conversation[j+1])
                            input()
                    # print(k, conversation[j+1])
                    # input()
                    continue
                        
                        

                    # print(k[2], conversation[j+1])
                    # input()
                    # conversation[j+1].replace(' ' + k[2] + ' ', ' ' + difficult_info_mask[k[1]] + ' ')
                    # print(conversation[j+1])
                    # k[2] = k[0] + '_' + difficult_info_mask[k[1]]
                

                used_k.add(str(k[:3]))
                if user_round:  # we only need simulate bot
                    using_k.add(str(k[:3]))  # using sest to remove redundant tuple such as multiple celebrity birthday



        if user_round:
            # add goal transition
            goal_transition = copy.deepcopy(goal_info[current_goal_stage - 1:current_goal_stage + 1])
            if '新闻' in goal_transition[0][1]:
                goal_transition[0][3] = goal_transition[0][3].replace(' ', '')[:128]
            if len(goal_transition) > 1 and '新闻' in goal_transition[1][1]:
                goal_transition[1][3] = goal_transition[1][3].replace(' ', '')[:128]

            # add knowledge about celebrity in goal
            if len(using_k) > 0 and ((goal_transition[0][1] == '关于 明星 的 聊天' and conversation[j+1][0] != '[')or \
                (len(goal_transition) > 1 and goal_transition[1][1] == '关于 明星 的 聊天' and conversation[j+1][0] == '[')):
                pos = 0 if goal_transition[0][1] == '关于 明星 的 聊天' else 1
                goal_transition[pos] += [eval(uk)[1:] for uk in using_k]

            print(*goal_transition, end=args.knowledge_end, sep=args.knowledge_sep, file=src)
            if 0 < j and args.force_history:  # add history
                add_history = []
                pos_h = j - 1
                delta_goal_stage = 0
                while len(' '.join(add_history) + conversation[pos_h]) < args.max_history_length and pos_h >= 0:
                    add_history.append(conversation[pos_h].strip()[:36])
                    if pos_h in goal_stage_milestone:
                        add_history[-1] += args.goal_stage_sep
                        delta_goal_stage += 1
                        if delta_goal_stage >= args.max_goal_stage_in_history:
                            break
                    pos_h -= 1
                # add_history = [c + ' 。' if c[-1] not in ['！', '？', '。'] else c for c in add_history]
                print(*add_history[::-1], sep=args.conversation_sep, end=args.conversation_sep, file=src)
        print(conversation[j] + args.goal_stage_sep, file=src if user_round else tgt)
        if user_round:
            len_src += 1
        else:
            len_tgt += 1
    if len_tgt == len_src - 1:
        print(conversation[-1], file=tgt)  # when bot say goodbye first, user's goodbye would be ignored.
        len_tgt += 1

    assert len_src == len_tgt
