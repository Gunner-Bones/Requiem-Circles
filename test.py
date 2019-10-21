import urllib.request
import json


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


print(pc_player(271))
