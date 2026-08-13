from datetime import date
from pathlib import Path
import tempfile

from content_os.research.library import bundle_filename,classify_freshness,sha256_file,validate_index_record,verify_bundle_hash


def run():
    ok={'research_id':'RSH-20260813-001','project':'Fit Biblia','topic':'carousel typography','research_question':'What improves mobile readability?','bundle_ref':'drive://bundle','bundle_sha256':'abc','status':'ACTIVE','reusable':'YES','version':'1.0'}
    assert validate_index_record(ok)=='OK'
    bad=dict(ok); bad['bundle_ref']=''; assert validate_index_record(bad)=='BUNDLE_REF_REQUIRED'
    bad=dict(ok); bad['bundle_sha256']=''; assert validate_index_record(bad)=='BUNDLE_HASH_REQUIRED'
    assert classify_freshness('NO',None,date(2026,8,13))=='NOT_APPLICABLE'
    assert classify_freshness('YES',None,date(2026,8,13))=='REVIEW_DATE_REQUIRED'
    assert classify_freshness('YES','2026-08-12',date(2026,8,13))=='REVIEW_DUE'
    assert classify_freshness('YES','2026-08-14',date(2026,8,13))=='FRESH'
    assert bundle_filename('RSH-20260813-001','Carousel tipográfia')=='RSH-20260813-001__carousel-tipografia.txt'
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'bundle.txt'; p.write_text('research knowledge',encoding='utf-8'); h=sha256_file(p)
        assert verify_bundle_hash(p,h) is True
        try: verify_bundle_hash(p,'0'*64)
        except ValueError as e: assert str(e)=='BUNDLE_HASH_MISMATCH'
        else: raise AssertionError('hash mismatch not detected')
    return 9

if __name__=='__main__':
    print(f'PASS {run()}/9')
