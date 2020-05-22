import re

from .model import GoalPlanning
from .config import Config

goal_planning = GoalPlanning(Config())

actors = {'范冰冰', '黄晓明', '谢娜', '吴亦凡', '王力宏', '黄渤', '林心如', '杨幂', '周迅', '成龙', '刘若英', '舒淇', '张学友', '张柏芝', '刘德华', '郭富城', '周杰伦', '张国荣', '林志颖', '何炅', '谢霆锋'}
dataset_bug_movies = {'金鸡2', '亚飞与亚基', '倩女幽魂Ⅲ：道道道', '城市猎人', '地球四季', '中国合伙人', '笑傲江湖', '救火英雄', '旺角黑夜', '男人四十', '无问西东', '太平轮·彼岸', '男儿本色', '新警察故事', '十二夜', '逆战', '太平轮（上）', '消失的子弹', '李米的猜想', '证人', '亚飞与亚基', '叶问2：宗师传奇', '忘不了', '苏州河', '钟无艳', '暴疯语', '鸳鸯蝴蝶', '金鸡2', '白兰', '线人', '情迷大话王', '异灵灵异-2002'}
ask_user_type = ['问User姓名', '问User性别', '问User年龄', '问User爱好']


def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return eval(f.read())

type2idx = read_file("goal_fill/type/goal_type_dict.txt")
idx2type = list(type2idx.keys())
type_nb = read_file("goal_fill/type/goal_type_neighbour.txt")

def get_goal_type_entity(goal):
    kg_flag = ["参考知识"]
    flag1 = ["关于明星的聊天", "音乐推荐", "播放音乐", "美食推荐",
             "电影推荐", "音乐点播", "问日期", "提问", "兴趣点推荐"]  # 一个关键词
    flag2 = ["问答"]  # 两个关键词
    flag_news = ["新闻推荐", "新闻点播"]

    type = goal.split(']', 1)[-1].split('(', 1)[0].replace(' ', '')

    if "『" and "』" not in goal or type == "问日期":
        entity = type
    elif type in flag1:
        entity = goal.split("『", 1)[-1].split("』", 1)[0].replace(' ', '')  # 由『』给出的第一个关键词
    elif type in flag2:
        entity1 = goal.split("『", 1)[-1].split("』", 1)[0].replace(' ', '')
        entity2 = goal.split("『", -1)[-1].split("』", -1)[0].replace(' ', '')

        if entity1 not in kg_flag:
            entity = entity1
        else:
            entity = entity2
    elif type in flag_news:
        entity = goal.split("『")[-1].split("』", 1)[0].replace(' ', '')
    else:
        entity = type

    # type = type.replace("User", "用户")
    # entity = entity.replace("User", "用户")
    return type, entity


def predict_goal(data):
    goals = data['goal'].split("-->")
    goals = [goal.strip() for goal in goals]

    first_goal, final_goal = goals[0], goals[-2]
    first_type, first_entity = get_goal_type_entity(first_goal)
    final_type, final_entity = get_goal_type_entity(final_goal)

    dialog_idx_seq = []
    type_seq = [type2idx[first_type]]
    entity_seq = [first_entity]

    cur_id = 2
    max_id = re.findall("\[(\d*)\]", final_goal)[0]
    max_id = int(max_id)

    # find candidate entities
    kg = data['knowledge']
    accept_movies = data['user_profile']['接受 的 电影'] if '接受 的 电影' in data['user_profile'].keys() else {}
    accept_movies = [m.replace(' ', '') for m in accept_movies]
    accept_songs = data['user_profile']['接受 的 音乐'] if '接受 的 音乐' in data['user_profile'].keys() else {}
    accept_songs = [s.replace(' ', '') for s in accept_songs]
    like_movies = data['user_profile']['喜欢 的 电影'] if "喜欢 的 电影" in data['user_profile'].keys() else {}
    like_movies = [m.replace(' ', '') for m in like_movies]
    like_songs = data['user_profile']['喜欢 的 音乐'] if "喜欢 的 音乐" in data['user_profile'].keys() else {}
    like_songs = [s.replace(' ', '') for s in like_songs]

    songs = list()
    movies = list()
    restaurant = list()
    likes = list()
    stars = list()
    birthday_person = ''
    singer = ''
    news_of = ''
    news = ''
    actor = ''
    food = ''
    if "同意 的 美食" in data['user_profile'].keys():
        food = data['user_profile']['同意 的 美食'].replace(' ', '')

    for j in kg:
        entity, relation, info = j
        entity = entity.replace(' ', '')
        info = info.replace(' ', '')
        if "喜欢" in relation:
            if info not in likes:
                likes.append(info)
        if relation == '新闻' and \
                first_entity != info and final_entity != info:
            news_of, news = entity, info
        if relation == '演唱' and info not in first_goal and info not in accept_songs:
            if info not in songs and info not in like_songs:
                songs.append(info)
            singer = entity
            if singer not in stars:
                stars.append(singer)
        if relation == '生日':
            birthday_person = entity
            if birthday_person not in stars:
                stars.append(birthday_person)
        if relation == '主演' and entity in actors:  # avoid sth like ["星月童话", "主演", "张国荣   常盘贵子"]
            if info not in movies \
                    and info not in first_goal.replace(' ', '') and info not in final_goal.replace(' ', ''):
                movies.append(info)
            actor = entity
            if actor not in stars:
                stars.append(actor)
        if relation == '地址':
            restaurant.append(entity)
        if relation == '评论' and entity.replace(' ', '') in dataset_bug_movies \
                and entity not in movies and entity not in songs and entity not in actors \
                and entity.replace(' ', '') not in first_goal.replace(' ', '') and entity.replace(' ', '') not in final_goal.replace(' ', ''):  # dataset bug: no acting knowledge
            movies.append(entity)
            # print(entity)

    # if size of items is more than two, delete accepted item
    movies = [m for m in movies if (m not in accept_movies and m not in like_movies)]
    songs = [s for s in songs if (s not in accept_songs and s not in like_songs)]

    if final_type == "播放音乐":
        songs.remove(final_entity)
        # songs.append(final_entity)

    movie_idx, song_idx, like_idx, star_idx, news_used, food_used = 0, 0, 0, 0, False, False
    while cur_id < max_id:
        dialog_idx_seq.append(cur_id)
        cur_id += 1

        # type
        next_type, next_type_prob = None, 0
        last_type_id = type_seq[-1]
        for nb in type_nb[last_type_id]:
            nb_name = idx2type[nb]
            last_type_name = idx2type[last_type_id]
            # filter
            if final_type in ask_user_type and nb_name not in ask_user_type:
                continue
            if final_type not in ask_user_type and nb_name in ask_user_type:
                continue
            if final_type == nb_name or nb in type_seq:
                # if not ((final_type == "电影推荐" and nb_name == "电影推荐") or nb_name == "音乐推荐"):
                if nb_name not in ['电影推荐', '音乐推荐']:
                    continue
            # if final_type == "播放音乐" and cur_id != max_id and nb_name == "音乐推荐":
            #     continue
            if len(type_nb[last_type_id]) > 2:
                if nb_name in ['再见', '寒暄', '播放音乐']:
                    continue
                if nb_name == "关于明星的聊天" and (len(stars) == 0 or star_idx >= len(stars)):
                    continue
                if nb_name == "音乐推荐" and (len(songs) == 0 or song_idx >= len(songs)):
                    continue
                if nb_name == "电影推荐" and (len(movies) == 0 or movie_idx >= len(movies)):
                    continue
                if nb_name == "新闻推荐" and (news == "" or news_used == True):
                    continue
                if nb_name == "美食推荐" and (food == "" or food_used == True):
                    continue
                if nb_name == "提问" and (len(likes) == 0 or like_idx >= len(likes)):
                    continue

            past_type_seq = type_seq + [nb]
            prob = goal_planning.goal_type_infer(past_type_seq, nb, type2idx[final_type])
            if prob > next_type_prob:
                next_type_prob = prob
                next_type = nb

        if last_type_name == "提问" and len(likes) > 0 and like_idx < len(likes):
            next_type = type2idx["提问"]
        if cur_id == max_id and final_type == "播放音乐":
            next_type = type2idx["音乐推荐"]
            type_seq.append(next_type)
            entity_seq.append([final_entity])
            continue

        if next_type == None:
            if len(likes) > 0 and like_idx < len(likes):
                next_type = "提问"
            if len(stars) > 0 and star_idx < len(stars):
                next_type = "关于明星的聊天"
            elif len(songs) > 0 and song_idx < len(songs):
                next_type = "音乐推荐"
            elif len(movies) > 0 and movie_idx < len(movies):
                next_type = "电影推荐"
            elif news != "" and news_used == False:
                next_type = "新闻推荐"
            elif food != "" and food_used == False:
                next_type = "美食推荐"
            next_type = type2idx[next_type]

        type_seq.append(next_type)

        # entity
        next_entity = [[]]
        next_type_name = idx2type[next_type]
        if next_type_name in ['新闻点播', '播放音乐', '音乐点播', '兴趣点推荐', '天气信息推送', '寒暄', '再见', '问日期', '问天气', '问时间', '问答', '问用户爱好', '问用户年龄', '问用户性别', '问用户姓名']:
            next_entity = [[]]
        elif next_type_name == "电影推荐":
            next_entity = [[movies[movie_idx]]]
            movie_idx += 1
        elif next_type_name == "音乐推荐":
            next_entity = [[songs[song_idx]]]
            song_idx += 1
        elif next_type_name == "提问":
            like_info = likes[like_idx]
            for key, value in data['user_profile'].items():
                if "喜欢" not in key:
                    continue
                if isinstance(value, list):
                    for v in value:
                        if like_info in v.replace(' ', ''):
                            next_entity = [key]
                            break
                elif like_info in value.replace(' ', ''):
                    next_entity = [key]
                    break
            like_idx += 1
        elif next_type_name == "关于明星的聊天":
            next_entity = [stars[star_idx]]
            star_idx += 1
        elif next_type_name == "新闻推荐":
            next_entity = [[news_of, news]]
            news_used = True
        elif next_type_name == "美食推荐":
            next_entity = [food]
            food_used = True

        entity_seq += next_entity

    type_seq = [idx2type[idx] for idx in type_seq]
    goal_fill = []
    for i in range(len(dialog_idx_seq)):
        goal_fill.append([dialog_idx_seq[i], type_seq[i + 1], entity_seq[i + 1]])
    # goal_fill = list(zip(dialog_idx_seq, type_seq[1:], entity_seq[1:]))
    for i in range(len(goal_fill)):
        if goal_fill[i][-1] == []:
            goal_fill[i] = goal_fill[i][:-1]
        if goal_fill[i][1] == "新闻推荐":
            goal_fill[i] = goal_fill[i][:-1] + goal_fill[i][-1]
    return goal_fill
