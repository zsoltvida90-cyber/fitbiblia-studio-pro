from content_os.platforms.platform_contract import normalize_platform,build_x_post,build_x_thread,validate_platform_output,x_weighted_length

passed=0

def ok(cond):
    global passed
    assert cond
    passed+=1

def err(fn,token):
    global passed
    try: fn()
    except Exception as exc:
        assert token in str(exc),str(exc)
        passed+=1
        return
    raise AssertionError('expected '+token)

ok(normalize_platform('Tik Tok')=='TIKTOK')
ok(normalize_platform('Twitter')=='X')
ok(build_x_post('a'*280)['character_count']==280)
err(lambda:build_x_post('a'*281),'X_POST_TOO_LONG')
ok(build_x_post('á'*280)['character_count']==280)
ok(validate_platform_output('tiktok','REEL')['compatible'] is True)
ok(validate_platform_output('x','CAROUSEL')['compatible'] is False)
ok(len(build_x_thread(['első','második'])['posts'])==2)

try:
    emoji_count,_,mode=x_weighted_length('👾')
except RuntimeError as exc:
    ok('X_WEIGHTED_COUNTER_REQUIRED' in str(exc))
else:
    ok(emoji_count==2 and mode=='TWITTER_TEXT_CONFORMANCE')

try:
    url_count,_,mode=x_weighted_length('https://example.com/very/long/path')
except RuntimeError as exc:
    ok('X_WEIGHTED_COUNTER_REQUIRED' in str(exc))
else:
    ok(url_count==23 and mode=='TWITTER_TEXT_CONFORMANCE')

print(f'PASS {passed}/10')
