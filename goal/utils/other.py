import re


def file_loader(file_path):
    with open(file_path, "r", encoding='utf-8') as f:
        data = eval(f.read())
    return data


def remove_punctuation(line):
    line = re.sub(r"\[\d*\]", "", line)
    return re.sub(r'[^\u4e00-\u9fa5^a-z^A-Z^0-9]', '', line)


def save_music(input_path, output_path):
    out = open(output_path, 'w', encoding='utf-8')
    mcs = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for music in f.readlines():
            star, music_list = music.split("\001")
            star = remove_punctuation(star)
            if star in all_star:
                music_list = [remove_punctuation(mc) for mc in music_list.split("\t")]
                mcs += music_list
    mcs = list(set(mcs))
    out.write(str(mcs))
    out.close()


def save_movie(input_path, output_path):
    out = open(output_path, 'w', encoding='utf-8')
    mvs = []
    with open(input_path, "r", encoding='utf-8') as f:
        for movie in f.readlines():
            star, movie_list = movie.split("\001")
            star = remove_punctuation(star)
            if star in all_star:
                movie_list = [remove_punctuation(mv) for mv in movie_list.split("\t")]
                mvs += movie_list

    mvs = list(set(mvs))
    out.write(str(mvs))
    out.close()


def save_food(input_path, output_path1, output_path2):
    pois, foods = [], []
    with open(input_path, "r", encoding='utf-8') as f:
        for line in f.readlines():
            line = eval(line)
            # city = remove_punctuation(line["city"])
            poi = remove_punctuation(line["shopName"])
            food = remove_punctuation(line["name"])
            pois.append(poi)
            foods.append(food)
    pois = list(set(pois))
    foods = list(set(foods))

    out1 = open(output_path1, 'w', encoding='utf-8')
    out1.write(str(pois))
    out1.close()
    out2 = open(output_path2, 'w', encoding='utf-8')
    out2.write(str(foods))
    out2.close()


if __name__ == '__main__':
    path_prefix = "../data/others/"
    all_star = file_loader(path_prefix + "all_star.txt")
    save_music(path_prefix + "singer2song_with_comment.txt", path_prefix + "all_song.txt")
    save_movie(path_prefix + "final_star2movie.txt", path_prefix + "all_movie.txt")
    save_food(path_prefix + "food_kg_human_filter.json", path_prefix + "all_poi.txt", path_prefix + "all_food.txt")