from content_os.research.library import validate_index_record
r={'research_id':'RSH-20260813-001','project':'Fit Biblia','topic':'carousel','research_question':'test','bundle_ref':'drive://bundle','bundle_sha256':'a'*64,'status':'ACTIVE','reusable':'YES','version':'1.0'}
assert validate_index_record(r)=='OK'
print('PASS 1/1')
