import sys

STDERR = sys.stderr
STDOUT = sys.stdout

account_email = "emailbox@hostname"
account_password = "************"

def gold_repr(value):
    rep = ""
    is_negative = (value < 0)
    try:
        positive_value = abs(int(value))
    except:
        return "Non gold value ("+str(value)+")"
    copper =  positive_value % 100
    silver = (positive_value / 100) % 100
    gold   =  positive_value / 10000

    if gold:
        rep = ("-" if is_negative else " ")
        rep += str(gold)+ "g " + str(silver).zfill(2)+"s " + str(copper).zfill(2)+"c"
    else:
        if silver:
            rep = ("-" if is_negative else " ")
            rep += str(silver)+"s " + str(copper).zfill(2)+"c"
        else:
            rep = ("-" if is_negative else " ")
            rep += str(copper)+"c"

    return rep
