def attack(actor, target, actor_before, target_before):
    msgs = [["%s attacks %s!"], ["%s is hit for %s damage."]]
    msgs[0][0] = msgs[0][0] % (actor.data['job'], target.data['job'])
    msgs[1][0] = msgs[1][0] % (target.data['job'], int(target_before['health']) - int(target.data['health']))
    if int(target.data['health']) < 1:
        msgs[1].append("%s is defeated!" % target.data['job'])
    return msgs
