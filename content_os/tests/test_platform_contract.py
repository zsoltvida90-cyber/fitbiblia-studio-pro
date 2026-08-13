from content_os.platforms.platform_contract import normalize_platform,build_x_post,validate_platform_output
assert normalize_platform('Tik Tok')=='TIKTOK'
assert normalize_platform('Twitter')=='X'
assert build_x_post('a'*280)['character_count']==280
assert validate_platform_output('tiktok','REEL')['compatible'] is True
assert validate_platform_output('x','CAROUSEL')['compatible'] is False
print('PASS 5/5')
