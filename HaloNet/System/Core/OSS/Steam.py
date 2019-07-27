from steam.webapi import WebAPI

from Core import WARN_MSG

api = WebAPI("52C026F06AD673EDB37CE692D70B6889")


class SteamError(RuntimeError):
    pass

def BeginAuthSession(session_ticket):
    result = api.ISteamUserAuth.AuthenticateUserTicket(ticket=session_ticket, appid=869380)
    response = result['response']
    if response['params']['result'] == 'OK':
        steam_id = response['params']['steamid']
        result = api.ISteamUser.GetPlayerSummaries(steamids=steam_id)
        return steam_id, result['response']['players'][0]['personaname']
    raise SteamError(f"Invalid session ticket {session_ticket}")
# print(dir(api.ISteamUser.GetFriendList()))
# r0 = api.call('ISteamUser.ResolveVanityURL', vanityurl="valve", url_type=2)
# r1 = api.ISteamUser.ResolveVanityURL(vanityurl="valve", url_type=2)
# r2 = api.ISteamUser.ResolveVanityURL_v1(vanityurl="valve", url_type=2)
# print(r0)
# print(r1)
# print(r2)
