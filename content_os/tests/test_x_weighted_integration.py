from types import SimpleNamespace
from content_os.platforms import platform_contract_v2 as pc

passed=0

def ok(cond):
    global passed
    assert cond
    passed+=1

class Result:
    def __init__(self,n,valid=True):
        self.weightedLength=n
        self.valid=valid

def fake_parse(text):
    if text=='👾': return Result(2)
    if text.startswith('https://'): return Result(23)
    if text=='日本語': return Result(6)
    return Result(len(text))

old=pc._parse_tweet
pc._parse_tweet=fake_parse
try:
    ok(pc.x_weighted_length('👾')[:2]==(2,True))
    ok(pc.x_weighted_length('https://example.com/very/long/path')[:2]==(23,True))
    ok(pc.x_weighted_length('日本語')[:2]==(6,True))
    ok(pc.build_x_post('👾')['character_count']==2)
    ok(pc.x_weighted_length('👾')[2]=='TWITTER_TEXT_CONFORMANCE')
finally:
    pc._parse_tweet=old
print(f'PASS {passed}/5')
