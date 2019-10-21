import sys
import urllib.request
import json
import math
import discord
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
FILE_PC_DATA = "pc_data.txt"
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


def unpack_dict(i_str: str, obj_type: str):
    if obj_type in ['player_published', 'player_verified', 'player_created']:
        unp_str = i_str.split(":")
        return Demon(name=unp_str[1], pid=int(unp_str[0]), position=int(unp_str[2]), requirement=int(unp_str[3]))
    if obj_type == 'player_record':
        unp_str = i_str.split(":")
        return Record(demon=Demon(pid=int(unp_str[0]), name=unp_str[1], position=int(unp_str[2]),
                                  requirement=int(unp_str[5])), rid=int(unp_str[3]), progress=int(unp_str[4]))


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

    def __str__(self):
        return_ls = []
        for obj in self.ls:
            return_ls.append(str(obj))
        return str(return_ls)


class PCRole(object):
    def __init__(self, d_guild: discord.Guild, d_role: discord.Role, role_type: str, role_data):
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
    with open(file=file_name, mode='r+', encoding='utf-8') as fd_infile:
        try:
            for line in fd_infile:
                if len(line) > 8:
                    read_data.append(line.replace('\n', '').replace('"', '').strip())
            fd_infile.close()
        except UnicodeDecodeError:
            fd_infile.truncate()
            fd_infile.close()
            return []
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
    print('[master_files_read] Files updated to internal PCLists.')


def master_files_write():
    print('[master_files_write] Writing to files...')
    # Demons List
    old_data = file_data(file_name=FILE_DEMONS)
    write_data = ["NAME, PID, POSITION, REQUIREMENT"]
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
                          player_published_write + ", " + player_verified_write + ", " + player_created_write + ", " +
                          player.did)
    with open(file=FILE_PLAYERS, mode='r+', encoding='utf-8') as outfile:
        if old_data != write_data:
            outfile.truncate()
            write_data_s = ""
            for st in write_data:
                write_data_s += st + '\n'
            print(write_data_s, file=outfile)
        outfile.close()
    print("[master_files_write] Files updated")


async def response_message(ctx, response, message_reaction, preset=""):
    if preset != "":
        pi = {"perms_failed_author": "You do not have Permission to perform this!",
              "perms_failed_bot": client.user.name + " does not have Permissions to perform this!",
              "params_failed": "Invalid parameters!"}
        response = pi[preset]
    await ctx.message.channel.send("**" + ctx.author.name + "**, " + response)
    mri = {"success": CHAR_SUCCESS, "failed": CHAR_FAILED}
    await ctx.message.add_reaction(mri[message_reaction])


def get_role(gr_guild, gr_i):
    try:
        rid = int(gr_i)
        return discord.utils.find(lambda r: str(rid) in str(r.id), gr_guild.roles)
    except ValueError:
        try:
            return discord.utils.find(lambda r: gr_i.lower() in r.name.lower(), gr_guild.roles)
        except AttributeError:
            return None


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

# Specific Discord Demons List methods


def user_gb(i_user):
    return i_user == client.get_user(172861416364179456)


@client.event
async def on_ready():
    print("Bot Ready!")
    print("Name: " + client.user.name + ", ID: " + str(client.user.id))
    server_list = ""
    for server in client.guilds:
        if server is not None:
            server_list += server.name + ", "
    print("Connected Guilds: " + server_list[:len(server_list) - 2])
    update_demons_list()
    master_files_write()
    master_files_read()
    print(DEMON_LIST)
    print(PLAYER_LIST)


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
async def rc_role(ctx, rc_type, i_role, rc_role_type=None, rc_role_params=None):
    # rc_role add|remove i_role points|demons|positional|counter parameters
    if bot_permissions(ctx):
        if author_permissions(ctx):
            set_role = get_role(gr_guild=ctx.guild, gr_i=i_role)
            if set_role:
                if rc_type.lower() == 'add':
                    rc_conditions = True
                    if rc_role_type:
                        rc_role_data = None
                        if rc_role_type.lower() == 'points':
                            if not is_number(rc_role_params):
                                rc_conditions = False
                            else:
                                rc_points = int(rc_role_params)
                                rc_role_data = rc_points
                        elif rc_role_type.lower() == 'demons':
                            if is_number(rc_role_params):
                                rc_conditions = False
                            else:
                                rc_demons = rc_role_params.replace(" ", "").split(",")
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
                            if is_number(rc_role_params):
                                rc_conditions = False
                            else:
                                rc_pos = rc_role_params.split(",")
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
                            if is_number(rc_role_params):
                                rc_conditions = False
                            else:
                                rc_counter = rc_role_params.split(",")
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
                                               role_data=rc_role_data)
                            ROLE_LIST.update_object(rc_role_r)
                            await response_message(ctx, response='Role set!', message_reaction='success')
                            role_set_m = '__**New PC Role**__\n'
                            role_set_m += '__Role:__ ' + set_role.name + "\n"
                            role_set_m += '__Type:__ ' + rc_role_type.lower().capitalize() + '\n'
                            role_set_m += '__Requirements:__ ' + rc_role_r.str_requirements()
                            await ctx.channel.send(content=role_set_m)
                        else:
                            await response_message(ctx, response='', message_reaction='failed', preset='params_failed')
                elif rc_type.lower() == 'remove':
                    rc_remove = None
                    for pc_role in ROLE_LIST.ls:
                        if pc_role.d_role == set_role:
                            rc_remove = pc_role
                    if ROLE_LIST.remove_object(rc_remove):
                        await response_message(ctx, response='Role *' + rc_remove.d_role.name + '* unset from PC Role!',
                                               message_reaction='success')
                    else:
                        await response_message(ctx, response='Could not find role!', message_reaction='failed')
                else:
                    await response_message(ctx, response='Invalid type!', message_reaction='failed')
            else:
                await response_message(ctx, response='Invalid role!', message_reaction='failed')
        else:
            await response_message(ctx, response='', message_reaction='failed', preset='perms_failed_author')
    else:
        await response_message(ctx, response='', message_reaction='failed', preset='perms_failed_bot')


client.run(SECRET)
