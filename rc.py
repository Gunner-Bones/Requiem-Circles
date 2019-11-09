import sys
import urllib.request
import json
import math
import discord
import random
import asyncio
import datetime
from discord.ext import commands

Client = discord.Client()
bot_prefix = "??"
client = commands.Bot(command_prefix=bot_prefix)
client.remove_command("help")

s = None
try:
    s = open("pass.txt", "r")
except FileNotFoundError:
    sys.exit("[Error] pass.txt needed for Secret")
sl = []
for l in s:
    sl.append(l.replace("\n", ""))
SECRET = sl[0]
FILE_PLAYERS = "players.csv"
FILE_DEMONS = "demons.csv"
FILE_ROLES = "roles.csv"
FILE_PC_DATA = "pc_data.txt"
FILE_WHITELIST = 'whitelist.txt'
INVITE_DLP = 'https://discord.gg/VkrsU3W'
CHAR_SUCCESS = "✅"
CHAR_FAILED = "❌"
CHAR_SENT = "📨"


def is_number(st):
    try:
        st = int(st)
        st += 1
    except ValueError:
        return False
    return True


def points_formula(completion) -> float:
    pgr = 100
    pos = 1
    rq = 50
    if type(completion) == Record:
        pgr = completion.progress
        pos = completion.demon.position
        rq = completion.demon.requirement
    elif type(completion) == Demon:
        pgr = 100
        pos = completion.position
        rq = completion.requirement
    if pos >= 151:
        return 0.0
    if pos >= 76 and pgr < 100:
        return 0.0
    if pgr == 100:
        return 150.0 * math.exp((1.0 - pos) * math.log(1.0 / 30.0) / (-149.0))
    else:
        return 150.0 * math.exp((1.0 - pos) * math.log(1.0 / 30.0) / (-149.0)) * (0.25 * (pgr - rq) / (100 - rq) + 0.25)


class Player(object):
    def __init__(self, name: str, pid: int, did="NONE", records=None, verified=None, published=None, created=None):
        if records is None:
            records = []
        self.name = name
        self.pid = pid
        self.did = did
        self.records = records
        self.verified = verified
        self.published = published
        self.created = created
        self.points = 0
        self.calculate_points()

    def calculate_points(self):
        if len(self.records) > 0:
            c_points = 0
            for record in self.records:
                add_points = points_formula(record)
                c_points += add_points
            if self.verified:
                for demon in self.verified:
                    add_points = points_formula(demon)
                    c_points += add_points
            self.points = c_points

    def add_record(self, record):  # record: Record
        self.records.append(record)

    def remove_record(self, record):  # record: Record
        try:
            self.records.remove(record)
        except ValueError:
            pass

    def __str__(self):
        return "<Player> Name:" + self.name + " PID:" + str(self.pid) + " Points:" + str(self.points)


class Demon(object):
    def __init__(self, pid: int, name: str, position: int, requirement: int, publisher=None, verifier=None):
        self.name = name
        self.position = position
        self.requirement = requirement
        self.publisher = publisher
        self.verifier = verifier
        self.pid = pid

    def __str__(self):
        return "<Demon> Name:" + self.name + " Position:" + str(self.position) + " PID:" + str(self.pid) + \
               " Requirement:" + str(self.requirement)


class Record(object):
    def __init__(self, demon: Demon, progress: int, rid: int, player=None):
        self.demon = demon
        self.player = player
        self.progress = progress
        self.rid = rid

    def __str__(self):
        return "<Record> Demon:" + str(self.demon) + " Player:" + str(self.player) + " Progress:" + str(self.progress) \
               + " RID:" + str(self.rid)


# 'published': [{'id': 72, 'name': 'MadMansion', 'position': 70}],
# 'records': {'demon': {'id': 143, 'name': 'Allegiance', 'position': 156}, 'id': 7369, 'progress': 100
#  ,'status': 'approved', 'video': 'https://www.youtube.com/watch?v=p5NHYDpGMrw'}
# 'verified': [{'id': 72, 'name': 'MadMansion', 'position': 70}]


def condense_dict(i_dic, obj_type: str) -> str:
    if obj_type in ['player_published', 'player_verified', 'player_created']:  # DEMON_ID:DEMON_NAME:DEMON_POS
        return str(i_dic.pid) + ":" + i_dic.name + ":" + str(i_dic.position) + ":" + str(i_dic.requirement)
    if obj_type == 'player_record':  # DEMON_ID:DEMON_NAME:DEMON_POS:RID:PROGRESS:STATUS
        return str(i_dic.demon.pid) + ":" + i_dic.demon.name + ":" + str(i_dic.demon.position) + ":" + \
               str(i_dic.rid) + ":" + str(i_dic.progress) + ":" + str(i_dic.demon.requirement)
    if obj_type == 'role_demons':
        r_str = ''
        for d in i_dic:
            r_str += d.name + ":"
        return r_str[:-1]
    if obj_type == 'role_positional':
        return str(i_dic[0]) + ":" + str(i_dic[1]) + ":" + str(i_dic[2])
    if obj_type == 'role_counter':
        return i_dic[0] + ":" + str(i_dic[1])


def unpack_dict(i_str: str, obj_type: str):
    if obj_type in ['player_published', 'player_verified', 'player_created']:
        unp_str = i_str.split(":")
        demon_off_list = True
        for dl in DEMON_LIST.ls:
            if str(dl.pid) == unp_str[0]:
                demon_off_list = False
                if unp_str[2] != str(dl.position):
                    unp_str[2] = str(dl.position)
                break
        if demon_off_list:
            unp_str[2] = str(200 + random.randint(1, 50))  # placeholder position for levels moved to legacy
            unp_str.append('100')
        if len(unp_str) == 3:
            if int(unp_str[2]) > 150 and not demon_off_list:
                unp_str.append('100')
            else:
                for dl in DEMON_LIST.ls:
                    if str(dl.pid) == unp_str[0]:
                        unp_str.append(str(dl.requirement))
                        break
        return Demon(name=unp_str[1], pid=int(unp_str[0]), position=int(unp_str[2]), requirement=int(unp_str[3]))
    if obj_type == 'player_record':
        unp_str = i_str.split(":")
        demon_off_list = True
        for dl in DEMON_LIST.ls:
            if str(dl.pid) == unp_str[0]:
                demon_off_list = False
                if unp_str[2] != str(dl.position):
                    unp_str[2] = str(dl.position)
                    break
        if demon_off_list:
            unp_str[2] = str(200 + random.randint(1, 50))  # placeholder position for levels moved to legacy
            unp_str.append('100')
        if len(unp_str) == 5:
            if int(unp_str[2]) > 150 and not demon_off_list:
                unp_str.append('100')
            else:
                for dl in DEMON_LIST.ls:
                    if str(dl.pid) == unp_str[0]:
                        unp_str.append(str(dl.requirement))
                        break
        return Record(demon=Demon(pid=int(unp_str[0]), name=unp_str[1], position=int(unp_str[2]),
                                  requirement=int(unp_str[5])), rid=int(unp_str[3]), progress=int(unp_str[4]))
    if obj_type == 'role_demons':
        if ':' not in i_str:
            unp_str = [i_str]
        else:
            unp_str = i_str.split(":")
        for d in unp_str:
            unp_str[unp_str.index(d)] = d.lower()
        unp_demons = []
        for ld in DEMON_LIST.ls:
            if ld.name.lower() in unp_str:
                unp_demons.append(ld)
        return unp_demons
    if obj_type == 'role_positional':
        unp_str = i_str.split(":")
        return [int(u) for u in unp_str]
    if obj_type == 'role_counter':
        unp_str = i_str.split(":")
        return [unp_str[0], int(unp_str[1])]


def pc_to_obj(i_dic: dict, obj_type: str):
    if obj_type == "record":
        return Record(demon=pc_to_obj(i_dic=i_dic['demon'], obj_type='demon'), progress=int(i_dic['progress']),
                      rid=int(i_dic['id']))
    if obj_type == 'demon':
        needs_req = False
        rq = 100
        try:
            rq = i_dic['requirement']
        except KeyError:
            needs_req = True
        return_demon = Demon(pid=int(i_dic['id']), name=i_dic['name'], position=int(i_dic['position']), requirement=50)
        if needs_req:
            req_demon = find_global_obj(i_list=DEMON_LIST.ls, i_obj=return_demon, obj_type='demon', obj_set='object')
            if req_demon:
                return_demon.requirement = req_demon.requirement
            else:
                return_demon.requirement = 50
            return return_demon
        else:
            return Demon(pid=int(i_dic['id']), name=i_dic['name'], position=int(i_dic['position']), requirement=rq)
    if obj_type == 'player':
        line_pd = i_dic
        if line_pd:
            line_pd_name = line_pd['name']
            line_pd_pid = int(line_pd['id'])
            line_pd_records = line_pd['records']
            if len(line_pd_records) > 0:
                o_counter = 0
                for record in line_pd_records:
                    pd_demon = pc_to_obj(record, 'record')
                    line_pd_records[o_counter] = pd_demon
                    o_counter += 1
            else:
                line_pd_records = None
            line_pd_published = line_pd['published']
            if len(line_pd_published) > 0:
                o_counter = 0
                for published in line_pd_published:
                    pd_demon = pc_to_obj(published, 'demon')
                    line_pd_published[o_counter] = pd_demon
                    o_counter += 1
            else:
                line_pd_published = None
            line_pd_verified = line_pd['verified']
            if len(line_pd_verified) > 0:
                o_counter = 0
                for verified in line_pd_verified:
                    pd_demon = pc_to_obj(verified, 'demon')
                    line_pd_verified[o_counter] = pd_demon
                    o_counter += 1
            else:
                line_pd_verified = None
            line_pd_created = line_pd['created']
            if len(line_pd_created) > 0:
                o_counter = 0
                for created in line_pd_created:
                    pd_demon = pc_to_obj(created, 'demon')
                    line_pd_created[o_counter] = pd_demon
                    o_counter += 1
            else:
                line_pd_created = None
            return Player(name=line_pd_name, pid=line_pd_pid, records=line_pd_records,
                          published=line_pd_published, verified=line_pd_verified, created=line_pd_created)
        else:
            return None


def find_global_obj(i_list: list, i_obj, obj_type: str, obj_set: str):
    # return Object in i_list if Object matches i_obj of type obj_type of type obj_set, assuming i_list contains Objects
    if obj_type in ['player', 'demon']:
        if obj_set == 'object':
            if i_obj in i_list:
                return i_obj
            found_obj = None
            for o in i_list:
                if int(o.pid) == int(i_obj.pid):
                    found_obj = o
                elif o.name.lower() == i_obj.name.lower():
                    found_obj = o
            return found_obj
        elif obj_set == 'dict':
            if i_obj in i_list:
                return i_obj
            found_obj = None
            for o in i_list:
                if int(o.pid) == int(i_obj['id']):
                    found_obj = o
                elif o.name.lower() == i_obj['name'].lower():
                    found_obj = o
            return found_obj
    elif obj_type in ['role']:
        if obj_set == 'object':
            if i_obj in i_list:
                return i_obj
            found_obj = None
            for o in i_list:
                if int(o.d_role.id) == int(i_obj.d_role.id):
                    found_obj = o
            return found_obj


def object_variables(obj, pr):
    obj_keys = obj.__dict__.keys()
    return obj_keys[pr]


class PCList(object):
    def __init__(self, list_type: str):
        """
        :param list_type: demon, player, role
        """
        self.list_type = list_type
        self.ls = []

    def get_object_by_obj(self, i_obj):
        if self.list_type in ['player', 'demon', 'role']:
            use_obj_inner = i_obj
            if type(use_obj_inner) is dict:
                use_obj_inner = pc_to_obj(use_obj_inner, self.list_type)
            return find_global_obj(i_list=self.ls, i_obj=use_obj_inner, obj_type=self.list_type, obj_set='object')

    def get_object_by_param(self, i_obj, pr: str):
        use_obj = i_obj
        if type(use_obj) is dict:
            use_obj = pc_to_obj(use_obj, self.list_type)
        for o in self.ls:
            if object_variables(o, pr) == object_variables(use_obj, pr):
                return o

    def update_object(self, i_obj):
        use_obj = i_obj
        if type(use_obj) is dict:
            use_obj = pc_to_obj(use_obj, self.list_type)
        change_obj = self.get_object_by_obj(i_obj=use_obj)
        if not change_obj:
            self.ls.append(use_obj)
        else:
            if change_obj != use_obj:
                if self.list_type == 'player':
                    self.ls[self.ls.index(change_obj)].records = use_obj.records
                    self.ls[self.ls.index(change_obj)].verified = use_obj.verified
                    self.ls[self.ls.index(change_obj)].published = use_obj.published
                    self.ls[self.ls.index(change_obj)].created = use_obj.created
                    self.ls[self.ls.index(change_obj)].name = use_obj.name
                else:
                    self.ls[self.ls.index(change_obj)] = use_obj
        self.positional_sort()

    def remove_object(self, i_obj):
        r_obj = True
        use_obj = i_obj
        if type(use_obj) is dict:
            use_obj = pc_to_obj(use_obj, self.list_type)
        try:
            self.ls.remove(use_obj)
        except ValueError:
            r_obj = False
        self.positional_sort()
        return r_obj

    def positional_sort(self):
        if self.list_type == 'demon':
            self.ls.sort(key=lambda x: x.position, reverse=False)

    def player_by_member(self, member: discord.Member):
        if self.list_type == 'player':
            for player in self.ls:
                if str(player.did) == str(member.id):
                    return player

    def __str__(self):
        return_ls = []
        for obj in self.ls:
            return_ls.append(str(obj))
        return str(return_ls)


class PCRole(object):
    def __init__(self, d_guild: discord.Guild, d_role: discord.Role, role_type: str, role_data, whs=False):
        """
        :param role_type:
        - 'points' then role_data: int
        - 'demons' then role_data: list(Demon)
        - 'positional' then role_data: list(int)
        - 'counter' then role_data: list[str['records', 'published', 'verified', 'created'], int]
        """
        self.d_guild = d_guild
        self.d_role = d_role
        self.role_type = role_type
        self.role_data = role_data
        self.whs = whs

    def str_requirements(self):
        if self.role_type == 'points':
            return str(self.role_data) + " point(s)"
        elif self.role_type == 'demons':
            r_st = ''
            for d in self.role_data:
                r_st += d.name + ", "
            return "Complete " + r_st[:-2]
        elif self.role_type == 'positional':
            return "Base Pos: " + str(self.role_data[0]) + ", Range from Base: " + str(self.role_data[1]) + \
                   ", # Required: " + str(self.role_data[2])
        elif self.role_type == 'counter':
            return str(self.role_data[1]) + " Levels in " + self.role_data[0].capitalize()

    def __str__(self):
        return '<PCRole> Role ID:' + str(self.d_role.id) + " Guild ID:" + str(self.d_guild.id) + " Type:" + \
               self.role_type + " Raw Data:" + str(self.role_data)

    def meets_requirements(self, player: Player):
        if self.role_type == 'points':
            return player.points >= self.role_data
        elif self.role_type == 'demons':
            found = {}
            for d in self.role_data:
                found[d.pid] = False
            for record in player.records:
                if record.demon.pid in found.keys() and record.progress == 100:
                    found[record.demon.pid] = True
            for verified in player.verified:
                if verified.pid in found.keys():
                    found[verified.pid] = True
            for d in found:
                if not found[d]:
                    return False
            return True
        elif self.role_type == 'positional':
            pos_max = int(self.role_data[0]) - int(self.role_data[1])
            pos_min = int(self.role_data[0])
            counter = 0
            for record in player.records:
                if pos_min >= record.demon.position >= pos_max and record.progress == 100:
                    counter += 1
            for verified in player.verified:
                if pos_min >= verified.position >= pos_max:
                    counter += 1
            return counter >= int(self.role_data[2])
        elif self.role_type == 'counter':
            counter = 0
            if self.role_data[0] == 'records':
                for _ in player.records:
                    counter += 1
            elif self.role_data[0] == 'verified':
                for _ in player.verified:
                    counter += 1
            elif self.role_data[0] == 'published':
                for _ in player.published:
                    counter += 1
            elif self.role_data[0] == 'created':
                for _ in player.created:
                    counter += 1
            return counter >= int(self.role_data[1])


DEMON_LIST = PCList(list_type='demon')
PLAYER_LIST = PCList(list_type='player')
ROLE_LIST = PCList(list_type='role')


def update_demons_list():
    print('[update_demons_list] Updating list...')
    url1 = "https://pointercrate.com/api/v1/demons?limit=100"
    url2 = "https://pointercrate.com/api/v1/demons?after=100"
    rq1 = urllib.request.Request(url1)
    rq2 = urllib.request.Request(url2)
    try:
        rt1 = str(urllib.request.urlopen(rq1).read())
        rt2 = str(urllib.request.urlopen(rq2).read())
    except urllib.request.HTTPError:
        print("[Demons List] Could not access the Demons List!")
        return
    rt1 = rt1[2:len(rt1) - 1]
    rt2 = rt2[2:len(rt2) - 1]
    rt1 = rt1.replace("\\n", "")
    rt2 = rt2.replace("\\n", "")
    rt1 = rt1.replace("  ", "")
    rt2 = rt2.replace("  ", "")
    rj1 = json.loads(rt1)
    rj2 = json.loads(rt2)
    for d1 in rj1:
        DEMON_LIST.update_object(d1)
    for d2 in rj2:
        DEMON_LIST.update_object(d2)
    print("[update_demons_list] Demon List updated.")


def pc_player(pid):
    if pid is None:
        return None
    url = "https://pointercrate.com/api/v1/players/" + str(pid)
    rq = urllib.request.Request(url)
    try:
        rt = str(urllib.request.urlopen(rq).read())
    except urllib.request.HTTPError:
        return None
    rt = rt[2:len(rt) - 1].replace("\\n", "").replace("  ", "")
    rj = json.loads(rt)
    return rj['data']


def old_rewrite_player_data():
    print('[old_rewrite_player_data] Logging players...')
    limit = 9999  # testing purposes
    with open(file=FILE_PC_DATA, mode='r', encoding='utf-8') as infile:
        limit_counter = 0
        for line in infile:
            if len(line) > 8:
                if limit_counter == limit:
                    break
                limit_counter += 1
                fixed_line = line.replace("\n", "").split("=")
                line_pd = pc_player(fixed_line[1])
                line_player = pc_to_obj(line_pd, 'player')
                if not line_player:
                    continue
                line_player.did = fixed_line[0]
                print('[old_rewrite_player_data] PLAYER: ' + line_player.name + " : " + str(line_player.pid) + " : "
                      + str(line_player.points))
                PLAYER_LIST.update_object(line_player)
        infile.close()
    print('[old_rewrite_player_data] Players logged.')


def file_data(file_name: str) -> list:
    read_data = []
    try:
        with open(file=file_name, mode='r+', encoding='utf-8') as fd_infile:
            try:
                for line in fd_infile:
                    if len(line) > 8:
                        read_data.append(line.replace('\n', '').replace('"', '').strip())
            except UnicodeDecodeError:
                fd_infile.truncate()
                return []
            finally:
                fd_infile.close()
    except PermissionError:
        print('[file_data] Permission Denied opening \"' + file_name + '\" | Is someone editing the file?')
    return read_data


def master_files_read():
    print('[master_files_read] Reading files...')
    # Demons List
    read_data = file_data(file_name=FILE_DEMONS)
    for data in read_data:
        if not data.startswith('NAME') and len(data) > 5:
            data_demon = data.split(", ")
            update_demon = Demon(pid=int(data_demon[1]), name=data_demon[0], position=int(data_demon[2]),
                                 requirement=int(data_demon[3]))
            DEMON_LIST.update_object(update_demon)
    # Players List
    read_data = file_data(file_name=FILE_PLAYERS)
    for data in read_data:
        if not data.startswith('NAME') and len(data) > 5:
            data_player = data.split(", ")
            if data_player[2] == "NONE":
                player_records = []
            else:
                player_records = data_player[2].split(";")
                for record in player_records:
                    player_records[player_records.index(record)] = unpack_dict(i_str=record, obj_type='player_record')
            if data_player[3] == "NONE":
                player_published = []
            else:
                player_published = data_player[3].split(";")
                for published in player_published:
                    player_published[player_published.index(published)] = unpack_dict(i_str=published,
                                                                                      obj_type='player_published')
            if data_player[4] == "NONE":
                player_verified = []
            else:
                player_verified = data_player[4].split(";")
                for verified in player_verified:
                    player_verified[player_verified.index(verified)] = unpack_dict(i_str=verified,
                                                                                   obj_type='player_published')
            if data_player[5] == "NONE":
                player_created = []
            else:
                player_created = data_player[5].split(";")
                for created in player_created:
                    player_created[player_created.index(created)] = unpack_dict(i_str=created,
                                                                                obj_type='player_published')
            update_player = Player(name=data_player[0], pid=int(data_player[1]), did=data_player[6],
                                   records=player_records, verified=player_verified,
                                   published=player_published, created=player_created)
            PLAYER_LIST.update_object(update_player)
    # Roles List
    read_data = file_data(file_name=FILE_ROLES)
    for data in read_data:
        if not data.startswith('ROLE_ID') and len(data) > 5:
            data_role = data.strip().split(', ')
            role_guild = client.get_guild(int(data_role[1]))
            if not role_guild:
                continue
            role_role = get_role(gr_guild=role_guild, gr_i=data_role[0])
            if not role_role:
                continue
            role_type = data_role[2]
            role_data = data_role[3]
            try:
                role_whs = {'False': False, 'True': True}[data_role[4]]
            except IndexError:
                role_whs = False
            if role_type == 'points':
                role_data = int(role_data)
            elif role_type in ['demons', 'positional', 'counter']:
                role_data = unpack_dict(i_str=role_data, obj_type='role_' + role_type)
            update_role = PCRole(d_guild=role_guild, d_role=role_role, role_type=role_type, role_data=role_data,
                                 whs=role_whs)
            ROLE_LIST.update_object(update_role)
    print('[master_files_read] Files updated to internal PCLists.')


def master_files_write():
    print('[master_files_write] Writing to files...')
    # Demons List
    old_data = file_data(file_name=FILE_DEMONS)
    write_data = ["NAME, PID, POSITION, REQUIREMENT"]
    if len(DEMON_LIST.ls) != 0:
        for demon in DEMON_LIST.ls:
            write_data.append(demon.name + ", " + str(demon.pid) + ", " + str(demon.position) + ", " +
                              str(demon.requirement))
        with open(file=FILE_DEMONS, mode='r+', encoding='utf-8') as outfile:
            if old_data != write_data:
                outfile.truncate()
                write_data_s = ""
                for st in write_data:
                    write_data_s += st + "\n"
                print(write_data_s, file=outfile)
            outfile.close()
    # Players List
    old_data = file_data(file_name=FILE_PLAYERS)
    write_data = ["NAME, PID, RECORDS, PUBLISHED, VERIFIED, CREATED, DID"]
    if len(PLAYER_LIST.ls) != 0:
        for player in PLAYER_LIST.ls:
            player_records = player.records
            player_records_write = "NONE"
            if player_records:
                player_records_write = ""
                for record in player_records:
                    player_records_write += condense_dict(record, 'player_record') + ";"
                player_records_write = player_records_write[:-1]
            player_published = player.published
            player_published_write = "NONE"
            if player_published:
                player_published_write = ""
                for published in player_published:
                    player_published_write += condense_dict(published, 'player_published') + ";"
                player_published_write = player_published_write[:-1]
            player_verified = player.verified
            player_verified_write = "NONE"
            if player_verified:
                player_verified_write = ""
                for verified in player_verified:
                    player_verified_write += condense_dict(verified, 'player_verified') + ";"
                player_verified_write = player_verified_write[:-1]
            player_created = player.created
            player_created_write = "NONE"
            if player_created:
                player_created_write = ""
                for created in player_created:
                    player_created_write += condense_dict(created, 'player_created') + ";"
                player_created_write = player_created_write[:-1]
            write_data.append(player.name + ", " + str(player.pid) + ", " + player_records_write + ", " +
                              player_published_write + ", " + player_verified_write + ", " + player_created_write +
                              ", " + str(player.did))
        with open(file=FILE_PLAYERS, mode='r+', encoding='utf-8') as outfile:
            if old_data != write_data:
                outfile.truncate()
                write_data_s = ""
                for st in write_data:
                    write_data_s += st + '\n'
                print(write_data_s, file=outfile)
            outfile.close()
    # Roles List
    old_data = file_data(file_name=FILE_ROLES)
    write_data = ["ROLE_ID, GUILD_ID, TYPE, DATA, WHITELIST"]
    if len(ROLE_LIST.ls) != 0:
        for role in ROLE_LIST.ls:
            role_data = 'NONE'
            if role.role_type == 'points':
                role_data = str(role.role_data)
            elif role.role_type in ['demons', 'positional', 'counter']:
                role_data = condense_dict(i_dic=role.role_data, obj_type='role_' + role.role_type)
            write_data.append(str(role.d_role.id) + ', ' + str(role.d_guild.id) + ', ' + role.role_type + ', ' +
                              role_data + ', ' + str(role.whs))
        with open(file=FILE_ROLES, mode='r+', encoding='utf-8') as outfile:
            if old_data != write_data:
                outfile.truncate()
                write_data_s = ""
                for st in write_data:
                    write_data_s += st + '\n'
                print(write_data_s, file=outfile)
            outfile.close()
    print("[master_files_write] Files updated")


def debug_print_lists():
    print(DEMON_LIST)
    print(PLAYER_LIST)
    print(ROLE_LIST)


async def response_message(ctx, response, message_reaction, preset=""):
    if preset != "":
        pi = {"perms_failed_author": "You do not have Permission to perform this!",
              "perms_failed_bot": client.user.name + " does not have Permissions to perform this!",
              "params_failed": "Invalid parameters!"}
        response = pi[preset]
    await ctx.message.channel.send("**" + ctx.author.name + "**, " + response)
    mri = {"success": CHAR_SUCCESS, "failed": CHAR_FAILED}
    await ctx.message.add_reaction(mri[message_reaction])


def get_role(gr_guild: discord.Guild, gr_i):
    try:
        rid = int(gr_i)
        for role in gr_guild.roles:
            if str(role.id) == str(rid):
                return role
    except ValueError:
        try:
            for role in gr_guild.roles:
                if role.name.lower() == gr_i.lower():
                    return role
        except AttributeError:
            return None


def search_member(gr_guild: discord.Guild, gr_i: str) -> discord.Member:
    for member in gr_guild.members:
        if member.name.lower() == gr_i.strip().lower():
            return member
        if gr_i.strip().lower().isdigit():
            if str(member.id) == str(gr_i.strip()):
                return member


def bot_permissions(ctx) -> bool:
    if not ctx.message.guild:
        return True
    for member in ctx.guild.members:
        if str(member.id) == str(client.user.id):
            for role in member.roles:
                if role.permissions.administrator:
                    return True
    return False


def author_permissions(ctx) -> bool:
    if not ctx.message.guild:
        return True
    for member in ctx.guild.members:
        if str(member.id) == str(ctx.author.id):
            for role in member.roles:
                if role.permissions.administrator:
                    return True
    return False


REFRESH_NOW = None
SUPER_REFRESH_NOW = None


async def roles_refresh():
    global REFRESH_NOW
    global SUPER_REFRESH_NOW
    master_refresh = False
    await client.wait_until_ready()
    while True:
        await asyncio.sleep(5)
        if (datetime.datetime.now().minute == 00 and datetime.datetime.now().hour == 00) or SUPER_REFRESH_NOW:
            master_refresh = True
            print('[roles_refresh] Master Refreshing...')
            master_files_write()
            master_files_read()
            # Player Refresh
            read_data = file_data(file_name=FILE_PLAYERS)
            debug_counter = 9999
            for data in read_data:
                if not data.startswith('NAME') and len(data) > 5:
                    data_player = data.split(", ")
                    if data_player[2] != "NONE":
                        if debug_counter == 0:
                            break
                        player_pc = pc_player(data_player[1])
                        if not player_pc:
                            continue
                        if player_pc:
                            debug_counter -= 1
                            player = pc_to_obj(i_dic=player_pc, obj_type='player')
                            if player:
                                PLAYER_LIST.update_object(player)
                                print('[roles_refresh] Master | ' + player.name + ', Points: ' + str(player.points))
            print('[roles_refresh] Master Refresh finished!')
            if isinstance(SUPER_REFRESH_NOW, discord.TextChannel):
                await SUPER_REFRESH_NOW.send('Refresh finished!')
            master_files_write()
            master_files_read()
        elif datetime.datetime.now().minute == 00 or REFRESH_NOW:
            print('[roles_refresh] Refreshing...')
            master_files_write()
            master_files_read()
            # PC Roles
            refresh_roles_added = 0
            refresh_roles_removed = 0
            if REFRESH_NOW:
                r_guild = [REFRESH_NOW.guild]
            else:
                r_guild = client.guilds
            for guild in r_guild:
                # print('[roles_refresh] Guild: ' + guild.name)
                for member in guild.members:
                    player = PLAYER_LIST.player_by_member(member=member)
                    if player:
                        for pc_role in ROLE_LIST.ls:
                            if pc_role.d_role.guild == guild:
                                if pc_role.meets_requirements(player=player):
                                    # print('[roles_refresh] ' + player.name + ' needs ' + pc_role.d_role.name)
                                    if pc_role.d_role not in member.roles:
                                        try:
                                            await member.add_roles(pc_role.d_role)
                                            refresh_roles_added += 1
                                        except discord.Forbidden:
                                            print('[roles_refresh] Missing Permissions: Adding \"' +
                                                  pc_role.d_role.name + '\" to \"' + member.name + '\"')
                                else:
                                    if pc_role.d_role in member.roles:
                                        try:
                                            await member.remove_roles(pc_role.d_role)
                                            refresh_roles_removed += 1
                                        except discord.Forbidden:
                                            print('[roles_refresh] Missing Permissions: Removing \"' +
                                                  pc_role.d_role.name + '\" from \"' + member.name + '\"')
            print('[roles_refresh] Refreshed!')
            print('[roles_refresh] PC Roles | Added ' + str(refresh_roles_added) + ' Removed ' +
                  str(refresh_roles_removed))
            if isinstance(REFRESH_NOW, discord.TextChannel):
                await REFRESH_NOW.send('Refresh finished!\n__Added__: ' + str(refresh_roles_added) + '\n__Removed__: '
                                       + str(refresh_roles_removed))
        if SUPER_REFRESH_NOW and not master_refresh:
            SUPER_REFRESH_NOW = None
            await asyncio.sleep(60)
        elif REFRESH_NOW:
            REFRESH_NOW = None
            master_refresh = False
            await asyncio.sleep(60)
        elif datetime.datetime.now().minute == 00:
            await asyncio.sleep(60)


def linked_by_did(user: discord.Member):
    pc_players = file_data(FILE_PLAYERS)
    for data in pc_players:
        split_data = data.split(', ')
        if split_data[0] != 'NAME':
            if split_data[6] == str(user.id):
                return split_data[1]


# Specific Discord Demons List methods


def user_gb(i_user):
    return i_user == client.get_user(172861416364179456)


def member_self(m_guild: discord.Guild) -> discord.Member:
    for member in m_guild.members:
        if member.id == client.user.id:
            return member


def guild_pros() -> discord.Guild:
    return client.get_guild(633023820206309416)


def guild_hq() -> discord.Guild:
    return client.get_guild(162862229065039872)


def guild_ps() -> discord.Guild:
    return client.get_guild(395654171422097420)


def channel_feedback() -> discord.TextChannel:
    return guild_hq().get_channel(507344865516978186)


def role_list_helper(author_id: int):
    helper_roles = [get_role(guild_pros(), '633025317455527962'),
                    get_role(guild_ps(), '395664123716829194'),
                    get_role(guild_hq(), '254769445723963393')]
    mem_pros = guild_pros().get_member(author_id)
    if mem_pros:
        if [role for role in helper_roles if role in mem_pros.roles]:
            return True
    mem_ps = guild_ps().get_member(author_id)
    if mem_ps:
        if [role for role in helper_roles if role in mem_ps.roles]:
            return True
    mem_hq = guild_hq().get_member(author_id)
    if mem_hq:
        if [role for role in helper_roles if role in mem_hq.roles]:
            return True
    return False


def role_list_moderator(author_id: int):
    moderator_roles = [get_role(guild_pros(), '633025213440983041'),
                       get_role(guild_ps(), '395663789598703619'),
                       get_role(guild_hq(), '365519088832872468')]
    mem_pros = guild_pros().get_member(author_id)
    if mem_pros:
        if [role for role in moderator_roles if role in mem_pros.roles]:
            return True
    mem_ps = guild_ps().get_member(author_id)
    if mem_ps:
        if [role for role in moderator_roles if role in mem_ps.roles]:
            return True
    mem_hq = guild_hq().get_member(author_id)
    if mem_hq:
        if [role for role in moderator_roles if role in mem_hq.roles]:
            return True
    return False


def role_list_leader(author_id: int):
    leader_roles = [get_role(guild_pros(), '633024750024917003'),
                    get_role(guild_ps(), '395663660233785345'),
                    get_role(guild_hq(), '215857332863762432')]
    mem_pros = guild_pros().get_member(author_id)
    if mem_pros:
        if [role for role in leader_roles if role in mem_pros.roles]:
            return True
    mem_ps = guild_ps().get_member(author_id)
    if mem_ps:
        if [role for role in leader_roles if role in mem_ps.roles]:
            return True
    mem_hq = guild_hq().get_member(author_id)
    if mem_hq:
        if [role for role in leader_roles if role in mem_hq.roles]:
            return True
    return False


@client.event
async def on_ready():
    print("Bot Ready!")
    print("Name: " + client.user.name + ", ID: " + str(client.user.id))
    server_list = ""
    for server in client.guilds:
        if server is not None:
            server_list += server.name + ", "
            """if server == guild_pros():
                for role in server.roles:
                    print(role.name, role.id)"""
    print("Connected Guilds: " + server_list[:len(server_list) - 2])
    await client.wait_until_ready()
    update_demons_list()
    master_files_write()
    master_files_read()


@client.event
async def on_member_join(member: discord.Member):
    if member.guild == guild_pros():
        print('[on_member_join] PROS | User \"' + member.name + '\" joining...')
        allowed = False
        player = PLAYER_LIST.player_by_member(member)
        if not player:
            player = pc_to_obj(i_dic=pc_player(linked_by_did(member)), obj_type='player')
        if player:  # Check Whitelisted PC Roles
            print('[on_member_join] Player found: ' + player.name + ' ' + str(player.pid))
            for pc_role in ROLE_LIST.ls:
                if pc_role.whs:
                    if pc_role.meets_requirements(player):
                        allowed = True
                        try:
                            await member.add_roles(pc_role.d_role)
                        except discord.Forbidden:
                            print('[on_member_join] Missing Permissions: Adding \"' +
                                  pc_role.d_role.name + '\" to \"' + member.name + '\"')
            if allowed:
                print('[on_member_join] Player meets requirements for PC Role: ACCEPTED')
            if role_list_helper(member.id):  # Check List staff
                print('[on_member_join] Player is List Staff: ACCEPTED')
                allowed = True
        with open(file=FILE_WHITELIST, mode='r') as infile:  # Check Whitelist exempts
            exempts = [line.strip().replace('\n', '') for line in infile]
            if str(member.id) in exempts:
                allowed = True
                print('[on_member_join] Player is on Whitelist: ACCEPTED')
            infile.close()
        if not allowed:
            print('[on_member_join] Player DENIED')
            await member.send('Whoa, you\'re not allowed in here! Contact Demon List Staff if you believe this to be a'
                              ' mistake.')
            await member.ban(reason='User is not on the Whitelist')


ALLOW_INVITES = True


@client.event
async def on_message(message: discord.Message):
    global ALLOW_INVITES
    if not message.guild:
        if message.content.startswith('??dlp') and ALLOW_INVITES:
            if message.author.id in [204213203566067714, 212948838862815242]:
                with open(file='zg.jpg', mode='rb') as zg:
                    await message.channel.send(file=discord.File(fp=zg))
            else:
                if guild_pros().get_member(message.author.id) not in guild_pros().members:
                    await message.author.send('Checking...')
                    await asyncio.sleep(3)
                    allowed = False
                    player = PLAYER_LIST.player_by_member(message.author)
                    if player:  # Check Whitelisted PC Roles
                        for pc_role in ROLE_LIST.ls:
                            if pc_role.whs:
                                if pc_role.meets_requirements(player):
                                    allowed = True
                                    break
                        if role_list_helper(message.author.id):
                            # Check List staff
                            allowed = True
                    else:  # Check Whitelist exempts
                        with open(file=FILE_WHITELIST, mode='r') as infile:
                            exempts = [line.strip().replace('\n', '') for line in infile]
                            if str(message.author.id) in exempts:
                                allowed = True
                            infile.close()
                    if allowed:
                        await message.author.send('Congratulations, you have access to __**Demon List Pros**__!\n' +
                                                  INVITE_DLP)
                    else:
                        await message.author.send('Access DENIED. You need **200** List Points to join '
                                                  '__**Demon List Pros**__!')
                else:
                    await message.author.send('Hey! You\'re already in __**Demon List Pros**__!')
    await client.process_commands(message)


@client.event
async def on_command_error(_, error):
    if isinstance(error, commands.CommandNotFound):
        return
    raise error


@client.command(pass_context=True)
async def old_kc_data(ctx):
    if user_gb(ctx.author):
        await ctx.channel.send('Updating __' + client.user.name + "__ with Old *KC* data.")
        await ctx.channel.send('`[Updating]` Internal **Demon List**...')
        update_demons_list()
        await ctx.channel.send('`[Updating]` **Demon List** synchronized to global `DEMON_LIST`')
        await ctx.channel.send('`[Updating]` Internal **Player List**...')
        old_rewrite_player_data()
        await ctx.channel.send('`[Updating]` **Player List** synchronized to global `PLAYER_LIST`')
        await ctx.channel.send('`[Updating]` Writing changes to CSV files...')
        master_files_write()
        print(PLAYER_LIST.ls)
        await ctx.channel.send('`[Updating]` Files written!')
        await response_message(ctx, 'Old *KC* data updated.', 'success')


@client.command(pass_context=True)
async def debug_write_read(ctx):
    if user_gb(ctx.author):
        await ctx.channel.send('`[Updating]` Writing changes to CSV files...')
        master_files_write()
        await ctx.channel.send('`[Updating]` Files written!')
        await ctx.channel.send('`[Updating]` Reading from CSV files...')
        master_files_read()
        await ctx.channel.send('`[Updating]` Files read!')


@client.command(pass_context=True)
async def super_refresh_now(ctx):
    global SUPER_REFRESH_NOW
    if bot_permissions(ctx):
        if user_gb(ctx.author):
            if not SUPER_REFRESH_NOW:
                SUPER_REFRESH_NOW = ctx.channel
                await response_message(ctx, response='Master Refreshing now...', message_reaction='success')
            else:
                await response_message(ctx, response='Already master refreshing!', message_reaction='failed')
    else:
        await response_message(ctx, response='', message_reaction='failed', preset='perms_failed_bot')


@client.command(pass_context=True)
async def refresh_now(ctx):
    global REFRESH_NOW
    if bot_permissions(ctx):
        if role_list_helper(ctx.author.id):
            if not REFRESH_NOW:
                REFRESH_NOW = ctx.channel
                await response_message(ctx, response='Refreshing now...', message_reaction='success')
            else:
                await response_message(ctx, response='Already refreshing!', message_reaction='failed')
        else:
            await response_message(ctx, response='You are not on the Demon List staff!', message_reaction='failed')
    else:
        await response_message(ctx, response='', message_reaction='failed', preset='perms_failed_bot')


@client.command(pass_context=True)
async def rc_role(ctx, rc_type, i_role, rc_role_type=None, rc_role_params=None):
    # rc_role add|remove i_role points|demons|positional|counter parameters
    if bot_permissions(ctx):
        if role_list_helper(ctx.author.id):
            use_role = i_role.replace('_', ' ')
            set_role = get_role(gr_guild=ctx.guild, gr_i=use_role)
            if set_role:
                if rc_type.lower() == 'add':
                    rc_conditions = True
                    if rc_role_type:
                        rc_role_data = None
                        if rc_role_type.lower() == 'points':
                            if not is_number(rc_role_params):
                                rc_conditions = False
                            else:
                                rc_points = int(rc_role_params.replace('\"', ''))
                                rc_role_data = rc_points
                        elif rc_role_type.lower() == 'demons':
                            if is_number(rc_role_params):
                                rc_conditions = False
                            else:
                                rc_demons = rc_role_params.replace("_", " ").replace('\"', '').split(",")
                                rc_demons_l = []
                                for d in rc_demons:
                                    for ld in DEMON_LIST.ls:
                                        if ld.name.lower() == d.lower():
                                            rc_demons_l.append(ld)
                                if len(rc_demons) != len(rc_demons_l):
                                    rc_conditions = False
                                else:
                                    rc_role_data = rc_demons_l
                        elif rc_role_type.lower() in ['positional', 'pos']:  # base,range,count
                            if is_number(rc_role_params.replace('\"', '')):
                                rc_conditions = False
                            else:
                                rc_pos = rc_role_params.replace('\"', '').split(",")
                                if len(rc_pos) != 3:
                                    rc_conditions = False
                                else:
                                    for p in rc_pos:
                                        if is_number(p):
                                            rc_pos[rc_pos.index(p)] = int(p)
                                        else:
                                            rc_conditions = False
                                    if rc_pos[0] - rc_pos[1] < 0 or rc_pos[2] > rc_pos[1] or \
                                            rc_pos[0] > 150 or rc_pos[0] < 1:
                                        rc_conditions = False
                                    else:
                                        rc_pos_base = rc_pos[0]
                                        rc_pos_range = rc_pos[1]
                                        rc_count = rc_pos[2]
                                        rc_role_data = [rc_pos_base, rc_pos_range, rc_count]
                        elif rc_role_type.lower() == 'counter':  # type,count
                            if is_number(rc_role_params.replace('\"', '')):
                                rc_conditions = False
                            else:
                                rc_counter = rc_role_params.replace('\"', '').split(",")
                                if len(rc_counter) != 2:
                                    rc_conditions = False
                                else:
                                    if not is_number(rc_counter[1]):
                                        rc_conditions = False
                                    else:
                                        if rc_counter[0].lower() not in ['records', 'published', 'verified', 'created']:
                                            rc_conditions = False
                                        else:
                                            rc_completion_type = rc_counter[0]
                                            rc_count = int(rc_counter[1])
                                            rc_role_data = [rc_completion_type, rc_count]
                        if rc_conditions and rc_role_data:
                            rc_role_r = PCRole(d_guild=ctx.guild, d_role=set_role, role_type=rc_role_type.lower(),
                                               role_data=rc_role_data, whs=False)
                            ROLE_LIST.update_object(rc_role_r)
                            await response_message(ctx, response='Role set!', message_reaction='success')
                            role_set_m = '__**New PC Role**__\n'
                            role_set_m += '__Role:__ ' + set_role.name + "\n"
                            role_set_m += '__Type:__ ' + rc_role_type.lower().capitalize() + '\n'
                            role_set_m += '__Requirements:__ ' + rc_role_r.str_requirements()
                            await ctx.channel.send(content=role_set_m)
                            master_files_write()
                            for member in ctx.guild.members:
                                player = PLAYER_LIST.player_by_member(member)
                                if player:
                                    if rc_role_r.meets_requirements(player):
                                        if rc_role_r.d_role not in member.roles:
                                            try:
                                                await member.add_roles(rc_role_r.d_role)
                                            except discord.Forbidden:
                                                print('[rc_role] Missing Permissions: Adding \"' +
                                                      rc_role_r.d_role.name + '\" to \"' + member.name + '\"')
                        else:
                            await response_message(ctx, response='', message_reaction='failed', preset='params_failed')
                elif rc_type.lower() == 'remove':
                    rc_remove = None
                    for pc_role in ROLE_LIST.ls:
                        if pc_role.d_role == set_role:
                            rc_remove = pc_role
                    if rc_remove:
                        for member in ctx.guild.members:
                            if rc_remove.d_role in member.roles:
                                try:
                                    await member.remove_roles(rc_remove.d_role)
                                except discord.Forbidden:
                                    print('[rc_role] Missing Permissions: Removing \"' + rc_remove.d_role.name +
                                          '\" from \"' + member.name + '\"')
                        if ROLE_LIST.remove_object(rc_remove):
                            await response_message(ctx, response='Role *' + rc_remove.d_role.name +
                                                                 '* unset from PC Role!', message_reaction='success')
                            master_files_write()
                        else:
                            await response_message(ctx, response='Could not find role!', message_reaction='failed')
                    else:
                        await response_message(ctx, response='Invalid RC Role!', message_reaction='failed')
                else:
                    await response_message(ctx, response='Invalid type!', message_reaction='failed')
            else:
                await response_message(ctx, response='Invalid role!', message_reaction='failed')
        else:
            await response_message(ctx, response='You are not on the Demon List staff!', message_reaction='failed')
    else:
        await response_message(ctx, response='', message_reaction='failed', preset='perms_failed_bot')


@client.command(pass_context=True)
async def rc_list(ctx):
    rc_embed = discord.Embed(title='Listing all RC Roles', description=ctx.guild.name,
                             color=member_self(ctx.guild).color)
    for pc_role in ROLE_LIST.ls:
        if pc_role.d_role in ctx.guild.roles:
            rc_embed.add_field(name=pc_role.d_role.name, value='<@&' + str(pc_role.d_role.id) + '> : ' +
                                                               pc_role.str_requirements(), inline=False)
    await ctx.channel.send(embed=rc_embed)


@client.command(pass_context=True)
async def player_link(ctx, i_user, i_pid):
    if role_list_helper(ctx.author.id):
        use_user = search_member(gr_guild=ctx.guild, gr_i=i_user)
        if use_user:
            player = pc_player(i_pid)
            if player:
                player_obj = pc_to_obj(i_dic=player, obj_type='player')
                if player_obj:
                    player_obj.did = int(use_user.id)
                    PLAYER_LIST.update_object(player_obj)
                    await response_message(ctx, response='User linked!', message_reaction='success')
                    link_message = '__User__: ' + use_user.display_name + ' (ID: ' + str(use_user.id) + ')\n'
                    link_message += '__Player__: ' + player_obj.name + ' (PID: ' + str(player_obj.pid) + ')'
                    await ctx.channel.send(link_message)
                    master_files_write()
                else:
                    await response_message(ctx, response='Invalid player!', message_reaction='failed')
            else:
                await response_message(ctx, response='Invalid player!', message_reaction='failed')
        else:
            await response_message(ctx, response='Invalid user!', message_reaction='failed')
    else:
        await response_message(ctx, response='You are not on the Demon List staff!', message_reaction='failed')


@client.command(pass_context=True)
async def player_unlink(ctx, i_user):
    if role_list_helper(ctx.author.id):
        use_user = search_member(gr_guild=ctx.guild, gr_i=i_user)
        if use_user:
            player_obj = PLAYER_LIST.player_by_member(use_user)
            if player_obj:
                PLAYER_LIST.remove_object(player_obj)
                await response_message(ctx, response='User unlinked!', message_reaction='success')
                master_files_write()
            else:
                await response_message(ctx, response='Invalid player!', message_reaction='failed')
        else:
            await response_message(ctx, response='Invalid user!', message_reaction='failed')
    else:
        await response_message(ctx, response='You are not on the Demon List staff!', message_reaction='failed')


@client.command(pass_context=True)
async def rc_whitelist(ctx, i_role):
    if bot_permissions(ctx):
        if role_list_leader(ctx.author.id):
            use_role = i_role.replace('_', ' ')
            set_role = get_role(gr_guild=ctx.guild, gr_i=use_role)
            if set_role:
                rc_whs = None
                for pc_role in ROLE_LIST.ls:
                    if pc_role.d_role == set_role:
                        rc_whs = pc_role
                if rc_whs:
                    rc_whs.whs = {False: True, True: False}[rc_whs.whs]
                    await response_message(ctx, response='Whitelist checker for RC Role set to **' + str(rc_whs.whs) +
                                                         '**!', message_reaction='success')
                    master_files_write()
                else:
                    await response_message(ctx, response='Invalid RC Role!', message_reaction='failed')
            else:
                await response_message(ctx, response='Invalid role!', message_reaction='failed')
        else:
            await response_message(ctx, response='You are not a Demon List Leader!', message_reaction='failed')
    else:
        await response_message(ctx, response='', message_reaction='failed', preset='perms_failed_bot')


@client.command(pass_context=True)
async def exempt_whitelist(ctx, i_user):
    if bot_permissions(ctx):
        if role_list_moderator(ctx.author.id):
            if is_number(i_user):
                whs_added = True
                with open(file=FILE_WHITELIST, mode='r') as infile:
                    exempts = [line.strip().replace('\n', '') for line in infile]
                    if i_user in exempts:
                        exempts.remove(i_user)
                        whs_added = False
                    else:
                        exempts.append(i_user)
                    infile.close()
                if exempts:
                    with open(file=FILE_WHITELIST, mode='w') as outfile:
                        outfile.truncate()
                        for e in exempts:
                            print(e, file=outfile)
                        outfile.close()
                    whs_message = {True: 'Added', False: 'Removed'}[whs_added]
                    await response_message(ctx, response=whs_message + ' ' + i_user + ' in Whitelist exempts!',
                                           message_reaction='success')
                else:
                    await response_message(ctx, response='Nothing changed!', message_reaction='failed')
            else:
                await response_message(ctx, response='Invalid user!', message_reaction='failed')
        else:
            await response_message(ctx, response='You are not a Demon List Moderator!', message_reaction='failed')
    else:
        await response_message(ctx, response='', message_reaction='failed', preset='perms_failed_bot')


@client.command(pass_context=True)
async def rc_player(ctx, i_user):
    use_user = search_member(gr_guild=ctx.guild, gr_i=i_user)
    if use_user:
        player = pc_player(linked_by_did(use_user))
        if player:
            player_obj = pc_to_obj(i_dic=player, obj_type='player')
            if player_obj:
                await response_message(ctx, response='Showing data for ' + use_user.display_name + ':',
                                       message_reaction='success')
                p_m = '__Name__: ' + player_obj.name + '\n'
                p_m += '__PID__: ' + str(player_obj.pid) + '\n'
                p_m += '__Points__: ' + str(player_obj.points) + '\n'
                m_records = ''
                m_progress = ''
                if player_obj.records:
                    for record in player_obj.records:
                        m_s = ''
                        if record.demon.position >= 151:
                            m_s = '*'
                        elif record.demon.position <= 75:
                            m_s = '**'
                        if record.progress == 100:
                            m_records += m_s + record.demon.name + m_s + ', '
                        else:
                            m_progress += m_s + record.demon.name + m_s + '(' + str(record.progress) + '%), '
                    m_records = m_records[:-2]
                    m_progress = m_progress[:-2]
                m_verified = ''
                if player_obj.verified:
                    for verified in player_obj.verified:
                        m_s = ''
                        if verified.position >= 151:
                            m_s = '*'
                        elif verified.position <= 75:
                            m_s = '**'
                        m_verified += m_s + verified.name + m_s + ', '
                    m_verified = m_verified[:-2]
                m_published = ''
                if player_obj.published:
                    for published in player_obj.published:
                        m_s = ''
                        if published.position >= 151:
                            m_s = '*'
                        elif published.position <= 75:
                            m_s = '**'
                        m_published += m_s + published.name + m_s + ', '
                    m_published = m_published[:-2]
                m_created = ''
                if player_obj.created:
                    for created in player_obj.created:
                        m_s = ''
                        if created.position >= 151:
                            m_s = '*'
                        elif created.position <= 75:
                            m_s = '**'
                        m_created += m_s + created.name + m_s + ', '
                    m_created = m_created[:-2]
                p_m += '__Records__: ' + m_records + '\n'
                p_m_2 = '__Verified__: ' + m_verified + '\n'
                p_m_2 += '__Published__: ' + m_published + '\n'
                p_m_2 += '__Created In__: ' + m_created + '\n'
                p_m_2 += '__Progress On__: ' + m_progress
                await ctx.channel.send(p_m)
                await ctx.channel.send(p_m_2)
            else:
                await response_message(ctx, response='Invalid player!', message_reaction='failed')
        else:
            await response_message(ctx, response='Invalid player!', message_reaction='failed')
    else:
        await response_message(ctx, response='Invalid user!', message_reaction='failed')


@client.command(pass_context=True)
async def suggestion(ctx, s_type, s_param, s_description):
    if s_type.replace('\"', '').lower() in ['organization', 'new', 'placement']:
        param_found = 1
        """
        :parameter param_found (int)
        - 0: Found
        - 1: Not Found (Invalid Parameters)
        - 2: Not Found (Invalid Demon for type_check 'placement')
        - 3: Not Found (Player has not beaten/verified param_check Demon for type_check 'placement')
        - 4: Not Found (Invalid Player for type_check 'placement')
        """
        param_check = s_param.replace('\"', '').lower()
        type_check = s_type.replace('\"', '').lower()
        param_demon = None
        param_player = None
        if type_check == 'organization' and param_check in ['website', 'dlp']:
            param_found = 0
        elif type_check == 'new' and len(param_check.strip()) != 0:
            param_found = 0
        elif type_check == 'placement':
            param_player = pc_player(linked_by_did(ctx.author))
            if not param_player:
                param_found = 4
            else:
                param_demon = None
                for pc_demon in DEMON_LIST.ls:
                    if pc_demon.name.lower() == param_check:
                        param_demon = pc_demon
                        break
                if not param_demon:
                    param_found = 2
                else:
                    param_completed = False
                    for record in param_player['records']:
                        if record['demon']['name'] == param_demon.name and record['progress'] == 100:
                            param_completed = True
                            break
                    if param_player['verified']:
                        for verified in param_player['verified']:
                            if verified['name'] == param_demon.name:
                                param_completed = True
                                break
                    if not param_completed:
                        param_found = 3
                    else:
                        param_found = 0
        if param_found == 0:
            desc_check = s_description.replace('\"', '')
            if len(desc_check) > 0:
                s_message = '**New Suggestion from:** *' + ctx.author.name + '#' + ctx.author.discriminator + \
                            '* (' + ctx.guild.name + ')\n'
                s_message += '__Type:__ ' + {'organization': 'Organization',
                                             'new': 'To Be Placed Level',
                                             'placement': 'Placement Opinion'}[type_check] + '\n'
                s_m_param = ''
                if type_check == 'organization':
                    s_m_param = {'website': 'Website', 'dlp': 'Demon List Public Server'}[param_check]
                elif type_check == 'new':
                    s_m_param = s_param.replace('\"', '')
                elif type_check == 'placement':
                    s_m_param = param_demon.name + ' | Position: ' + \
                                str(param_demon.position)
                s_message += '__Parameter:__ ' + s_m_param + '\n'
                if type_check == 'placement':
                    s_message += '__Player Data:__ ' + param_player['name'] + ' (PID: ' +\
                                 str(linked_by_did(ctx.author)) + ') | Records: ' + \
                                 str(len(param_player['records'])) + ' Verified: ' + str(len(param_player['verified']))\
                                 + ' Published: ' + str(len(param_player['published'])) + ' Created: ' + \
                                 str(len(param_player['created'])) + '\n'
                s_message += '__Message:__ ' + desc_check
                await channel_feedback().send(s_message)
                await response_message(ctx, response='Feedback sent!', message_reaction='success')
            else:
                await response_message(ctx, response='Invalid description!', message_reaction='failed')
        else:
            param_not_found = {1: 'Invalid parameters!', 2: 'Invalid demon!', 3: 'You have not beaten this Demon!',
                               4: 'You are not linked to a valid Player!'}
            await response_message(ctx, response=param_not_found[param_found], message_reaction='failed')
    else:
        await response_message(ctx, response='Invalid suggestion type!', message_reaction='failed')


client.loop.create_task(roles_refresh())
client.run(SECRET)
